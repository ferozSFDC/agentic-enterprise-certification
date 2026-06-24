## Module 1: Why Agentic — The Enterprise Case

---

### Slide 1.1 — The Integration Problem Has Changed

Traditional integration solves: "System A needs data from System B."

Agentic integration solves: "A customer said something ambiguous, and we need to reason about it, check policy, look up their history, take action, and respond — all in under 5 seconds."

| Era | Pattern | Decision Maker |
|-----|---------|----------------|
| 2005 | Point-to-point | Developer (hardcoded) |
| 2015 | API-led connectivity | Process layer (orchestration logic) |
| 2025 | Agentic | AI model — constrained by enterprise policy |

The middleware didn't go away. It became the guardrails.

---

### Slide 1.2 — [VIDEO PLACEHOLDER] The Agent in Action

> **Demo video (2 min)**: Show the finished product. A user types a natural language refund request in Slack, the agent reasons about it, checks policy, creates a case in Service Cloud, and responds — all in real time. No slides can replace seeing this work.

---

### Slide 1.3 — What "Agentic" Means in an Enterprise Context

An agent is a system that can:
1. **Perceive** — ingest unstructured input (natural language, events)
2. **Reason** — decide what to do (intent extraction, risk assessment)
3. **Act** — execute operations on enterprise systems (create cases, issue refunds)
4. **Respond** — report back to the human in their channel

Enterprise constraints agents must respect:
- **Policy** — hard limits that override AI decisions (refund caps, velocity checks)
- **Identity** — act on behalf of verified users, not anonymous requests
- **Audit** — every decision traceable end-to-end with correlation IDs
- **Resilience** — degrade gracefully; never lose a customer request silently

---

### Slide 1.4 — Why MuleSoft for the Agent Backbone

The AI model is the brain. MuleSoft is the nervous system.

| Concern | Who Owns It |
|---------|-------------|
| "What should we do?" | The LLM (intent, reasoning, risk scoring) |
| "Are we allowed to?" | MuleSoft orchestrator (policy guards) |
| "How do we connect?" | MuleSoft connectors (Salesforce, Slack, Bedrock) |
| "What if it fails?" | MuleSoft resilience patterns (retry, circuit breaker, DLQ) |
| "Who asked?" | MuleSoft identity propagation (OBO headers, correlation IDs) |
| "Can we prove it?" | MuleSoft observability (structured logs, MDC, monitoring) |

You don't give the LLM a database connection. You give it tools — and MuleSoft is how you build those tools safely.

---

### Slide 1.5 — Where We're Headed

> [DIAGRAM — full-page, high-impact. This is the "north star" architecture participants will build toward. Revisit this slide at the start of each module to show progress.]

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│    👤 Slack User                                                        │
│      │                                                                   │
│      ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  EXPERIENCE LAYER                                                │    │
│  │  slack-agent-router                                              │    │
│  │  [Dedup] → [Extract Identity] → [Dispatch] → [Format Response] │    │
│  └─────────────────────────────┬───────────────────────────────────┘    │
│                                │                                         │
│  ┌─────────────────────────────▼───────────────────────────────────┐    │
│  │  PROCESS LAYER                                                   │    │
│  │  ai-orchestrator                                                 │    │
│  │  [AI Gateway] → [Intent] → [Risk] → [Policy Guard] → [Route]  │    │
│  └──────────┬──────────────────────────────────────┬───────────────┘    │
│             │                                      │                     │
│  ┌──────────▼──────────────┐    ┌──────────────────▼────────────────┐   │
│  │  SYSTEM LAYER           │    │  SYSTEM LAYER                     │   │
│  │  data-cloud-sapi        │    │  service-cloud-mcp                │   │
│  │  [Customer 360 Context] │    │  [Case Create / Opp Update]      │   │
│  └──────────┬──────────────┘    └──────────────────┬────────────────┘   │
│             │                                      │                     │
│  ┌──────────▼──────────────┐    ┌──────────────────▼────────────────┐   │
│  │  Salesforce Data Cloud  │    │  Salesforce Service Cloud         │   │
│  └─────────────────────────┘    └───────────────────────────────────┘   │
│                                                                          │
│            ┌───────────────────────────┐                                 │
│            │  Amazon Bedrock (via      │                                 │
│            │  MuleSoft AI Gateway)     │                                 │
│            └───────────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

By the end of this course, you will have built every box in this diagram.

---

### Slide 1.6 — API-Led Connectivity — Still the Foundation

| Layer | Traditional Role | Agentic Role |
|-------|-----------------|--------------|
| Experience | Expose data for a channel (mobile, web) | Adapt a human channel (Slack) into structured requests |
| Process | Orchestrate + transform | Orchestrate + **reason** + enforce policy |
| System | Wrap a backend system | Expose backend as a **tool** the AI can invoke |

**Rule**: Experience never calls System directly.  
**Rule**: System APIs never decide — they execute.  
**Rule**: The Process layer owns "should we do this?"

The layers haven't changed. The intelligence moved into the Process layer.

---

### Slide 1.7 — MCP: How the AI Discovers Available Actions

> [DIAGRAM — show the AI model "reading" tool schemas like a menu, then selecting which tool to invoke]

**Model Context Protocol (MCP)** makes each System API a "tool" the AI model can invoke.

```yaml
tools:
  - name: get_customer_profile
    description: "Retrieve loyalty tier and churn risk for a customer"
    inputSchema:
      type: object
      required: [email]
      properties:
        email: { type: string, format: email }

  - name: issue_credit
    description: "Issue a refund/credit to a customer account"
    inputSchema:
      type: object
      required: [customerId, amount, reason, orderId]
      properties:
        customerId: { type: string }
        amount: { type: number, maximum: 500 }
        reason: { type: string, enum: [defective, late_delivery, wrong_item] }
```

The AI reads the schema. It decides which tool to call and with what parameters. MuleSoft executes the call safely.

---

### Slide 1.8 — Security Model: On-Behalf-Of (OBO) Identity

> [DIAGRAM — horizontal flow showing identity propagation from Slack user through all layers, each arrow labeled with the header]

```
👤 Sarah Chen (sarah.chen@globaltech.com)
  │
  │ Slack event (user_id: U0AA9JSR2AD)
  ▼
┌──────────────────────────────┐
│ slack-agent-router           │  ← calls Slack API: users.info → gets email
│ x-obo-user-id: sarah.chen@  │
│ x-request-id: uuid-1234     │
│ x-flow-id: thread-5678      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ ai-orchestrator              │  ← same headers propagated
│ x-obo-user-id: sarah.chen@  │
└──────┬───────────────┬───────┘
       ▼               ▼
┌──────────────┐ ┌─────────────┐
│data-cloud-sapi│ │service-cloud│  ← queries/actions scoped to THIS user
│ WHERE email= │ │ ContactId=  │
│ sarah.chen@  │ │ (her record)│
└──────────────┘ └─────────────┘
```

Every log line, every query, every action — attributable to a specific human.

---

### Slide 1.9a — Agent Fabric: Bring Any Agent Under Control

> [VIDEO REFERENCE: "What's New with Agent Fabric: From Guided Determinism to Governance Controls" — MuleSoft Videos, Apr 14 2026, https://www.youtube.com/watch?v=jWwgboa_z8Y]

The architecture you are building in this course is one implementation of a broader Salesforce/MuleSoft principle:

**"Bring any agent, tool, and model under control with trusted technology."**

Agent Fabric is the enterprise control plane that makes this real:

| Fabric capability | What it governs |
|-------------------|-----------------|
| **Agents catalog** | Every AI agent across all clouds — discovered, versioned, documented |
| **MCP Servers** | Tool contracts any agent can consume |
| **LLMs** | Which models are in use, by whom, at what cost |
| **Gateways** | AI Gateway instances enforcing policy at the API surface |
| **Governance** | Trust Center + Governance Strategy — policy applied to agents |
| **Observability** | Token usage dashboards, cost attribution by business unit, latency SLA tracking |

As of launch (Sep 2025), Agent Fabric has managed **thousands of agents** across enterprises — all built on the same platform, running in different clouds.

> The four-app stack in this course (slack-agent-router, ai-orchestrator, data-cloud-sapi, service-cloud-mcp) is a single entry in an Agent Fabric catalog that may contain hundreds of agents.

---

### Slide 1.9 — Design Principles (Non-Negotiable)

These six principles govern every decision in this course:

1. **Fail safe, not silent** — every error reaches the user with a friendly message
2. **Deterministic guardrails over AI** — policy rules override LLM suggestions, always
3. **Idempotent by default** — retries must never create duplicate actions
4. **Observable end-to-end** — correlation IDs from first event to last log line
5. **Secure by construction** — secrets encrypted, TLS enforced, properties externalized
6. **Same artifact, different config** — one build, promoted across environments

> When in doubt about any implementation decision, ask: "Which principle does this serve?"

---
