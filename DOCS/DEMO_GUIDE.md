# Slack AI Codebase Assistant - 

**Status:** MVP / Demo Version  
**Date:** 21/01/26
**Purpose:** Demo for team feedback and suggestions

---

## 🎯 What This Is

A Slack bot that answers questions about your codebase using AI. Ask it questions in Slack, get instant answers about your code, schemas, and logic.

---

## ✨ Key Features

- ✅ **Slack Integration** - Works in channels and DMs
- ✅ **Codebase Queries** - Uses cursor-agent for intelligent code search
- ✅ **AI Processing** - Gemini API for clear, concise answers
- ✅ **Conversation Context** - Remembers last 10 messages in thread
- ✅ **Read-Only** - Safe, can't modify code

---

## 🏗️ Current Architecture

```
Slack → Socket Mode → slack_bot.py → cursor-agent → Gemini API → Response
```

**Components:**
- `slack_bot.py` - Handles Slack events
- `query_service.py` - Executes cursor-agent queries
- `ai_service.py` - Processes responses with Gemini
- `lambda_memory.py` - Manages conversation context

---

## 📊 Current Status

### ✅ What Works
- Channel mentions and direct messages
- Codebase queries via cursor-agent
- AI-powered response processing
- Conversation context (last 10 messages)
- Read-only file system protection

### ⚠️ Known Limitations
- In-memory storage (lost on restart)
- No rate limiting
- No channel access restrictions (works in any channel) 

### 🔄 Planned Improvements
- See `IMPROVEMENTS.md` for full list
- Priority: Error handling, logging, access control

---

## 💰 Cost Estimate

**Note:** Using GPT-4o-mini for response formatting (simple structuring task, no complex reasoning needed)

### Scenario A: Pilot (10 Users, ~10 queries/day)

| Component | Cost | Notes |
|:----------|:-----|:------|
| AWS Lambda & API Gateway | $0.00 | Well within AWS Free Tier (1M requests/month) |
| OpenAI API (GPT-4o-mini) | ~$1.50/month | ~30k context/query (formatting only) |
| Cursor Subscription | $20.00/month | Fixed cost for cursor-agent access |
| **Total** | **~$22.00/month** | |
| **Effective Cost** | **<$2.00/month** | *If using existing Cursor account* |

### Scenario B: Scale (50 Users, ~100 queries/day)

| Component | Cost | Notes |
|:----------|:-----|:------|
| AWS Lambda & API Gateway | <$2.00/month | Exceeds free tier slightly if complex |
| OpenAI API (GPT-4o-mini) | ~$15–$20/month | Higher volume, same per-query cost |
| Cursor Subscription | $20.00/month | Fixed cost for cursor-agent access |
| **Total** | **<$45.00/month** | |
| **Effective Cost** | **$20–25/month** | *If using existing Cursor account* |

**Key Points:**
- LLM is used only for formatting/structuring cursor-agent responses (simple task)
- GPT-4o-mini is sufficient and cost-effective for this use case
- Cursor subscription is the main fixed cost (can be shared across team)

---

## 🔗 Related Documentation

- **Full Proposal:** `SLACKBOT_AI_ASSISTANCE.md` (RFC)
- **Setup Guide:** `SLACK_SETUP_GUIDE.md`
- **Scalability:** `SCALABILITY_ANALYSIS.md`

---

## ❓ FAQ

**Q: Can it modify code?**  
A: No, it's read-only. It can only query and explain code.

**Q: Does it access production data?**  
A: No, it only reads code files and schema definitions.

**Q: How accurate is it?**  
A: It uses cursor-agent for code search + Gemini for synthesis. Accuracy depends on codebase clarity.

**Q: Can I use it in any channel?**  
A: Currently yes, but we plan to restrict to engineering channels.

**Q: What if it gives wrong answers?**  
A: It cites sources. Always verify critical information. It's an assistant, not an oracle.
