# RFC: Slack-Native Read-Only AI Assistant

**Status:** Draft
**Date:** 2024-12-31
**Author:** [Your Name/Team]
**Audience:** CTO / Engineering Leadership

---

## 1. Executive Summary

This proposal introduces a read-only, Slack-native AI assistant designed to provide accurate, context-aware answers about our codebase (`NinjasTool`), database schemas, and service logic directly within engineering channels. By leveraging our existing documentation and codebase as a knowledge base, this tool aims to democratize system understanding and reduce the "tribal knowledge" bottleneck.

The need for this solution arises from the increasing cognitive load on oncall engineers and the friction in PM–Engineering communication. Routine questions about logic ("How is X calculated?") or schema ("Where is Y stored?") currently disrupt senior engineers, delaying critical work. This tool will handle these Tier-1 inquiries instantly.

We expect this implementation to significantly reduce context-switching for senior staff, accelerate onboarding for new hires, and empower Product Managers and Data Analysts to self-serve technical answers safely.

---

## 2. Problem Statement

Our engineering team currently faces efficiency challenges related to knowledge sharing and system understanding:

*   **High Oncall Cognitive Load:** Oncall engineers spend a significant portion of their shift answering routine questions.
*   **Knowledge Silos:** Deep understanding of legacy logic and schema relationships is concentrated among a few senior engineers, creating single points of failure.
*   **PM–Engineering Misalignment:** Product Managers often wait hours or days for feasibility answers that could be retrieved in minutes.
*   **Context Switching Costs:** Every interruption to answer a "quick question" breaks flow, costing estimated lost dev hours per week.

**Engineering Cost Impact:**
*   **Slower Incident Response:** Noise in oncall channels distracts from active fires.
*   **Delayed Delivery:** Senior engineers blocked by support-style questions.

---

## 3. Goals & Non-Goals

### Goals
*   **Reduce Oncall Load:** Automate responses to factual questions about code and schema.
*   **Democratize Knowledge:** Provide instant, shared understanding of the system to all stakeholders.
*   **Self-Serve for PMs/Analysts:** Enable non-engineers to verify logic and schema details without blocking devs.
*   **Production Safety:** Ensure zero risk to production data or stability.

### Non-Goals
*   **No Auto-Fixing:** The bot will not attempt to write code fixes or patch bugs.
*   **No Production DB Queries:** The bot will not execute arbitrary SQL against the production database.
*   **Not Replacing Cursor/IDEs:** This is a quick-access conversational interface, not a full development environment.
*   **Not Replacing Monitoring:** It will not replace New Relic, Datadog, or existing alerting tools.

---

## 4. Proposed Solution

We propose building a **Slack-based AI Assistant** with the following capabilities:

*   **Interface:** A standard Slack bot (`@NinjasBot`) available in engineering channels.
*   **Knowledge Base:** Read-only access to:
    *   The `NinjasTool` codebase (Rails).
    *   Database schema definitions (`schema.rb`).
    *   Migration history.
    *   Internal documentation.
*   **Core Function:** Translate natural language questions into accurate technical explanations using semantic search and LLM reasoning.

The solution focuses on **information retrieval and synthesis**, providing answers with citations to specific files and lines of code.

---

## 5. Target Users & Use-Case Categories

### 1. Product Managers (PMs)
*   **Value:** Instant clarification on existing business logic and feasibility checks.
*   **Use Case:** "How is the 'Super Ninja' discount currently calculated?"

### 2. Data Analysts
*   **Value:** Rapid navigation of complex database schemas and table relationships.
*   **Use Case:** "How connects `users` to `subscription_plans`?"

### 3. Oncall & Junior Engineers
*   **Value:** Faster triage, error tracing, and understanding legacy code without pinging seniors.
*   **Use Case:** "Where is the `PaymentFailed` event triggered?"

### 4. Senior Engineers
*   **Value:** Quick recall of obscure implementation details and reduced interruption.
*   **Use Case:** "What was the migration that added `risk_score` to users?"

---

## 6. System Architecture

The system follows a strict **Read-Only** architecture to ensure safety.

*   **Interaction Layer:** Slack Bot (using Slack Bolt framework) handles user messages and threads.
*   **Compute Layer:** AWS Lambda functions process requests (Serverless).
*   **Intelligence Layer:**
    *   **Orchestrator:** Python-based service manages the conversation flow.
    *   **AI Engine:** Gemini API (via `ai_service.py`) for natural language understanding and code synthesis.
    *   **Context Retrieval:** `query_service.py` performs safe, read-only searches against a local clone of the codebase.
*   **Memory:** Currently using in-memory storage (Lambda warm state) retaining the last 10 messages for context. This interface is modular and easily extendable to persistent storage (e.g., DynamoDB) as needed.

**Safety Boundaries:**
*   The system has **Network Isolation** where possible.
*   The "Execution" layer is strictly **Read-Only** on the file system level.

---

## 7. Security & Safety Considerations

This is the most critical aspect of the design. We operate on a **Zero-Trust** basis for write operations.

### Read-Only Enforcement
*   **File System:** The codebase copy accessed by the bot is mounted as Read-Only or permission-locked (`chmod -R a-w`) before any query execution.
*   **Database:** The bot has **NO access** to production database credentials. It can only read the `schema.rb` file and structure definitions, not actual customer data.

### Access Control & Auditing
*   **Auditing:** Every query and response is logged to CloudWatch/DynamoDB for review.
*   **Access Control:** The bot is restricted to internal Slack channels.

### AI Safety
*   **Prompt Injection:** System prompts explicitly instruct the model to ignore attempts to override safety rules.
*   **Hallucination Mitigation:** The bot is instructed to cite sources. If it cannot find the answer in the code, it is trained to say "I don't know" rather than guess.

---

## 8. Cost & Feasibility

We have designed this to be cost-effective and predictable using Serverless infrastructure.

### Infrastructure Costs (Monthly Estimates)

**Scenario A: Pilot (10 Users, ~10 queries/day)**
*   **AWS Lambda & API Gateway:** $0.00 (Well within AWS Free Tier of 1M requests/month).
*   **OpenAI API (GPT-4o-mini):** ~$1.50/month (assuming safe buffer of ~30k context/query).
*   **Cursor Subscription:** $20.00/month (Fixed cost for `cursor-agent` access).
*   **Total:** ~$22.00/month.

**Scenario B: Scale (50 Users, ~100 queries/day)**
*   **AWS Lambda & API Gateway:** Still <$2.00/month (exceeds free tier slightly if complex).
*   **OpenAI API (GPT-4o-mini):** Estimated ~$15–$20/month.
*   **Cursor Subscription:** $20.00/month (Fixed cost).
*   **Total:** <$45.00/month.

---

## 9. Expected Impact & Success Metrics

We will evaluate the success of this project after a **4-week pilot**.

### Metrics
1.  **Reduction in "Clarification" Pings:** Measured by qualitative survey of Senior Engineers.
2.  **Response Time:** Time saved per question (e.g., instant vs. 2-hour wait for a human).
3.  **Adoption:** Weekly Active Users (WAU) within the Engineering and Product org.
4.  **Accuracy:** Percentage of answers marked as "Helpful" via Slack reactions.

### Success Definition
*   > 50% of time saved of tech team answering Product team's doubts on current code flows.
*   > 50% of routine schema/logic questions are answered by the bot without human intervention.
*   Positive sentiment from the Oncall team regarding reduced noise.

---

## 10. Rollout Plan

We propose a phased rollout to minimize risk and gather feedback.

*   **Phase 1: Pilot (Weeks 1-2)**
    *   **Users:** Oncall Engineers + select PMs.
    *   **Scope:** Slack channel `#ask-ninjas-bot-beta`.
    *   **Goal:** Verify accuracy and safety; fix edge cases.

*   **Phase 2: Engineering General Availability (Weeks 3-4)**
    *   **Users:** All Engineering.
    *   **Scope:** Integration into main dev channels.
    *   **Goal:** Load testing and broader adoption.

*   **Phase 3: Org-Wide (Month 2+)**
    *   **Users:** Product, Data, Support.
    *   **Goal:** Self-serve enablement.

**Kill Switch:** We maintain a single environment variable to instantly disable the bot if any issues arise.

---

## 11. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **Incorrect Answers** | Bot is prompted to provide code citations. Users are educated to treat it as an "assistant," not an oracle. |
| **Prompt Injection** | Strict system prompts and separation of data/instruction layers. |
| **Over-reliance** | "Human in the loop" culture; bot answers are a starting point for critical decisions. |
| **Cost Spikes** | Usage alerts and hard limits on API spend. |

---

## 12. Alternatives Considered

*   **Status Quo (Human Response):** Not scalable; expensive use of senior time.
*   **Static Documentation (Wiki/Notion):** Quickly becomes outdated; search is often poor.
*   **Cursor/IDE AI (Individual):** Great for coding, but doesn't solve the "shared knowledge" or non-engineer access problem.
*   **Why Build vs. Buy?** Custom solution allows us to strictly control security boundaries (Read-Only) and integrate deeply with our specific Rails architecture at a fraction of the cost of enterprise AI platforms.

---

## 13. Appendix

*(Detailed examples of intended behavior)*

### A. PM Scenario: Feature Logic
**User:** "How do we currently determine if a user is eligible for the 'Student' plan?"
**Bot:** "According to `app/services/plan_eligibility_service.rb`, a user is eligible if:
1. They have a valid `.edu` email address (Line 45).
2. They are not currently on a 'Enterprise' plan (Line 52).
Code snippet:
```ruby
def student_eligible?
  email.end_with?('.edu') && !enterprise_plan?
end
```
"

### B. Analyst Scenario: Schema
**User:** "What table stores the user's last login time?"
**Bot:** "The `users` table contains a `last_sign_in_at` timestamp column. This is defined in `db/schema.rb`."

### C. Oncall Scenario: Debugging
**User:** "Where is the `SubscriptionExpired` email sent?"
**Bot:** "This is triggered in the `SubscriptionWorker` (`app/workers/subscription_worker.rb`), which calls `UserMailer.subscription_expired` on line 23."

