# Memory System Options for Slack Bot

Short reference for conversation memory: what we use on **EC2** and what to use if you deploy on **serverless**.

---

## Why memory is needed

Without memory, every message is answered in isolation. Follow-ups lose context:

```
User: "What is the auth system?"
Bot: [Queries cursor-agent] → "Which method? OAuth, JWT, or Basic?"
User: "JWT"  ← Without memory, the bot doesn't know this refers to auth; context is lost.
```

Memory stores recent messages per conversation (e.g. by `user_id:channel_id:thread_id`) so the bot can pass "previous conversation" into the next query.

---

## EC2 deployment (current) – recommended options

On EC2 the bot runs in a **single long‑running process**. In‑memory state persists for the life of that process, so the following options make sense.

### In-memory (current implementation) – recommended for EC2

**How it works:** A Python dict in the bot process; key = session id, value = list of recent messages. Implemented in `memory_manager.py` (used on EC2 as well as the name suggests).

**Pros:**
- Fastest (no network or disk I/O)
- No external dependencies or services
- Simple to implement and debug
- Zero infra or usage cost

**Cons:**
- Lost on process restart
- Not shared across multiple bot instances (single-instance only)
- No persistence for audit or replay

**Best for:** EC2 with one instance; 10–50 users; development and most production use.

**Cost:** Free.

---

### Optional: file-based (EC2 only)

Store each session as a JSON file on disk (e.g. `sessions/{session_id}.json`) with a cap on messages and optional TTL cleanup.

**Pros:**
- Survives bot restarts
- No external service or DB
- Easy to debug (readable files)
- Free (uses instance disk)

**Cons:**
- Not suitable for serverless (Lambda)
- Does not scale across multiple instances
- Manual or cron-based cleanup for TTL
- Disk I/O and possible lock handling

**Best for:** Single EC2 where you want persistence across restarts and prefer not to use DynamoDB.

**Cost:** Free (disk on the instance).

---

### Optional: hybrid (EC2)

In-memory cache for active sessions plus periodic or shutdown sync to DynamoDB (or file). Reduces persistent storage reads/writes.

**Pros:**
- Fast for hot conversations (in-memory)
- Durable state in DynamoDB or file
- Can reduce DynamoDB cost at higher traffic

**Cons:**
- More complex (cache + sync logic)
- Risk of lost updates if sync fails before shutdown
- Two systems to configure and operate

**Best for:** Higher traffic or when you need both speed and durable persistence.

**Cost:** Free (if backing store is file) or DynamoDB cost (often free tier).

---

## Serverless deployment – options

On Lambda, **every Slack message is a new invocation**. There is no shared in-process memory between requests. So:

- **In-memory in Lambda does not give conversation context across messages.** Each invocation’s memory is gone by the next message. Any “Lambda container memory” option that relies only on in-process state is therefore **not** suitable for multi-turn conversations in serverless; it has been removed from this doc.
- For serverless you need **persistent storage** that Lambda reads/writes on each invocation.

### DynamoDB – recommended for serverless

Store session history in a DynamoDB table (e.g. partition key `session_id`), with optional TTL for automatic expiry.

**Pros:**
- Persists across Lambda invocations (real multi-turn context)
- Serverless-native; no long-lived connections
- Auto-scaling; shared across all invocations
- Low latency (~10–50 ms typical)
- Free tier: 25 GB storage, 200M read/write units/month
- PAY_PER_REQUEST billing so low usage can stay at $0

**Cons:**
- Extra latency vs in-memory (each request does 1–2 DB ops)
- Requires table creation and IAM permissions
- Need to implement a small DynamoDB-backed memory manager

**Best for:** Any production Slack bot on Lambda (or API Gateway + Lambda).

**Cost:** Free tier covers typical small usage (e.g. tens of thousands of sessions/month). Beyond that, roughly $1–5/month for moderate traffic (hundreds of queries/day).

---

### Redis (serverless)

Use Redis (e.g. ElastiCache or a managed service) to store session history. Lambda connects to Redis over the network (e.g. in a VPC or via a proxy).

**Pros:**
- Very fast (sub-millisecond reads/writes)
- Shared across all Lambda invocations
- Rich structures (list per session, TTL per key)
- Works with serverless if networking is set up

**Cons:**
- Higher cost than DynamoDB for similar scale
- Requires VPC/subnet or connection proxy; cold starts can be slower
- More operational overhead (Redis cluster or managed service)

**Best for:** When you already have Redis in the stack or need very high read/write throughput.

**Cost:** AWS ElastiCache (small node) roughly $15–50/month; managed Redis (e.g. Redis Cloud) often $10–30/month for small tiers.

---

## Summary

| Deployment | Recommended option        | Reason |
|------------|---------------------------|--------|
| **EC2**    | **In-memory** (current)   | One process; state lives for the process; no extra services. |
| **EC2** (need persistence across restarts) | File-based or DynamoDB | Survives restarts; still simple. |
| **Serverless (Lambda)** | **DynamoDB**              | No per-request memory; only persistent storage gives cross-message context. |

**Important:** On Lambda, in-memory (or “container memory”) alone **cannot** provide conversation context between different Slack messages; each message is a new invocation. Use DynamoDB (or another persistent store) for serverless.

---

## Implementation notes

- **Session key:** `user_id:channel_id:thread_ts` (or `channel_id` for non-threaded DMs). Already used in `memory_manager.py`.
- **Context window:** Last 5–10 messages per session is usually enough (configurable via `MAX_CONVERSATION_MESSAGES`).
- **TTL (DynamoDB/file):** e.g. 24 hours so old sessions are dropped.
- **Privacy:** Align retention and storage with your data policy.

For deployment choices (EC2 vs serverless) and cursor-agent, see the deployment docs in this folder.
