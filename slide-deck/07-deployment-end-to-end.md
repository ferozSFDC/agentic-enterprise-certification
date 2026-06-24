## Module 7: Deployment and End-to-End Validation

---

### Slide 7.1 — Where We Are

> [DIAGRAM — full north-star architecture, all layers lit up. No greying out. Label: "Everything you've built."]

You have built six independent components. This module wires them together and proves the full flow works.

| Component | What it does | Built in |
|-----------|-------------|----------|
| slack-agent-router | Experience layer — Slack → structured request | Module 3 |
| ai-orchestrator | Process layer — reason, risk, policy, route | Module 5 |
| data-cloud-sapi | System layer — Customer 360 profile | Module 6 |
| service-cloud-mcp | System layer — Case creation, Opportunity update | Module 6 |
| Bedrock Agent | AI decision engine — fraud scoring | Module 4 |
| AI Gateway | Governed LLM access — field extraction | Module 4 |

---

### Slide 7.2 — The Four Deployment Targets

```
┌─────────────────────────────────────────────────────────┐
│  CloudHub 2.0 — Shared Space: agentic-enterprise-training│
│                                                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │  slack-agent-router        port 443 (public)      │   │
│  │  ai-orchestrator           port 443 (public)      │   │
│  │  data-cloud-sapi           port 443 (internal)    │   │
│  │  service-cloud-mcp         port 443 (internal)    │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  Omni Gateway (Flex Gateway)                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Agent and Tool Instance (/llmproxy2)             │   │
│  │  → bedrock-runtime (Claude Haiku, field extraction│   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Public endpoints** (Slack must reach them): `slack-agent-router`
**Internal endpoints** (only called by other Mule apps): `data-cloud-sapi`, `service-cloud-mcp`
**Both**: `ai-orchestrator` (called by router, calls system APIs)

---

### Slide 7.3 — Deployment Order Matters

Dependencies flow downward. Deploy in this order:

```
1. data-cloud-sapi        (no Mule dependencies — calls Salesforce Data Cloud only)
2. service-cloud-mcp      (no Mule dependencies — calls Salesforce Service Cloud only)
3. ai-orchestrator        (depends on data-cloud-sapi and service-cloud-mcp)
4. slack-agent-router     (depends on ai-orchestrator and AI Gateway)
```

If you deploy out of order, the earlier apps start with broken downstream references — they will error on the first call but won't fail to start (HTTP request configs are lazy).

**Verification after each deploy:**
- Each app exposes `GET /health` → `{"status":"ok","app":"<app-name>"}`
- The `ai-orchestrator` readiness endpoint (`GET /health/ready`) scatter-gathers health checks for all downstream apps

---

### Slide 7.4 — Property Strategy: What Goes Where

| Property type | Where it lives | Example |
|--------------|---------------|---------|
| Non-sensitive defaults | `shared-config.yaml` in the JAR | `http.pool.maxConnections=10` |
| Environment-specific hosts | `dev-config.yaml` in the JAR | `data-cloud.host=data-cloud-sapi-835dgu...` |
| Secrets — CloudHub | Runtime Manager → Properties (encrypted) | `aws.accessKeyId`, `sfdc.clientSecret` |
| Secrets — local | `wrapper.conf` additional properties | Same keys, local values |

**The rule**: the same artifact (JAR) deploys everywhere. Secrets are never in source control.

```
pom.xml <properties>           ← non-secret build-time config only
shared-config.yaml             ← non-secret runtime defaults
dev-config.yaml / prod-config.yaml ← non-secret per-env overrides
CloudHub Runtime Properties    ← ALL secrets
wrapper.conf (local only)      ← ALL secrets for local dev
```

---

### Slide 7.5 — CloudHub 2.0: What the mule-maven-plugin Sends

The `mule-maven-plugin` `<cloudhub2Deployment>` block controls deployment:

```xml
<cloudhub2Deployment>
    <environment>Sandbox</environment>
    <target>agentic-enterprise-training</target>      <!-- Shared Space name -->
    <applicationName>slack-agent-router</applicationName>
    <replicas>1</replicas>
    <vCores>0.1</vCores>                              <!-- 0.1 vCore = Micro -->
    <deploymentSettings>
        <generateDefaultPublicUrl>true</generateDefaultPublicUrl>
    </deploymentSettings>
    <properties>
        <!-- non-secrets only — secrets patched via Runtime Manager after deploy -->
        <env>dev</env>
        <ai-gateway.host>${ai-gateway.host}</ai-gateway.host>
        ...
    </properties>
</cloudhub2Deployment>
```

**After deploy**: patch secrets via Runtime Manager UI or REST API:
```bash
PATCH /amc/application-manager/api/v2/.../deployments/{id}
Body: { "configuration": { "mule.agent.application.properties.service": {
    "applicationName": "slack-agent-router",
    "properties": { "slack.botToken": "xoxb-...", "ai-gateway.clientSecret": "..." }
}}}
```

---

### Slide 7.6 — The Critical Property Map

Every property the apps pass across the wire at runtime:

```
slack-agent-router → ai-orchestrator
  Header: x-user-id          ← Slack user ID
  Header: x-request-id       ← UUID per event
  Header: x-flow-id          ← = requestId at origin
  Header: x-session-id       ← Slack thread_ts
  Header: x-source-app       ← "slack-agent-router"
  Body:   contractVersion, requestId, flowId, sessionId,
          structured.orderNumber, structured.reason

ai-orchestrator → data-cloud-sapi
  Header: x-user-id, x-flow-id, x-request-id, x-session-id
  Path:   /api/profile/{userId}

ai-orchestrator → service-cloud-mcp
  Header: x-user-id, x-flow-id, x-request-id, x-session-id
  Body:   customerId, orderNumber, reason, amount, fraudScore,
          product, amountSource

ai-orchestrator → AI Gateway (/llmproxy2/chat/completions)
  Header: client_id, client_secret
  Body:   {model, messages, max_tokens} (OpenAI chat format)
```

---

### Slide 7.7 — The Complete Request Flow

```
👤 Sarah types: "@agent refund ORD-789 wrong item"
│
▼
┌──────────────────────────────────────────────────────────┐
│  1. slack-agent-router                                    │
│     • Dedup check (SlackEventDedupeStore)                │
│     • AI Gateway extraction → orderNumber=ORD-789,       │
│       reason="wrong item"                                │
│     • Opens Slack confirmation modal                     │
│     • Sarah clicks Confirm                              │
│     • Posts "🎬 Initializing refund mission control..." │
│     • Sends canonical payload to ai-orchestrator        │
└───────────────────────┬──────────────────────────────────┘
                        │ POST /api/orchestrate
                        ▼
┌──────────────────────────────────────────────────────────┐
│  2. ai-orchestrator                                       │
│     Stage 1: validate-identity (x-user-id present?)     │
│     Stage 2: enrich-customer-profile                     │
│              └─ GET data-cloud-sapi /profile/{userId}   │
│     Stage 3: resolve-intent-and-order                    │
│              ├─ intent=REFUND_REQUEST                    │
│              ├─ orderNumber=ORD-789                      │
│              └─ refundAmount from Salesforce SOQL       │
│     Stage 4: assess-risk                                 │
│              └─ POST AI Gateway /llmproxy2/chat/completions│
│                 → decision=APPROVE, riskLevel=SAFE       │
│     Stage 5: enforce-policy                              │
│              └─ allowMutation=true (all gates pass)     │
│     Stage 6: execute-mutation                            │
│              └─ POST service-cloud-mcp /tool/issue_credit│
└───────────────────────┬──────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
┌─────────────────────┐  ┌─────────────────────────┐
│  3. data-cloud-sapi │  │  4. service-cloud-mcp   │
│  Returns:           │  │  Creates: Case          │
│  customerTier=Gold  │  │  Updates: Opportunity   │
│  churnRisk=HIGH     │  │  Returns: caseId        │
└─────────────────────┘  └─────────────────────────┘
                        │
                        ▼
              ai-orchestrator builds response
              → decision=APPROVE, caseId=5004K...
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│  5. slack-agent-router (Slack chat.update)               │
│     "*Refund decision:* APPROVE                         │
│      *Risk:* SAFE (score 14)                            │
│      *Case Reference:* 5004K000001AbCd"                 │
└──────────────────────────────────────────────────────────┘
```

---

### Slide 7.8 — Verification Sequence

Run these in order after a full deploy:

**Step 1 — Health checks (each app)**
```bash
curl https://{app-host}/health   # → {"status":"ok","app":"<app-name>"}
```

**Step 2 — Orchestrator readiness (all downstream)**
```bash
curl https://{orchestrator-host}/health/ready
# → {"dataCloud":"UP","serviceCloud":"UP"}
```

**Step 3 — AI Gateway field extraction**
```bash
curl -X POST https://{gateway-host}/llmproxy2/chat/completions \
  -H "client_id: {clientId}" -H "client_secret: {clientSecret}" \
  -H "Content-Type: application/json" \
  -d '{"model":"us.anthropic.claude-3-haiku-20240307-v1:0",
       "messages":[{"role":"user","content":"refund order ORD-123 wrong item"}],
       "max_tokens":100}'
# → choices[0].message.content contains {"orderNumber":"ORD-123","reason":"wrong item"}
```

**Step 4 — Direct orchestrator call (bypassing Slack)**
```bash
curl -X POST https://{orchestrator-host}/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: testuser" \
  -d '{"contractVersion":"1.2","requestId":"test-001","flowId":"test-001",
       "sessionId":"test-001","inputText":"refund order ORD-999 wrong item",
       "structured":{"orderNumber":"ORD-999","reason":"wrong item"}}'
# → {"response":"...","metadata":{"decision":"APPROVE","stageStatus":{"dataCloud":"OK",...}}}
```

**Step 5 — Fraud block (999-prefix)**
```bash
# Same as Step 4 but orderNumber: "999-001"
# → metadata.decision = "ESCALATE", metadata.riskLevel = "CRITICAL"
```

**Step 6 — Full Slack flow**
- Type `@agent refund ORD-789 wrong item` in Slack
- Confirm modal → check for pipeline view update in thread

---

### Slide 7.9 — Reading the Pipeline View in Slack

After a successful orchestration, Slack shows:

```
*Refund decision:* APPROVE
*Reason:* wrong item
*Risk:* SAFE (score 14)
*Credit action:* Issue credit
*Case Reference:* 5004K000001AbCd

*End-to-end flow trace*
*Pipeline view*
🧠 *AI Orchestrator* ✅ OK
  • gateway completed
⬇️
☁️ *Data Cloud SAPI* ✅ OK
  • data cloud stage completed
⬇️
🛠️ *Service Cloud MCP* ✅ OK
  • service cloud stage completed
```

The `stageStatus` in the response metadata drives the badges:
- `OK` / `SUCCESS` → ✅
- `SKIPPED` → ⏭️
- `FAILED` / `ERROR` → ❌
- anything else → ⚪

---

### Slide 7.10 — What Degraded Looks Like

| Scenario | stageGateway | stageDataCloud | stageServiceCloud | Decision |
|----------|-------------|----------------|-------------------|---------|
| All healthy | OK | OK | OK | APPROVE |
| AI Gateway down (circuit open) | DEGRADED | OK | OK | APPROVE (via direct Bedrock SDK) |
| Bedrock also down | DEGRADED | OK | SKIPPED | ESCALATE (mimic fallback) |
| Data Cloud down | OK | FAIL | OK | APPROVE (fallback profile: Standard/UNKNOWN) |
| Service Cloud down | OK | OK | FAIL | CLARIFY (caseId=null, DLQ written) |
| Identity missing | SKIPPED | SKIPPED | SKIPPED | CLARIFY (identity guard fires first) |

The orchestrator always returns a usable response. The `failureClassification` field explains what went wrong.

---

### Slide 7.11 — [VIDEO PLACEHOLDER] Full End-to-End Demo

> **Screencast (6 min)**: Show the full flow from Slack message to Slack response.
> 1. Type a safe refund request → confirm modal → APPROVE with Case reference
> 2. Type a fraudulent 999-prefix order → ESCALATE response
> 3. Open CloudHub logs — show the `telemetry stage=FINAL` log line with all fields
> 4. Open Salesforce — show the Case created and Opportunity updated
> 5. Simulate AI Gateway failure (change `ai-gateway.clientSecret` to wrong value) → show DEGRADED fallback still returns a decision

---

### Slide 7.12 — Module Summary: What You've Built

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  slack-agent-router    ← Slack event dedup, AI extraction,  │
│  (Experience)             modal, circuit breaker, OBO       │
│       │                                                      │
│       ▼                                                      │
│  ai-orchestrator       ← 6-stage pipeline, Bedrock,        │
│  (Process)                policy engine, DLQ, 5 OS stores  │
│       │                                                      │
│  ┌────┴─────┐                                               │
│  ▼          ▼                                               │
│  data-cloud-sapi   service-cloud-mcp                        │
│  (System)          (System)                                 │
│  Customer 360      Case + Opportunity                       │
│  via Data Cloud    via Service Cloud                        │
│       │                   │                                 │
│  ┌────┘                   └────┐                            │
│  ▼                             ▼                            │
│  Salesforce Data Cloud    Salesforce Service Cloud          │
│                                                             │
│  Amazon Bedrock ←── AI Gateway (Omni Gateway, /llmproxy2)  │
│  MuleSoft-Returns-Agent    Agent Scanner (Exchange)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**15 MuleSoft features implemented. 4 apps. 1 working agent.**

---
