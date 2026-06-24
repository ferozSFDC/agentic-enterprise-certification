## Module 4: The Process Layer — AI Gateway and Amazon Bedrock

---

### Slide 4.1 — Where We Are

> [DIAGRAM — north star architecture, highlight the Process Layer (ai-orchestrator) and the AI Gateway / Amazon Bedrock box. Grey out Experience and System layers. Label: "You are here."]

You've built the foundation (Salesforce) and the front door (Slack). Now we build the **brain** — the AI reasoning layer that decides whether to act or deny.

---

### Slide 4.2 — The Backstory: Why AWS for Fraud Detection

Enterprise reality: the fraud engine lives where the data lives.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  10 years of call center data                           │
│  ├── Refund velocity patterns                           │
│  ├── Account behavior baselines                         │
│  ├── Known fraud signatures                             │
│  └── IP/device fingerprints                             │
│                                                         │
│  This data already lives in AWS.                        │
│  Moving it to Salesforce? Not happening.                │
│  Training a model on it? Already done (Bedrock).        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The agent doesn't replace your fraud team. It **consults** the fraud engine the same way a human agent would — but in milliseconds.

---

### Slide 4.3 — Amazon Bedrock: What It Is (and Isn't)

| What Bedrock IS | What Bedrock ISN'T |
|-----------------|-------------------|
| Managed service for foundation models | A single model |
| Agent framework with tool calling | An API gateway |
| Action Groups that invoke Lambda | A workflow engine |
| Multi-model access (Claude, Titan, etc.) | A training platform (that's SageMaker) |

**Bedrock Agent** = Foundation Model + Instructions + Action Groups

```
┌─────────────────────────────────────────────┐
│  Bedrock Agent: MuleSoft-Returns-Agent       │
│                                              │
│  Model: Claude Sonnet                        │
│  Instructions: "You are a returns agent..."  │
│                                              │
│  Action Groups:                              │
│  ├── Fraud_Scorer  → Lambda function         │
│  └── Process_Refund → Lambda function        │
│                                              │
│  Alias: Production-v1 → Version 3            │
└─────────────────────────────────────────────┘
```

---

### Slide 4.4 — Enforced Tool Ordering: The Agent's Constitution

> [DIAGRAM — decision flow chart showing mandatory Fraud_Scorer → gate → Process_Refund path]

The agent's instructions create a **hard sequencing rule**:

```
User: "Refund order ORD-123, wrong item"
         │
         ▼
┌─────────────────────────┐
│ 1. MUST call Fraud_Scorer │
│    orderNumber: ORD-123   │
└────────────┬────────────┘
             │
         ┌───▼───┐
         │ SAFE? │
         └───┬───┘
        Yes  │       No (CRITICAL)
         ┌───▼───┐       ┌──────────────────┐
         │       │       │ DENY the refund.  │
         │       │       │ Explain velocity  │
         │       │       │ anomaly to user.  │
         └───┬───┘       └──────────────────┘
             │
┌────────────▼────────────┐
│ 2. Call Process_Refund    │
│    reason: "wrong item"   │
│    orderNumber: ORD-123   │
└────────────┬────────────┘
             │
             ▼
    "Your refund is confirmed."
```

**Key insight**: The model enforces this sequencing through natural-language instructions — no code required for orchestration logic. The instructions ARE the policy.

---

### Slide 4.5 — The Lambda Response Contract

Bedrock Action Groups speak a strict protocol:

```python
# What Bedrock SENDS to your Lambda:
{
    "messageVersion": "1.0",
    "actionGroup": "Fraud_Scorer_Group",
    "function": "Fraud_Scorer",
    "parameters": [
        {"name": "orderNumber", "type": "string", "value": "ORD-123"}
    ]
}

# What your Lambda MUST return:
{
    "messageVersion": "1.0",
    "response": {
        "actionGroup": "Fraud_Scorer_Group",
        "function": "Fraud_Scorer",
        "functionResponse": {
            "responseBody": {
                "TEXT": {"body": "{\"riskScore\": 14, \"riskLevel\": \"SAFE\"}"}
            }
        }
    }
}
```

| Rule | Consequence of Breaking |
|------|------------------------|
| `messageVersion` must be `"1.0"` | Agent fails silently |
| `responseBody` must be under `TEXT.body` | Agent gets no data |
| Body must be a JSON **string** (stringified) | Agent can't parse structured data |
| `actionGroup` + `function` must echo back | Response misrouted |

---

### Slide 4.6 — Two Bedrock Paths: Why Both Exist

> [DIAGRAM — show both paths side by side from the MuleSoft apps to Bedrock]

```
PATH 1: Foundation Model (via AI Gateway)          PATH 2: Agent Invocation (via AWS SDK)
────────────────────────────────────────           ────────────────────────────────────────
slack-agent-router                                 ai-orchestrator
  → Omni Gateway (/llmproxy2)                       → BedrockDirectInvoker (Java)
    → Client-ID-Enforcement ✓                         → InvokeAgent API (streaming)
    → SigV4 credential signing ✓                      → Agent triggers Action Groups
    → Message logging ✓                               → Fraud_Scorer Lambda fires
    → bedrock-runtime (Claude Haiku)                  → Agent returns decision
    → Response: extracted JSON fields                 → Response: APPROVE/DENY/ESCALATE

Purpose: Parse user messages                       Purpose: Make fraud decisions
Speed: ~1s (small model, simple task)              Speed: ~5-10s (agent loop, Lambda calls)
Governed by: AI Gateway policies                   Governed by: Scanner (visibility/audit)
```

**Why not run everything through the AI Gateway?**

The InvokeAgent API uses a streaming protocol with multi-turn tool calling (Action Groups → Lambda → results → more reasoning). The AI Gateway's LLM Proxy speaks OpenAI-compatible `chat/completions` — it forwards prompts and returns completions. It cannot broker the agent conversation loop.

**The AI Gateway governs what it can**: model access, credential management, rate limiting, logging.
**Scanner governs the rest**: visibility, metadata, compliance, continuous sync.

---

### Slide 4.6b — The AI Gateway: Same Pattern as API Manager

> [DIAGRAM — side-by-side: API Manager for REST APIs vs. AI Gateway for LLM calls]

```
REST API governance (you already do this):    AI governance (same pattern):
──────────────────────────────────────────    ──────────────────────────────
App → API Manager → Salesforce REST API       App → AI Gateway → Bedrock model
• Client-ID-Enforcement                       • Client-ID-Enforcement
• Rate limiting                               • Rate limiting
• Request/response logging                    • Message logging
• Centralized credentials                     • AWS SigV4 signing centralized
• Contract in Exchange                        • Contract in Exchange
```

**Configuration:**

| Section | Controls |
|---------|----------|
| **Runtime** | Which Omni Gateway to deploy on |
| **Downstream** | Base path (`/llmproxy2`), port, Client-ID enforcement |
| **Upstream** | Bedrock runtime URL, AWS credentials, region, target model |

---

### Slide 4.6c — Governance Policies: The Policy Library

> [VIDEO REFERENCE: ~3:40 in "What's New with Agent Fabric" https://www.youtube.com/watch?v=jWwgboa_z8Y]

Agent Fabric ships a **policy library** you apply to any Agent or Tool Instance. The same governance UI used for REST API Manager governs AI agents.

**Access and Security policies:**

| Policy | Severity | What it enforces |
|--------|----------|-----------------|
| Perimeter Defense & Threat Mitigation | — | Network-level blocking |
| PII Handling Standard | Critical | Requires masking/encryption of personally identifiable information |
| Input Validation Required | High | All user inputs validated and sanitised before processing |
| Basic Authentication | High | Usernames/password authentication for API access |
| Secret Rotation Policy | High | API keys and secrets must be rotated every 90 days |
| **OAuth 2.0 OBO Credential Injection** | High | Exchanges incoming bearer token for a new token targeting an upstream service using OAuth 2.0 Token Exchange — **this is the policy that enforces OBO in our stack** |

**Performance and Cost policies:**

| Policy | Severity | What it enforces |
|--------|----------|-----------------|
| Rate Limiting | Medium | Enforces rate limits to prevent abuse |
| Cost Threshold Alert | Medium | Triggers when daily cost exceeds configured threshold |
| Latency SLA Enforcement | High | Alerts on SLA breaches |

> In our stack, the AI Gateway already enforces Client-ID-Enforcement. These Fabric governance policies would be applied at the Agent/Tool Instance level for enterprise-grade deployments.

---

### Slide 4.7 — Agent Scanner: From Sprawl to Visibility

> [DIAGRAM — multiple clouds (AWS, GCP, Azure) with agents scattered across them → single funnel → Anypoint Exchange with organized assets]
> [VIDEO REFERENCE: ~3:00 in "What's New with Agent Fabric" https://www.youtube.com/watch?v=jWwgboa_z8Y — shows Amazon scanner with 6 scanners, 169 services discovered]

Enterprises don't have one AI agent. They have dozens — scattered across teams and clouds. **Nobody knows the full picture.**

**Agent Scanner** answers: "What AI agents exist in our enterprise?"

```
┌─────────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│ AWS Bedrock          │     │              │     │ Anypoint Exchange    │
│ • MuleSoft-Returns   │────▶│   Scanner    │────▶│ • What model?        │
│ • PurchaseHistory    │     │  (daily run) │     │ • What instructions? │
│ • FraudAnalyzer      │     │              │     │ • What can it access?│
├─────────────────────┤     └──────────────┘     │ • Version & status   │
│ Google Vertex AI     │────▶     ...       ────▶│ • Endpoint URL       │
│ • RecommendationBot  │                          │ • Last updated       │
└─────────────────────┘                           └─────────────────────┘
```

| Scanner Behavior | Detail |
|-----------------|--------|
| Frequency | Once daily (automatic) + on-demand |
| Discovery | Extracts agent metadata, LLM used, skills, endpoints |
| Sync | Overwrites Exchange metadata with source-of-truth values |
| Capacity | Up to 1,200 services per scan |
| Retention | Scan logs retained 90+ days |
| Protocol classification | A2A (Vertex AI, Snowflake) or "other" (Bedrock, Copilot) |

**What Scanner IS**: Enterprise-wide AI visibility, compliance, metadata sync.

**What Scanner IS NOT**: An invocation gateway. Bedrock agents use AWS's InvokeAgent API (not A2A protocol). Scanner catalogs them — it doesn't create a callable endpoint.

**The scanner makes the invisible visible.** If a team in another business unit deploys a new Bedrock agent, it appears in your registry on the next scan — with its model, instructions, and capabilities documented automatically.

---

### Slide 4.8 — The IAM Principle: Two Policies, Two Purposes

```
┌─────────────────────────────────────────────────────────┐
│  IAM User: mulesoft-bedrock-user                         │
│                                                          │
│  Policy 1: AmazonBedrockFullAccess (AWS Managed)         │
│  └── Full Bedrock access for agent creation/testing      │
│                                                          │
│  Policy 2: bedrock_for_scanner (Custom)                  │
│  └── Least-privilege for MuleSoft scanner discovery:     │
│      • bedrock:ListAgents                                │
│      • bedrock:GetAgent                                  │
│      • bedrock:ListAgentAliases                          │
│      • bedrock:GetAgentAlias                             │
│      • bedrock:InvokeModel                               │
│      • bedrock:InvokeAgent                               │
└─────────────────────────────────────────────────────────┘
```

**Production rule**: Drop `AmazonBedrockFullAccess` and use ONLY the custom policy. Full access is for training environments where you're building agents.

---

### Slide 4.8b — Token Cost Observability

> [VIDEO REFERENCE: ~7:00 in "What's New with Agent Fabric" https://www.youtube.com/watch?v=jWwgboa_z8Y]

Agent Fabric's Observability dashboard gives enterprise-wide LLM cost attribution:

```
TOTAL TOKENS       INPUT TOKENS       OUTPUT TOKENS
  1,014.0M (+10%)    771.7M (+9%)       242.3M (+12%)

Token Usage by Provider:          Token Distribution by Model:
  AWS Bedrock    244.0M              Nova Premier          17%
  Anthropic      151.0M              Claude 3.5 Haiku      17%
  Azure          140.0M              Mistral Codestral     17%
  Mistral        134.4M              Voyage AI Embeddings  17%
  Google         117.9M              Claude 3.5 Sonnet     17%
  xAI            ...                 Claude 3 Opus         16%
```

The platform answers the question: **"Which business groups are these costs coming from?"** — breaking down token spend by provider, model, and business unit across all agents running in the enterprise.

> This matters for our stack: ai-orchestrator calls Bedrock (agent invocation), slack-agent-router calls Bedrock (via AI Gateway for field extraction). Both show up as separate cost line items in this dashboard.

---

### Slide 4.9 — [VIDEO PLACEHOLDER] Bedrock Agent + AI Gateway in Action

> **Screencast video (4 min)**: Walk through the Bedrock console — show the agent's instructions, test it with a safe order (shows Fraud_Scorer → Process_Refund), test with a 999 order (shows denial). Then switch to Anypoint — show the LLM Proxy configuration, the Scanner discovering the agent, and the Exchange asset card with auto-generated metadata.

---

### Slide 4.10 — What Can Go Wrong

| Failure | Silent? | Root Cause | Prevention |
|---------|---------|-----------|------------|
| Agent skips Fraud_Scorer | Yes (sometimes) | Instructions not clear enough | Use MANDATORY/MUST/NEVER language |
| Lambda returns wrong format | Yes | Missing `messageVersion` or wrong body structure | Test with Bedrock's test panel first |
| Scanner finds 0 agents | No (shows count) | Agent not in PREPARED status | Prepare agent before scanning |
| LLM Proxy 403 | No | AWS credentials expired or wrong | Verify keys in Outbound tab |
| Agent alias points to old version | Yes | Alias not updated after agent changes | Create new alias or update existing |
| "Connection failed" on scanner | No | Wrong region or invalid keys | Match region exactly (us-east-2 not us-east-1) |

---

### Slide 4.11 — Exercise Time

## Exercise 3: AWS Bedrock Agent + MuleSoft AI Gateway

**What you'll build:**
- IAM user with AmazonBedrockFullAccess + custom scanner policy
- Lambda function: deterministic fraud scoring (SAFE vs. CRITICAL based on order prefix)
- Bedrock Agent with enforced tool ordering (Fraud_Scorer → Process_Refund)
- Agent and Tool Instance on Omni Gateway (Downstream/Upstream/Route configuration)
- Agent Scanner discovering and publishing the agent to Exchange

**What you'll prove works before leaving this exercise:**
- Lambda returns correct risk assessments for safe and fraudulent orders
- Agent ALWAYS calls Fraud_Scorer before Process_Refund
- Agent DENIES refunds when fraud is detected
- AI Gateway responds to `POST /llmproxy2/chat/completions` with extracted fields
- Client-ID-Enforcement rejects unauthenticated requests (401)
- Scanner successfully imports agent to Exchange registry

**Time**: ~60 minutes

> **Open**: `exercise-guide/03-aws-bedrock-ai-gateway.md`

---
