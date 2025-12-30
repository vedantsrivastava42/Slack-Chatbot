# Memory System Options for Slack Bot

This document outlines the available options for implementing conversation memory/session management in the Slack bot.

## Why Memory is Needed

Currently, the bot treats each message independently. When cursor-agent asks follow-up questions, the bot cannot remember previous context, forcing users to repeat information.

**Example Problem:**
```
User: "What is the auth system?"
Bot: [Queries cursor-agent]
Cursor-agent: "Which method? OAuth, JWT, or Basic?"
User: "JWT"  ← Bot doesn't remember the original question!
```

## Memory System Options

### Option 1: In-Memory Storage ⚠️

**How it works:**
- Stores conversation history in Python dictionary (RAM)
- Session key: `user_id:channel_id:thread_id`
- Data lives in process memory

**Pros:**
- ✅ Fastest access (no network calls)
- ✅ No external dependencies
- ✅ Free (no service costs)
- ✅ Simple to implement

**Cons:**
- ❌ Lost on process restart
- ❌ Not suitable for serverless (Lambda) - **unless using Lambda Container Memory**
- ❌ Doesn't scale across multiple instances
- ❌ No persistence

**Best for:**
- Development/testing
- Single-instance deployments
- Non-critical conversations

**Cost:** Free

### **Lambda Container Memory Variant** ⭐⭐⭐ (Recommended for Serverless, We implemented this) 

**Perfect for your use case - maintains conversation context without any extra cost!**

**How it works:**
- Each Lambda invocation maintains its own in-memory conversation history
- Memory lives for the duration of the Lambda execution (typically 5-10 minutes)
- Session key includes thread_ts to maintain thread-specific conversations
- Keeps only last 5-10 messages per conversation (configurable)
- Memory automatically disappears when Lambda finishes

**Pros:**
- ✅ **Fully serverless-compatible** (works perfectly with Lambda)
- ✅ **Zero extra cost** (uses allocated Lambda memory)
- ✅ **Automatic cleanup** (no manual maintenance)
- ✅ **Thread-aware** (separate memory per Slack thread)
- ✅ **Simple implementation** (no external services)

**Cons:**
- ⚠️ Memory lost between Lambda invocations (but conversations typically complete within one invocation)
- ⚠️ Limited by Lambda timeout (max 15 minutes)

**Best for:**
- Serverless deployments (Lambda)
- Low-traffic applications (1-2 queries/day)
- Conversational bots needing short-term context
- Cost-sensitive implementations

**Cost:** **FREE** (no additional AWS services)

**Implementation:**
```python
class LambdaMemoryManager:
    def __init__(self, max_messages=10):
        self.conversations = {}  # session_id -> messages
        self.max_messages = max_messages

    def get_context(self, session_id):
        return self.conversations.get(session_id, [])

    def add_message(self, session_id, role, content):
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        self.conversations[session_id].append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })

        # Keep only recent messages
        if len(self.conversations[session_id]) > self.max_messages:
            self.conversations[session_id] = self.conversations[session_id][-self.max_messages:]
```

---

### Option 2: AWS DynamoDB ⭐ (Recommended)

**How it works:**
- Stores conversation history in DynamoDB table
- Session key: `user_id:channel_id:thread_id`
- TTL for automatic cleanup (e.g., 24 hours)

**Pros:**
- ✅ Fully serverless (works with Lambda)
- ✅ Persistent (survives restarts)
- ✅ Auto-scaling
- ✅ Low latency (~10-50ms)
- ✅ Shared across multiple instances
- ✅ AWS free tier: 25GB storage

**Cons:**
- ⚠️ Requires AWS account
- ⚠️ Slight latency vs in-memory
- ⚠️ Need to set up DynamoDB table

**Best for:**
- Production deployments
- Serverless (Lambda) architecture
- Multi-instance scaling
- Cost-effective persistence

**Cost:** 
- Free tier: 25GB storage, 200M read/write units/month
- Beyond free tier: ~$1-5/month for small usage (1-2 queries/day)

**Setup:**
```bash
# Create DynamoDB table
aws dynamodb create-table \
  --table-name slack_conversations \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

### Option 3: Redis

**How it works:**
- Stores conversation history in Redis cache
- Session key: `user_id:channel_id:thread_id`
- TTL for automatic expiration

**Pros:**
- ✅ Very fast (sub-millisecond)
- ✅ Persistent (with persistence enabled)
- ✅ Works with serverless
- ✅ Shared across instances
- ✅ Rich data structures

**Cons:**
- ❌ Requires Redis service
- ❌ Higher cost than DynamoDB
- ❌ More complex setup
- ❌ Need to manage Redis instance

**Best for:**
- High-traffic applications
- When speed is critical
- Existing Redis infrastructure

**Cost:**
- AWS ElastiCache: ~$15-50/month (small instance)
- Redis Cloud: ~$10-30/month
- Self-hosted: Infrastructure costs

---

### Option 4: File-Based Storage

**How it works:**
- Stores conversation history in JSON files
- File path: `sessions/{user_id}_{channel_id}_{thread_id}.json`
- Local filesystem storage

**Pros:**
- ✅ Simple implementation
- ✅ No external services
- ✅ Free
- ✅ Easy to debug (readable files)

**Cons:**
- ❌ Not suitable for serverless (Lambda)
- ❌ File system limitations
- ❌ Doesn't scale across instances
- ❌ Manual cleanup needed
- ❌ Not ideal for production

**Best for:**
- Local development
- Single-instance deployments
- Testing

**Cost:** Free

---

### Option 5: Hybrid Approach

**How it works:**
- In-memory cache for active sessions (fast access)
- Periodic sync to DynamoDB/Redis (persistence)
- Load from storage on restart

**Pros:**
- ✅ Best of both worlds (speed + persistence)
- ✅ Reduces storage read/write costs
- ✅ Fast for active conversations

**Cons:**
- ⚠️ More complex implementation
- ⚠️ Potential data loss if sync fails
- ⚠️ Requires both systems

**Best for:**
- High-traffic applications
- When optimizing costs
- Complex requirements

**Cost:** Combined costs of both systems

---

## Comparison Table

| Option | Speed | Persistence | Serverless | Scalability | Cost | Complexity |
|--------|-------|-------------|------------|-------------|------|------------|
| **In-Memory** | ⭐⭐⭐⭐⭐ | ❌ | ⚠️ (Lambda Container) | ❌ | Free | Low |
| **DynamoDB** | ⭐⭐⭐⭐ | ✅ | ✅ | ✅ | Low | Medium |
| **Redis** | ⭐⭐⭐⭐⭐ | ✅ | ✅ | ✅ | Medium | Medium |
| **File-Based** | ⭐⭐⭐ | ✅ | ❌ | ❌ | Free | Low |
| **Hybrid** | ⭐⭐⭐⭐⭐ | ✅ | ✅ | ✅ | Medium | High |

## Recommendation

### For Your Use Case (1-2 queries/day, Serverless):

**🏆 Best Choice: Lambda Container Memory (Option 1 Variant)**

**Reasons:**
1. ✅ **Fully serverless** (works perfectly with Lambda)
2. ✅ **Zero extra cost** (FREE - no additional AWS services)
3. ✅ **Perfect for low usage** (1-2 queries/day)
4. ✅ **Automatic cleanup** (no maintenance needed)
5. ✅ **Thread-aware conversations** (maintains context per Slack thread)
6. ✅ **Simple implementation** (no external dependencies)

**💡 Alternative for Higher Usage: AWS DynamoDB**
- If you expect >10 queries/day or need persistence across Lambda restarts
- Cost: ~$1-5/month (likely free tier for small usage)

### Implementation Priority:

1. **Phase 1 (Development):** Start with Lambda Container Memory
   - Quick to implement for serverless
   - Test conversational memory logic
   - No external dependencies or costs
   - Perfect for Lambda development

2. **Phase 2 (Scale/Production):** Consider DynamoDB if needed
   - If conversations span multiple Lambda invocations
   - If you need >10 queries/day
   - If persistence across restarts is critical

## Next Steps

1. Choose your preferred option
2. Implement memory manager module
3. Update bot handlers to use memory
4. Test conversation flow
5. Deploy with chosen storage solution

## Additional Considerations

- **Session TTL:** How long to keep conversations? (Recommend: 24 hours)
- **Context Window:** How many previous messages? (Recommend: 5-10)
- **Question Detection:** Detect when cursor-agent asks questions
- **Privacy:** Consider data retention policies
- **Cost Monitoring:** Set up CloudWatch alarms for DynamoDB usage

