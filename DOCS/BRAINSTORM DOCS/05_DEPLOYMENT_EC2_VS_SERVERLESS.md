# Deployment Deep Dive: Issues, EC2 vs Serverless, and Codebase Storage

This document provides a detailed reference for deploying the Slack Codebase Chatbot: deployment challenges, a full EC2 vs Serverless comparison, and when and how to handle codebase storage.

---

## Table of Contents

1. [Deployment Issues Overview](#1-deployment-issues-overview)
2. [EC2 vs Serverless: Detailed Comparison](#2-ec2-vs-serverless-detailed-comparison)
3. [Codebase Storage: When and How](#3-codebase-storage-when-and-how)
4. [Decision Summary](#4-decision-summary)

*Section 1 also covers: [cursor-agent authentication (1.7)](#17-cursor-agent-authentication-required-to-run) — required for the bot to run.*

---

## 1. Deployment Issues Overview

### 1.1 Slack Connection Model (Socket Mode vs Events API)

| Aspect | Current Code (Socket Mode) | Required for Lambda |
|--------|---------------------------|---------------------|
| **How it works** | Long-lived WebSocket via `SocketModeHandler` and `SLACK_APP_TOKEN` | Slack sends HTTP POST to your URL (Request URL) for each event |
| **Code** | `slack_bot.py` uses `SocketModeHandler(app, SLACK_APP_TOKEN)` and `handler.start()` | Need `handler.py` with `lambda_handler(event, context)` and URL verification |
| **Required changes for Lambda** | **Yes** – remove Socket Mode; add HTTP handler; implement URL verification (`challenge`); refactor event handling into a callable (e.g. `handle_slack_event(body)`) |
| **Required changes for EC2** | **No** – keep current code as-is |

**Issue:** Lambda cannot hold a persistent WebSocket. To go serverless you must switch the Slack app to **Events API** and provide a public Request URL. On EC2 you can keep Socket Mode with no code change.

---

### 1.2 cursor-agent and Repository Path

| Aspect | Detail |
|--------|--------|
| **Current behavior** | `query_service.py` runs `cursor-agent` as a **subprocess** with `--workspace <path>`. The path must be a **local directory on disk**. |
| **Dependency** | The `cursor-agent` **binary** must be installed and on `PATH` where the bot runs. It is not a Python package. |
| **Implication for Lambda** | Lambda has no persistent filesystem and a read-only root. You cannot ship a full repo inside the deployment package (size limits ~250 MB unzipped). So either: (a) put the codebase in external storage and make it available at runtime (e.g. download to `/tmp`), or (b) run `cursor-agent` elsewhere (e.g. staging server as a query API) and have Lambda call that API. |
| **Implication for EC2** | The repo can live on the same EC2 (or an attached/mounted volume). Set `DEFAULT_REPOSITORY_PATH` to that path. No code change. `cursor-agent` must be installed on the EC2. |

**Issue:** The design assumes a local workspace. Serverless requires either external codebase storage/access or delegating the actual query to another host (e.g. staging).

#### Serverless and the codebase: you must choose how Lambda “talks” to it

On EC2, the bot and the repo can live on the same server, so `query_service` just uses a local path. **With serverless, the codebase is not on the same machine as the Lambda**, so you have to pick one of two approaches:

| Approach | How Lambda reaches the codebase | Where the code runs |
|----------|---------------------------------|----------------------|
| **A. Bring codebase to Lambda** | Lambda gets the repo at runtime (e.g. from S3 or EFS) and runs `cursor-agent` inside the same invocation. | `cursor-agent` runs **inside Lambda**; workspace is `/tmp` or an EFS mount. |
| **B. Send query to a host that has the repo** | Lambda does **not** run `cursor-agent`. It calls an HTTP API on another machine (e.g. staging or EC2) that has the repo and runs `query_codebase()` there, then returns the result. | `cursor-agent` runs **on staging/EC2**; Lambda only does Slack + HTTP client + optional AI formatting. |

- **A** needs codebase storage (S3 or EFS) and possibly bundling or downloading the repo (or tarball) into Lambda’s environment; good if you want “all in AWS” and no separate server.
- **B** needs a small query API on the host that already has the repo; no copy of the repo in AWS; Lambda just “communicates” with the codebase by sending the user query over HTTP and getting back the answer.

So yes: **even with serverless, you must figure out how the Lambda will communicate with the codebase** — either by making the codebase available inside Lambda (A) or by calling a service that has the codebase (B). Section 3 below spells out the storage options for each.

---

### 1.3 Filesystem and Read-Only Enforcement

```python
# query_service.py – lines 32–33, 93–94
subprocess.run(["chmod", "-R", "a-w", repository_path], ...)
# ...
subprocess.run(["chmod", "-R", "u+w", repository_path], ...)
```

| Aspect | Detail |
|--------|--------|
| **Purpose** | Make the repo read-only during the query to avoid accidental writes by cursor-agent. |
| **Concurrency** | Under multiple simultaneous queries, concurrent `chmod -R` on the same tree can cause lock contention or race conditions (see SCALABILITY_ANALYSIS.md). |
| **Lambda** | Only relevant if the codebase is available as a directory in Lambda (e.g. in `/tmp`). If you use a remote query API (staging), chmod runs on that host, not in Lambda. |
| **EC2** | Works as-is; consider file locking or disabling if you hit contention. |

**Issue:** Minor operational concern on EC2 at scale; not a blocker for deployment.

---

### 1.4 Conversation Memory

| Aspect | Current (`memory_manager.py`) | Lambda (recommended) | EC2 |
|--------|-----------------------------|----------------------|-----|
| **Storage** | In-memory dict keyed by `session_id` | In-memory is **per invocation** – state is lost between requests. Need **DynamoDB** (or similar) for persistent context. | In-memory is fine (process is long-lived). Optional: DynamoDB or Redis for persistence across restarts. |
| **Code change for Lambda** | **Yes** – implement a `MemoryManager` that uses DynamoDB (or use the one in DEPLOYMENT_GUIDE.md) and swap it in. | | **No** for in-memory; **optional** if you add persistence. |

**Issue:** For serverless, in-memory context is not shared across invocations; you need a persistent store (e.g. DynamoDB) for multi-turn conversations.

---

### 1.5 Timeouts and Long-Running Queries

| Limit | Lambda | EC2 |
|-------|--------|-----|
| **Max execution** | 15 minutes (900 s) per invocation | Unlimited (limited by your process manager and Slack). |
| **Current default** | `DEFAULT_TIMEOUT = 600000` ms (10 min) in `query_service.py` – within Lambda limit. | Same. |
| **Slack** | Slack may timeout waiting for HTTP response (Events API); 3 s recommendation for responding quickly and doing work asynchronously if needed. | Socket Mode does not impose the same HTTP timeout. |

**Issue:** For Lambda, design for quick HTTP 200 to Slack (e.g. acknowledge immediately) and process events asynchronously if a single query can run for minutes, or ensure queries finish within Slack’s expectations.

---

### 1.6 Dependencies and Environment

| Dependency | Notes |
|------------|--------|
| **Python** | 3.x; `requirements.txt`: `openai`, `python-dotenv`, `slack-bolt`, `certifi`. For Lambda add `boto3` if using DynamoDB. |
| **cursor-agent** | External binary; must be installed on the **same environment** that runs `query_codebase()` (EC2 or the host that serves the “staging query API”). Lambda cannot realistically ship and run it unless you bundle it and the workspace in the deployment or /tmp (size and complexity are high). |
| **Secrets** | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` (Socket Mode), or `SLACK_SIGNING_SECRET` (Events API), `GEMINI_API_KEY`. Use env vars or a secrets manager; never commit. |
| **Optional env** | `DEFAULT_REPOSITORY_PATH`, `MAX_CONVERSATION_MESSAGES`, `CURSOR_AGENT_MODEL`, `ENABLE_READONLY_ENFORCEMENT`, `GEMINI_MODEL`. |

**Issue:** Serverless requires packaging Python deps (e.g. Lambda layer); cursor-agent and the repo must be handled separately (see codebase storage section).

---

### 1.7 cursor-agent Authentication (Required to Run)

**cursor-agent needs Cursor account authentication to run.** Without it, the subprocess will fail when the bot tries to query the codebase. This is a real constraint for deployment.

| Where cursor-agent runs | How authentication is provided |
|-------------------------|---------------------------------|
| **EC2** | Auth lives on the instance: run `cursor-agent status` / `cursor auth login` once (or set `CURSOR_API_KEY` / equivalent in the environment). The same machine has both the bot and cursor-agent, so one-time setup is enough. |
| **Lambda (approach A – run cursor-agent in Lambda)** | **You must provide auth in the Lambda environment.** e.g. set `CURSOR_API_KEY` (or whatever cursor-agent reads) as a Lambda env var or from Secrets Manager. If you don’t, there will be no authentication and cursor-agent will fail. In practice, approach A is not viable: cursor-agent needs the codebase on disk and auth that does not work by simply setting an API key in a headless environment. |
| **Lambda (approach B – staging/EC2 as query API)** | cursor-agent runs **on the staging/EC2 server**, not in Lambda. Authentication stays on that server (where you already ran `cursor auth login` or set the key). Lambda never runs cursor-agent and does not need Cursor credentials. **This is the option where “auth stays where cursor-agent runs” with no extra step in Lambda.** |

**Important:** cursor-agent authentication **does not work by simply setting an API key** in a headless or serverless environment; it is intended for use on a machine where you have run `cursor auth login` (or equivalent). Running cursor-agent inside Lambda (approach A) is therefore **not a viable option** for this project. **Recommendation:** Proceed with **EC2** (or an existing staging server)—run the Slack bot, cursor-agent, and the codebase on the same machine and authenticate cursor-agent there once. (With approach B you still need an EC2 or staging server to run cursor-agent; Lambda only calls its HTTP API. So in practice, if you rely on cursor-agent, prefer EC2.)

---

## 2. EC2 vs Serverless: Detailed Comparison

### 2.1 Architecture at a Glance

**EC2 (current design, minimal change):**

```
Slack (Socket Mode) ←→ EC2 [ Slack process + cursor-agent + repo on disk ]
                              ↑
                        Same machine or mounted volume
```

**Serverless (Lambda + Events API):**

```
Slack (Events API) → API Gateway → Lambda (handler + bot logic)
                                        ↓
                        Either: (A) Lambda /tmp + S3 or EFS (repo)
                        Or:     (B) Lambda → HTTP call → Staging/EC2 query API (repo there)
                        Plus:   DynamoDB (conversation memory)
```

---

### 2.2 Code and Configuration Changes

| Item | EC2 | Serverless (Lambda) |
|------|-----|----------------------|
| **Slack integration** | No change. Keep Socket Mode and `SocketModeHandler`. | Switch to Events API; add `handler.py`; URL verification; refactor to `handle_slack_event(body)`. |
| **query_service.py** | No change. Continue subprocess + `--workspace` with local path. | No change to function signature; implementation either uses a path in `/tmp` (populated from S3/EFS or download) or is replaced by an HTTP client that calls a remote query API. |
| **slack_bot.py** | No change. | Extract mention/message handling into a function called from the Lambda handler; remove `SocketModeHandler` and `start_slack_bot()` for the Lambda entry path. |
| **Memory** | Keep `MemoryManager` (in-memory). Optional: add DynamoDB/Redis later. | Replace with DynamoDB-backed memory (new or existing `memory_manager.py`) so context persists across invocations. |
| **New files** | None required. | `handler.py`; optionally `memory_manager.py` (DynamoDB); `serverless.yml` or SAM template. |
| **Configuration** | Env vars on EC2; `DEFAULT_REPOSITORY_PATH` to local path. | Env vars in Lambda (or Secrets Manager); possibly `CODEBASE_QUERY_URL` if using remote query API; DynamoDB table name. |

---

### 2.3 Cost (Rough Monthly Estimates)

Assumptions: few dozen to low hundreds of queries per day; conversation memory in DynamoDB for Lambda.

| Component | EC2 | Serverless |
|-----------|-----|------------|
| **Compute** | One small instance (e.g. t3.small): ~\$15–25. Always on. | Lambda: free tier then ~\$0.20 per 1M requests; first few hundred queries effectively \$0. |
| **API Gateway** | N/A. | Free tier 1M calls; minimal cost at low volume. |
| **DynamoDB** | Optional; similar cost if used. | PAY_PER_REQUEST; cents at low usage. |
| **Storage (repo)** | Use existing disk on EC2 or attach volume; no extra S3/EFS. | Only if you use S3/EFS for repo: S3 cheap; EFS ~\$0.30/GB-month. |
| **Total (low traffic)** | ~\$15–25/month. | ~\$0–2/month. |
| **Total (higher traffic)** | Same fixed cost; scales with instance size if needed. | Grows with invocations and duration; still often cheaper until consistently high load. |

---

### 2.4 Operations and Reliability

| Aspect | EC2 | Serverless |
|--------|-----|------------|
| **Deployment** | SSH/CI; start/restart process (systemd/supervisor); optional Docker. | `serverless deploy` or SAM; no OS management. |
| **Scaling** | Vertical (bigger instance) or add instances + load balancer if you expose an API. | Automatic; concurrency and retries managed by AWS. |
| **Availability** | Depends on single instance (or your redundancy). Patches and reboots are your responsibility. | Multi-AZ by default; no server patching. |
| **Cold starts** | None (process always running). | Lambda can have 1–3+ s cold start; first request per idle period may be slower. |
| **Monitoring** | CloudWatch agent, custom metrics, logs on instance. | CloudWatch Logs and metrics per function; easier out of the box. |
| **Secrets** | Env file or parameter store on instance. | Env vars, Parameter Store, or Secrets Manager. |

---

### 2.5 When to Choose Which

- **Prefer EC2 if:**
  - You want **minimal code change** and already have (or can have) the repo on that box.
  - You have a **staging EC2** and are fine running the bot on the same server (same cost, no extra storage).
  - You want **no cold starts** and simple Socket Mode.
  - Low fixed monthly cost (~\$15–25) is acceptable.

- **Prefer Serverless if:**
  - You want **pay-per-use** and near-zero cost at low volume.
  - You prefer **no server management** and automatic scaling.
  - You are okay implementing **Events API**, **handler.py**, and **DynamoDB memory**, and either (a) remote query API on staging/EC2 or (b) codebase in S3/EFS + /tmp (or similar).

---

## 3. Codebase Storage: When and How

The bot needs *some* way to run `cursor-agent --workspace <path>` (or an equivalent that has access to the repo). Whether you need “separate” storage depends on where the code runs and where the repo lives.

### 3.1 Do You Need Separate Codebase Storage?

| Deployment | Where repo lives | Separate storage needed? |
|------------|------------------|---------------------------|
| **EC2, repo on same instance** | e.g. `/home/ubuntu/NinjasTool` | **No.** Set `DEFAULT_REPOSITORY_PATH` to that path. |
| **EC2, repo on another server** | NFS mount or clone on EC2 | **No** from the app’s view (path is still local). You may use NFS/EFS for the mount. |
| **Lambda, query runs inside Lambda** | Must be inside Lambda env (e.g. `/tmp`) | **Yes.** Repo must be fetched from somewhere (S3, EFS, or HTTP) into Lambda’s filesystem. |
| **Lambda, query runs on staging/EC2** | Staging or EC2 | **No.** Lambda does not store the repo; it calls a remote query API that has the repo locally. |

So: **you need explicit “codebase storage” and a strategy only when the process that runs `cursor-agent` does not already have the repo on its local disk** (i.e. in Lambda if you run cursor-agent there). On EC2, if the repo is on the same box (or a mount), you do **not** need extra storage for the codebase.

---

### 3.2 Options When You Do Need to Provide the Repo (e.g. for Lambda)

#### Option A: Staging (or EC2) as Query API – No Repo in AWS

- **Idea:** Run a small HTTP service on the host that already has the repo (staging/EC2). It accepts `POST /query` with `query` and `conversation_context`, runs `query_codebase()` locally, returns the result. Lambda receives the Slack event, calls this API, then posts the answer back to Slack.
- **Repo storage:** Repo stays only on staging/EC2. **No** S3 or EFS for the codebase.
- **Pros:** No duplicate storage; single source of truth; Lambda stays small.  
- **Cons:** Staging/EC2 must be reachable from Lambda (VPC or public URL); you must secure the endpoint (e.g. API key, VPC); that host does the CPU work.

#### Option B: S3 + Download to Lambda `/tmp`

- **Idea:** Repo (or a tarball) is in S3. On each (or first) invocation, Lambda downloads and extracts to `/tmp` and runs `cursor-agent` on that path.
- **Repo storage:** S3 (e.g. bucket + versioning). Lambda uses `/tmp` (up to 10 GB configurable).
- **Pros:** No other server needed; fits “pure serverless.”  
- **Cons:** Cold start and latency grow with repo size; 250 MB deployment limit for the Lambda package (so the repo cannot go in the package; it must be in S3). `/tmp` is limited; large repos may not fit or may be slow.

#### Option C: EFS Mount for Lambda

- **Idea:** Repo lives on an EFS file system; Lambda mounts EFS and uses a path like `/mnt/efs/NinjasTool` as `DEFAULT_REPOSITORY_PATH`.
- **Repo storage:** EFS. Sync or clone the repo into EFS (e.g. from CI or a small job).
- **Pros:** No download per invocation; shared across invocations; can support larger repos.  
- **Cons:** EFS cost (~\$0.30/GB-month); VPC required; more setup (NFS, sync pipeline).

#### Option D: EC2 (or Staging) Has Repo – Bot Runs There

- **Idea:** Run the Slack bot process on the same EC2 (or staging) where the repo already exists. No Lambda.
- **Repo storage:** None extra. Use existing directory.
- **Pros:** Simplest; no codebase storage design; no code change for paths.  
- **Cons:** You operate an EC2 and a long-running process.

---

### 3.3 Codebase Storage Summary Table

| Option | Where repo lives | Extra storage in AWS? | Complexity | Best for |
|--------|------------------|------------------------|------------|----------|
| **Staging/EC2 as API** | Staging/EC2 | No | Medium (build query API + auth) | Lambda + existing staging server |
| **S3 → /tmp** | S3; at runtime in Lambda /tmp | S3 only | Medium (download + extract in handler) | Small repos; pure serverless |
| **EFS for Lambda** | EFS | EFS | Higher (VPC, mount, sync) | Larger repos; many invocations |
| **EC2 same box** | EC2 disk | No | Low | Easiest; acceptable to run on one server |

---

## 4. Decision Summary

- **Deployment issues:** The main hurdles are (1) Slack Socket Mode vs Events API for Lambda, (2) cursor-agent requiring a local workspace or a remote query API, (3) conversation memory persistence in Lambda (DynamoDB), and (4) timeouts and packaging (deps + optional codebase).
- **EC2 vs Serverless:** EC2 needs minimal or no code change and works with the current repo path and in-memory memory. Serverless needs Events API, handler, DynamoDB memory, and a clear strategy for where `cursor-agent` runs and where the repo lives.
- **Codebase storage:** You only need separate codebase storage when the environment that runs `cursor-agent` does not already have the repo on disk (typically Lambda). On EC2, pointing `DEFAULT_REPOSITORY_PATH` at the staging/local path is enough. For Lambda, the most storage-efficient approach is “staging as query API” (no repo copy in AWS); alternatives are S3+/tmp or EFS if you want the query to run inside Lambda.

Use this document alongside **DEPLOYMENT_GUIDE.md** (serverless steps) and **SCALABILITY_ANALYSIS.md** (concurrency and scaling) when choosing and implementing your deployment.
