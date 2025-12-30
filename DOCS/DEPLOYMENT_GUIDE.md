# Deployment Guide - Serverless Slack Bot

This guide covers deploying the Slack bot to AWS Lambda for cost-effective, serverless operation.

## Overview

**Use Case:** 2-3 queries per day, doesn't need to be always-on  
**Architecture:** AWS Lambda + API Gateway + DynamoDB  
**Cost:** ~$0-2/month (mostly free tier)

## Architecture

```
Slack → API Gateway → Lambda (Bot Handler) → cursor-agent → Lambda (Query Processing)
                                              ↓
                                         DynamoDB (Memory)
```

### Components:

1. **AWS Lambda** - Runs bot code (pay per request)
2. **API Gateway** - Receives Slack webhooks
3. **DynamoDB** - Stores conversation memory
4. **Lambda Layer** - Python dependencies
5. **S3** - Stores codebase repository (optional)

## Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.11+
- Serverless Framework or AWS SAM (recommended: Serverless Framework)

## Step 1: Convert to Events API (HTTP Webhooks)

Since Socket Mode requires persistent connections (not suitable for Lambda), we need to convert to Events API.

### Changes Required:

1. **Remove Socket Mode** - No `SocketModeHandler`
2. **Add HTTP Handler** - Lambda function handler
3. **Add URL Verification** - Slack requires URL verification
4. **Update Slack App** - Configure Request URL in Slack app settings

## Step 2: Setup AWS Resources

### 2.1 Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name slack-conversations \
  --attribute-definitions AttributeName=session_id,AttributeType=S \
  --key-schema AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2.2 Create S3 Bucket (for repository storage - optional)

```bash
aws s3 mb s3://your-slack-bot-repo --region us-east-1
```

## Step 3: Create Lambda Function Structure

### Project Structure:

```
slack-bot-lambda/
├── handler.py          # Lambda entry point
├── slack_bot.py        # Bot logic (modified)
├── query_service.py    # Query processing
├── ai_service.py       # AI processing
├── memory_manager.py   # DynamoDB memory management
├── requirements.txt    # Dependencies
└── serverless.yml      # Serverless Framework config
```

## Step 4: Serverless Framework Configuration

### `serverless.yml`:

```yaml
service: slack-codebase-bot

frameworkVersion: '3'

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  timeout: 300  # 5 minutes (max for Lambda)
  memorySize: 1024
  environment:
    SLACK_BOT_TOKEN: ${env:SLACK_BOT_TOKEN}
    SLACK_SIGNING_SECRET: ${env:SLACK_SIGNING_SECRET}
    GEMINI_API_KEY: ${env:GEMINI_API_KEY}
    GEMINI_MODEL: ${env:GEMINI_MODEL, 'models/gemini-flash-latest'}
    DEFAULT_REPOSITORY_PATH: ${env:DEFAULT_REPOSITORY_PATH}
    DYNAMODB_TABLE: slack-conversations
  iamRoleStatements:
    - Effect: Allow
      Action:
        - dynamodb:GetItem
        - dynamodb:PutItem
        - dynamodb:UpdateItem
        - dynamodb:DeleteItem
      Resource: arn:aws:dynamodb:${self:provider.region}:*:table/slack-conversations

functions:
  slackBot:
    handler: handler.lambda_handler
    events:
      - http:
          path: slack/events
          method: post
          cors: true

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: non-linux
    layer: true
```

## Step 5: Lambda Handler Code

### `handler.py`:

```python
import json
from slack_bot import handle_slack_event

def lambda_handler(event, context):
    """Lambda handler for Slack Events API"""
    
    # Parse request body
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', {})
    
    # URL verification challenge
    if body.get('type') == 'url_verification':
        return {
            'statusCode': 200,
            'body': body.get('challenge')
        }
    
    # Handle Slack event
    try:
        result = handle_slack_event(body)
        return {
            'statusCode': 200,
            'body': json.dumps({'ok': True})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

## Step 6: Modified Slack Bot Code

### Key Changes:

1. **Remove Socket Mode** - No `SocketModeHandler`
2. **Add HTTP Handler** - Process Events API payloads
3. **Add Memory Manager** - Use DynamoDB for sessions
4. **Handle Async** - Lambda-compatible async handling

### `slack_bot.py` (Modified):

```python
from slack_bolt import App
from slack_sdk.web import WebClient
from memory_manager import MemoryManager
from query_service import query_codebase, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT

# Initialize
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
memory = MemoryManager()

def handle_slack_event(body):
    """Handle Slack Events API payload"""
    event = body.get('event', {})
    event_type = event.get('type')
    
    if event_type == 'app_mention':
        handle_app_mention(event)
    elif event_type == 'message':
        handle_message(event)
    
    return {'ok': True}

@app.event("app_mention")
def handle_app_mention(event):
    # Get conversation context
    session_id = f"{event['user']}:{event['channel']}:{event.get('thread_ts', event['ts'])}"
    context = memory.get_context(session_id)
    
    # Process query with context
    query = extract_query(event['text'])
    result = query_codebase(query, DEFAULT_REPOSITORY_PATH, DEFAULT_TIMEOUT, context)
    
    # Save to memory
    memory.add_message(session_id, 'user', query)
    memory.add_message(session_id, 'bot', result['response'])
    
    # Send response
    app.client.chat_postMessage(
        channel=event['channel'],
        thread_ts=event.get('thread_ts', event['ts']),
        text=result['response']
    )
```

## Step 7: Memory Manager with DynamoDB

### `memory_manager.py`:

```python
import boto3
import json
from datetime import datetime, timedelta
from typing import List, Dict

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('slack-conversations')

class MemoryManager:
    def __init__(self, ttl_hours=24):
        self.ttl_hours = ttl_hours
    
    def get_session_id(self, user_id: str, channel_id: str, thread_ts: str = None) -> str:
        """Generate session ID"""
        if thread_ts:
            return f"{user_id}:{channel_id}:{thread_ts}"
        return f"{user_id}:{channel_id}"
    
    def get_context(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        """Get conversation context from DynamoDB"""
        try:
            response = table.get_item(Key={'session_id': session_id})
            if 'Item' in response:
                history = response['Item'].get('history', [])
                return history[-max_messages:]  # Last N messages
            return []
        except Exception as e:
            print(f"Error getting context: {e}")
            return []
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message to conversation history"""
        try:
            # Get existing history
            response = table.get_item(Key={'session_id': session_id})
            history = response.get('Item', {}).get('history', []) if 'Item' in response else []
            
            # Add new message
            history.append({
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Keep only last 20 messages
            history = history[-20:]
            
            # Save to DynamoDB with TTL
            ttl = int((datetime.utcnow() + timedelta(hours=self.ttl_hours)).timestamp())
            table.put_item(Item={
                'session_id': session_id,
                'history': history,
                'last_activity': datetime.utcnow().isoformat(),
                'ttl': ttl
            })
        except Exception as e:
            print(f"Error saving message: {e}")
```

## Step 8: Update Requirements

### `requirements.txt`:

```txt
slack-bolt>=1.18.0
openai>=1.0.0
python-dotenv>=1.0.0
certifi>=2024.0.0
boto3>=1.34.0
```

## Step 9: Deployment Steps

### 9.1 Install Serverless Framework

```bash
npm install -g serverless
npm install --save-dev serverless-python-requirements
```

### 9.2 Configure Environment Variables

Create `.env` file:
```env
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
GEMINI_API_KEY=your-gemini-key
DEFAULT_REPOSITORY_PATH=/path/to/repo
```

### 9.3 Deploy

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy to AWS
serverless deploy

# Output will show API Gateway URL:
# https://xxxxx.execute-api.us-east-1.amazonaws.com/dev/slack/events
```

### 9.4 Configure Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your app
3. Go to **Event Subscriptions**
4. Enable Events
5. Set **Request URL** to: `https://your-api-gateway-url/slack/events`
6. Slack will verify the URL (must return challenge)
7. Subscribe to events: `app_mention`, `message.im`, `message.channels`

## Step 10: Cost Analysis

### Monthly Cost Estimate (2-3 queries/day):

| Service | Usage | Cost |
|---------|-------|------|
| **Lambda** | ~90 invocations/month | **Free** (1M free/month) |
| **API Gateway** | ~90 requests/month | **Free** (1M free/month) |
| **DynamoDB** | ~90 read/write ops/month | **Free** (25GB free) |
| **Data Transfer** | Minimal | **Free** (1GB free/month) |
| **Total** | | **~$0/month** |

### If Usage Increases:

- 100 queries/day = ~$0.50-1/month
- 1000 queries/day = ~$5-10/month

## Step 11: Monitoring & Logs

### CloudWatch Logs:

```bash
# View logs
serverless logs -f slackBot --tail

# Or via AWS CLI
aws logs tail /aws/lambda/slack-codebase-bot-dev-slackBot --follow
```

### Set Up Alarms (Optional):

```yaml
# Add to serverless.yml
resources:
  Resources:
    ErrorAlarm:
      Type: AWS::CloudWatch::Alarm
      Properties:
        AlarmName: slack-bot-errors
        MetricName: Errors
        Namespace: AWS/Lambda
        Statistic: Sum
        Period: 300
        EvaluationPeriods: 1
        Threshold: 5
        ComparisonOperator: GreaterThanThreshold
```

## Step 12: Testing

### Local Testing:

```bash
# Install serverless-offline plugin
npm install --save-dev serverless-offline

# Add to serverless.yml plugins
plugins:
  - serverless-python-requirements
  - serverless-offline

# Run locally
serverless offline
```

### Test Slack Integration:

1. Send test message in Slack
2. Check CloudWatch logs
3. Verify DynamoDB entries
4. Test conversation context

## Troubleshooting

### Common Issues:

1. **Timeout Errors**
   - Increase Lambda timeout (max 15 min)
   - Optimize cursor-agent queries

2. **Cold Start Delays**
   - Use Lambda Provisioned Concurrency (costs more)
   - Or accept 2-3 second cold start

3. **Memory Issues**
   - Increase Lambda memory (affects CPU)
   - Optimize dependencies

4. **DynamoDB Errors**
   - Check IAM permissions
   - Verify table exists

## Alternative: AWS SAM Deployment

If you prefer AWS SAM over Serverless Framework:

### `template.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  SlackBotFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      Runtime: python3.11
      Timeout: 300
      MemorySize: 1024
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /slack/events
            Method: post
      Environment:
        Variables:
          SLACK_BOT_TOKEN: !Ref SlackBotToken
          DYNAMODB_TABLE: slack-conversations
      Policies:
        - DynamoDBCrudPolicy:
            TableName: slack-conversations
```

Deploy with:
```bash
sam build
sam deploy --guided
```

## Security Best Practices

1. **Environment Variables** - Use AWS Secrets Manager for sensitive data
2. **IAM Roles** - Least privilege principle
3. **VPC** - Not needed for this use case
4. **API Gateway** - Enable API key if needed
5. **Slack Signing** - Verify request signatures

## Next Steps

1. ✅ Deploy Lambda function
2. ✅ Configure Slack Events API
3. ✅ Test basic functionality
4. ✅ Implement memory system
5. ✅ Monitor costs and performance
6. ✅ Set up alerts

## Resources

- [Serverless Framework Docs](https://www.serverless.com/framework/docs)
- [AWS Lambda Python Guide](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Slack Events API](https://api.slack.com/events-api)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

