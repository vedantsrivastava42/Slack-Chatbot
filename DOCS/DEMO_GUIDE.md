# Slack AI Codebase Assistant - Demo Guide

**Status:** MVP / Demo Version  
**Date:** 2024-12-31  
**Purpose:** Demo for team feedback and suggestions

---

## 🎯 What This Is

A Slack bot that answers questions about your codebase using AI. Ask it questions in Slack, get instant answers about your code, schemas, and logic.

---

## 🚀 Quick Demo (2 minutes)

### Demo Scenario 1: Code Understanding
**In Slack channel:**
```
@BotName what is the User model?
```
**Bot responds with:** Model structure, relationships, key methods

### Demo Scenario 2: Schema Query
**In Slack channel:**
```
@BotName how does users table connect to subscriptions?
```
**Bot responds with:** Database relationships and foreign keys

### Demo Scenario 3: Business Logic
**In Slack channel:**
```
@BotName how is user authentication handled?
```
**Bot responds with:** Authentication flow, key files, implementation details

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
- No structured logging yet
- No rate limiting
- No channel access restrictions (works in any channel)

### 🔄 Planned Improvements
- See `IMPROVEMENTS.md` for full list
- Priority: Error handling, logging, access control

---

## 💰 Cost Estimate

**Current Usage (MVP):**
- AWS Lambda: $0 (free tier)
- Gemini API: ~$1-5/month (depends on usage)
- Cursor Subscription: $20/month (or $0 if using existing)
- **Total: ~$21-25/month** (or $1-5/month with existing Cursor)

---

## 🎯 What We Need Feedback On

1. **Use Cases** - What questions do you want to ask?
2. **Accuracy** - Are the answers helpful and correct?
3. **Response Time** - Is 30-90 seconds acceptable?
4. **Access Control** - Should we restrict to specific channels?
5. **Features** - What's missing? What would make it more useful?

---

## 🧪 How to Test

1. **Join a channel** where the bot is invited
2. **Mention the bot:** `@BotName [your question]`
3. **Wait for response** (shows 👀 emoji while processing)
4. **Try follow-up questions** in the same thread

---

## 📝 Feedback Form

After the demo, please share:
- ✅ What worked well?
- ❌ What didn't work?
- 💡 What features would you add?
- 🚀 Would you use this regularly?

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

---

## 🎬 Demo Script (5 minutes)

1. **Introduction** (30 sec)
   - "This is a Slack bot that answers codebase questions using AI"

2. **Live Demo** (2 min)
   - Show 2-3 example queries
   - Demonstrate conversation context (follow-up question)

3. **Architecture Overview** (1 min)
   - Quick diagram of how it works
   - Mention read-only safety

4. **Q&A & Feedback** (1.5 min)
   - Collect suggestions
   - Discuss use cases

---
