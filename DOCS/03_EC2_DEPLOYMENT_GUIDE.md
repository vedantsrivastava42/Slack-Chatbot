# EC2 Deployment – Slack Codebase Chatbot (Simplified)

## What this setup does

* Runs Slack bot + cursor-agent + codebase on **one EC2**
* Uses **Slack Socket Mode**
* cursor-agent is authenticated **once via terminal**
* No serverless, no extra infra

This is required because **cursor-agent needs a persistent, authenticated machine**.

---

## 1. Launch EC2

* AMI: **Ubuntu 22.04**
* Instance: **t4g.medium**
* Disk: **25 GB**
* Security group:

  * Inbound: SSH (22) from your IP
  * Outbound: allow all

---

## 2. SSH & basic setup

```bash
ssh -i KEY.pem ubuntu@PUBLIC_IP
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3.12 python3.12-venv python3-pip nodejs npm
```

---

## 3. Install & authenticate cursor-agent

```bash
curl https://cursor.com/install -fsSL | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
cursor-agent status
cursor-agent auth login
cursor-agent status
```

✅ This step **must succeed**.
Cursor auth is tied to this machine.

---

## 4. Clone repos

```bash
# Bot
mkdir -p ~/app && cd ~/app
git clone YOUR_BOT_REPO slack-bot

# Codebase to query
git clone YOUR_CODEBASE_REPO ~/codebase
```

---

## 5. Setup bot environment

```bash
cd ~/app/slack-bot/CHATBOT\ SERVICE
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

GEMINI_API_KEY=...
GEMINI_MODEL=models/gemini-flash-latest

DEFAULT_REPOSITORY_PATH=/home/ubuntu/codebase
```

---

## 6. Run as a service (systemd)

```bash
sudo nano /etc/systemd/system/slack-bot.service
```

```ini
[Unit]
Description=Slack Codebase Bot
After=network.target

[Service]
User=ubuntu
Environment="PATH=/home/ubuntu/.local/bin:/usr/bin:/bin"
WorkingDirectory=/home/ubuntu/Slack-Chatbot
ExecStart=/home/ubuntu/Slack-Chatbot/venv/bin/python slack_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Reload systemd so it picks up the new/edited service file
sudo systemctl daemon-reload
# Start the service on every boot (survives EC2 reboot)
sudo systemctl enable slack-bot
# Start the service now (runs in background)
sudo systemctl start slack-bot
# Stream live logs (Ctrl+C to exit; service keeps running)
journalctl -u slack-bot -f
```

### Other important commands

| Goal | Command |
|------|--------|
| **Stop** the app | `sudo systemctl stop slack-bot` |
| **Restart** (e.g. after code or `.env` change) | `sudo systemctl restart slack-bot` |
| **Check status** (running/stopped, recent logs) | `sudo systemctl status slack-bot` |
| **Disable** (don’t start on boot) | `sudo systemctl disable slack-bot` |
| **Re-enable** (start on boot again) | `sudo systemctl enable slack-bot` |
| **Recent logs** (no follow) | `journalctl -u slack-bot -n 100` |
| **Reload** (after editing the `.service` file) | `sudo systemctl daemon-reload` then `sudo systemctl restart slack-bot` |

---

## 7. Verify

* Invite bot to Slack
* Mention it
* Check logs

---

## Cron: auto-pull and cursor-agent

If you use cron to pull the repo (e.g. `git pull` on a schedule), and cursor-agent is run from cron or from a non-interactive session, you may see:

```text
Workspace Trust Required
Cursor Agent can execute code and access files in this directory.
Do you trust the contents of this directory?
...
To proceed, you can either:
  • Run 'agent' interactively to decide
  • Pass --trust, --yolo, or -f if you trust this directory
```

**If you see this:** run the agent with trust for that run:

```bash
cursor-agent --trust
# or
cursor-agent -f
```

If the agent is invoked from a **cron job**, add `--trust` (or `-f`) to the command so the job doesn’t block, e.g.:

```bash
cursor-agent --trust "your instruction"
```

Trust is per environment; runs from cron don’t use the same “trusted” state as Cursor IDE, so the flag is needed for non-interactive runs.

---

## Why this is EC2 (important note)

* cursor-agent:

  * needs local repo
  * needs terminal-based auth
  * cannot run reliably in Lambda
* Hence **serverless is not suitable for execution layer**

---

