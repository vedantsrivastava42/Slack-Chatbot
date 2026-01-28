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
sudo apt install -y git python3.11 python3.11-venv python3-pip nodejs npm
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
python3.11 -m venv venv
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
WorkingDirectory=/home/ubuntu/app/slack-bot/CHATBOT SERVICE
ExecStart=/home/ubuntu/app/slack-bot/CHATBOT SERVICE/venv/bin/python slack_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable slack-bot
sudo systemctl start slack-bot
journalctl -u slack-bot -f
```

---

## 7. Verify

* Invite bot to Slack
* Mention it
* Check logs

---

## Why this is EC2 (important note)

* cursor-agent:

  * needs local repo
  * needs terminal-based auth
  * cannot run reliably in Lambda
* Hence **serverless is not suitable for execution layer**

---

