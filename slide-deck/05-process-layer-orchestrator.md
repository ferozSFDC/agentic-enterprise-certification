### Slide 5.1 — Module 5: The Process Layer

**ai-orchestrator** — the decision engine that turns a Slack message into a governed credit mutation.

```
Port 8081  POST /api/orchestrate
```

This module does not repeat the Bedrock setup from Module 4 or the Slack event pipeline from Module 3.
It focuses on what sits between them: the code that validates identity, enriches context, infers intent,
calls AI, enforces policy, and either issues a Service Cloud credit or sends a structured refund to a
dead-letter queue for manual replay.

By the end of this module you will have built every file in `ai-orchestrator/src/main/mule/` and
`src/main/resources/dw/` from scratch.

---

### Slide 5.2 — Where ai-orchestrator sits

```
Slack              slack-agent-router          ai-orchestrator         data-cloud-sapi
 User               (port 8081)                 (port 8082)             (port 8083)
  |                      |                           |                       |
  |-- Slack event ------->|                          |                       |
  |                       |-- POST /api/orchestrate ->|                      |
  |                       |                           |-- GET /profile/{id} ->|
  |                       |                           |                       |
  |                       |                    Amazon Bedrock AI Gateway      |
  |                       |                           |-- POST /llmproxy ---> |
  |                       |                           |                  service-cloud-mcp
  |                       |                           |-- POST /tool/issue_credit -> |
  |                       |<------- JSON response ----|
  |<-- Slack message ------|
```

**API-led position:** Process layer. Consumes two System APIs (`data-cloud-sapi`, `service-cloud-mcp`)
and one platform service (AI Gateway). Consumed by one Experience API (`slack-agent-router`).

---

### Slide 5.2b — Guided Determinism: Not Every Step Needs to Be Agentic

> [VIDEO REFERENCE: ~5:00–5:30 in "What's New with Agent Fabric" https://www.youtube.com/watch?v=jWwgboa_z8Y]

> **"It's become clear that not every step in a process needs to be fully agentic."** — MuleSoft, Apr 2026

This is the design philosophy behind ai-orchestrator. The pipeline uses AI precisely where reasoning is valuable, and deterministic logic everywhere else.

```
Ticket arrives
     │
     ▼
[REASONING step]          ← AI classifies severity (fast, cheap model)
Classify Severity
     │
     ▼
[DETERMINISTIC step]      ← Switch routes by severity (no AI needed here)
Severity Router
     │
     ├─── High ──────────▶ [DETERMINISTIC] Execute: Escalate Ticket
     │
     ├─── Low ───────────▶ [AGENTIC] Orchestration: Cross-Platform Triage
     │                         LLM: gemini-pro
     │                         MCP Tools: jiraMcp
     │                         Sub-agents: helpCenterAgent, licenseProcurementAgent
     │
     └─── Needs Info ────▶ [GENERATIVE] Generate: More Info Message
```

**The pattern in our ai-orchestrator:**

| Stage | Type | Why |
|-------|------|-----|
| validate-identity | Deterministic | Identity is binary — present or not |
| enrich-customer-profile | Deterministic | Cache lookup / HTTP call |
| resolve-intent-and-order | AI reasoning | Natural language → structured fields |
| assess-risk | Deterministic (+ Bedrock agent) | Bedrock *enforces* tool order, not free-form |
| enforce-policy | Deterministic | Rules are binary — amount ≤ cap or not |
| execute-mutation | Deterministic | Call Service Cloud MCP tool |

**AI is used in exactly two places**: intent resolution and risk assessment. Everything else is deterministic. This is not a limitation — it's what makes the system auditable, debuggable, and safe to put in production.

---

### Slide 5.3 — The 6-Stage Pipeline

```
POST /api/orchestrate
        |
        v
initialize-orchestration-context
  (set ~30 variables, dedupe check)
        |
        v
   [ duplicate? ] --YES--> decision=CLARIFY, skip all stages
        |
        NO
        |
        v
  validate-identity          <-- business-validation.xml
        |
        v
  enrich-customer-profile    <-- business-validation.xml
        |
        v
  resolve-intent-and-order   <-- business-resolution.xml
        |
        v
     assess-risk              <-- business-risk.xml
        |
        v
   enforce-policy             <-- business-policy.xml
        |
        v
  execute-mutation            <-- business-mutation.xml
        |
        v
  Build Final Response Envelope
  (orchestration-flow.xml)
```

Each stage is a named `<sub-flow>`. The main flow in `orchestration-flow.xml` calls
`initialize-orchestration-context` then `process-orchestration-request`. `process-orchestration-request`
(in `orchestration-context.xml`) handles the duplicate-or-normal branch, then calls all six stages in
sequence.

---

### Slide 5.4 — Context Initialization and Deduplication

`initialize-orchestration-context` sets every variable to a safe default before any stage runs.
Key variables and their defaults:

| Variable | Default | Purpose |
|---|---|---|
| `decision` | `ESCALATE` | Safe-fail default |
| `shouldIssueCredit` | `false` | Side-effect gate |
| `allowMutation` | `false` | Mutation gate |
| `identityMissing` | `false` | Identity flag |
| `riskLevel` | `UNKNOWN` | AI output |
| `riskScore` | `-1` | AI output |
| `stageDataCloud` | `NOT_RUN` | Observability |
| `stageGateway` | `NOT_RUN` | Observability |
| `stageServiceCloud` | `NOT_RUN` | Observability |

**Deduplication:**

```xml
<set-variable variableName="dedupeKey"
              value='#["request::" ++ ((vars.requestId default correlationId) as String)]' />
<os:contains key="#[vars.dedupeKey]"
             objectStore="requestDedupeObjectStore"
             target="isDuplicateRequest" />
```

Object store: `requestDedupeObjectStore` — persistent, max 20 000 entries, TTL 30 minutes.

If `isDuplicateRequest` is true, `process-orchestration-request` short-circuits:
- `decision` = `CLARIFY`
- All stage statuses = `SKIPPED`
- Response: "This request was already received. Please wait for the previous outcome."
- No Bedrock call is made. No Salesforce query. No credit.

---

### Slide 5.5 — Stage 1: validate-identity

File: `business-validation.xml`, sub-flow `validate-identity`

**Rule:** If `userId` is blank or literally `"unknown"`, the orchestrator cannot trust who is making
the request. It must not issue a credit on behalf of an anonymous caller.

```
x-user-id header (from slack-agent-router OBO flow, covered in Module 3)
    |
    v
isBlank(userId) OR userId == "unknown"?
    YES --> identityMissing=true
            decision=CLARIFY
            shouldIssueCredit=false
            validationCode=400
            failureClassification=POLICY_REJECTED
            agentResponse="Missing trusted identity..."
            (return — no further stages run usefully)
```

Telemetry log line emitted at WARN:
```
telemetry stage=VALIDATION_FAIL ... reason=missing-trusted-identity
```

**Design principle:** The Bedrock call is downstream of this check. A missing identity exits early
and saves an AI inference cost. This is OBO-awareness at the process layer — the identity set by
slack-agent-router's OBO token exchange is enforced here, not assumed.

---

### Slide 5.6 — Stage 2: enrich-customer-profile

File: `business-validation.xml`, sub-flow `enrich-customer-profile`

**Purpose:** Fetch the customer's `customerTier` and `churnRisk` from Data Cloud so the Bedrock
prompt contains real customer context, not generic text.

```
profileCacheKey = "profile::" + userId

profileCacheObjectStore.contains(profileCacheKey)?
    HIT  --> load from cache, stageDataCloud=CACHE_HIT
    MISS --> HTTP GET data-cloud-sapi /api/profile/{userId}
                 headers: x-user-id, x-flow-id, x-request-id, x-session-id
             --> store in profileCacheObjectStore
             --> stageDataCloud=OK

    FAIL (on-error-continue) -->
             customerProfile = {customerName:"Guest", customerTier:"Standard", churnRisk:"UNKNOWN"}
             stageDataCloud=FAIL
```

Object store: `profileCacheObjectStore` — persistent, max 5 000 entries, TTL 5 minutes.

**Cache invalidation:** After a successful Service Cloud credit mutation in `execute-mutation`,
the profile entry is explicitly removed:
```xml
<os:remove key="#[vars.profileCacheKey]" objectStore="profileCacheObjectStore" />
```
This ensures the next request fetches fresh loyalty data reflecting the issued credit.

**Into the Bedrock prompt (Stage 3):**
```
customerTier=Gold, churnRisk=HIGH
```
These fields are injected into the `inputText` string sent to the AI Gateway in `assess-risk`.

---

### Slide 5.7 — Stage 3: resolve-intent-and-order

File: `business-resolution.xml`, sub-flow `resolve-intent-and-order`

Two problems to solve: what the user wants (intent), and which order they mean (order number).

**Structured extraction takes priority:**

`slack-agent-router` (Module 3) already ran AI extraction and put the result in `payload.structured`.
The orchestrator reads it first:

```
vars.structuredOrderNumber = payload.structured.orderNumber   (if present)
vars.structuredReason      = payload.structured.reason        (if present)
```

**Regex fallback if structured is absent:**

```
inputText scan /\b(ORD-[A-Za-z0-9-]+|\d{3}-\d{3}|\d{3}-\d{2,4}-\d|\d{5,})\b/
```

Results are uppercased and deduplicated. If exactly 1 candidate: `orderNumber` = that value,
`hasValidOrderId` = true. If 0 or >1 candidates: `orderIdAmbiguous` = true (triggers CLARIFY later).

**Intent inference (priority order):**
1. `payload.structured.intent` == `REFUND_REQUEST` or `ORDER_INQUIRY` (exact match, uppercased)
2. `payload.intent` (same check)
3. `contains(lower(inputText), "refund")` → `REFUND_REQUEST`
4. `contains(lower(inputText), "order")` → `ORDER_INQUIRY`
5. Default: `UNKNOWN`

**SOQL injection guard:**

Before hitting Salesforce, the order number is sanitized:
```
dw::sanitize::sanitizeOrderNumberForSoqlLike(vars.normalizedOrderNumber)
```
`sanitize.dwl` strips everything except `[A-Za-z0-9 -]`, then uppercases and trims.

**Refund amount from Salesforce (sub-flow `resolve-refund-amount-from-salesforce`):**

```
salesforce:query
  SELECT Amount, Name FROM Opportunity
  WHERE Name LIKE '%{sanitizedOrderSearchTerm}%'
  ORDER BY LastModifiedDate DESC LIMIT 1

Found?  YES --> refundAmount = payload[0].Amount
                refundAmountSource = "salesforce_query"
                refundProduct = payload[0].Name
        NO  --> decision=CLARIFY, failureClassification=POLICY_REJECTED
 Error?      --> decision=CLARIFY, failureClassification=SALESFORCE_UNAVAILABLE
```

The amount is real data from the Salesforce Opportunity record — not a hardcoded value. If the lookup
fails for any reason, the orchestrator returns CLARIFY and does not proceed to mutation.

---

### Slide 5.8 — Stage 4: assess-risk (Circuit Breaker + 3-Level Fallback)

File: `business-risk.xml`, sub-flow `assess-risk`

This stage calls Amazon Bedrock through the AI Gateway configured in Module 4. It applies a
software circuit breaker to protect downstream availability.

```
circuitKey = "ai-gateway"
circuit-breaker-before-call
    |
    v
circuitOpen?
    YES --> invoke-bedrock-direct-runtime
            bedrockDirectResult.success?
                YES --> use direct Bedrock result
                NO  --> invoke-mimic-risk-fallback
    NO  -->
identityMissing?
    YES --> stageGateway=SKIPPED
    NO  -->
        Build Bedrock Proxy Request payload:
          inputText: "Refund request order {orderNumber} reason {reason}.
                      customerTier={tier}, churnRisk={risk}"
          systemPrompt: "Return ONLY strict JSON: decision, riskLevel, riskScore, response"
          sessionId: vars.sessionId
          enableTrace: true

        until-successful maxRetries=3 millisBetweenRetries=2000
            HTTP POST aiGatewayRequestConfig
            (path: ai-gateway.openaiPath or ai-gateway.anthropicPath based on ai-gateway.apiStyle)
            on HTTP:BAD_REQUEST/UNAUTHORIZED/FORBIDDEN --> mark non-retryable, stop

        handle-gateway-response-or-fallback

    on-error-continue (ANY):
        circuit-breaker-on-failure
        invoke-bedrock-direct-runtime
            success? --> use direct result
            fail    --> invoke-mimic-risk-fallback
```

**The 3-level fallback:**

```
Level 1: AI Gateway (aiGatewayRequestConfig, HTTPS, retry x3)
    |
    FAIL
    |
Level 2: BedrockDirectInvoker (Java SDK, invoke-bedrock-direct-runtime)
    |
    FAIL
    |
Level 3: invoke-mimic-risk-fallback (deterministic rules, no network call)
```

The circuit breaker is backed by `circuitBreakerObjectStore` — the same pattern covered in Module 3
for slack-agent-router, applied here to the AI Gateway endpoint. Three consecutive failures open the
circuit. Cooldown window: 60 000 ms. After cooldown, state transitions to HALF_OPEN and the next
request probes liveness.

---

### Slide 5.9 — Circuit Breaker State Machine

File: `circuit-breaker.xml`

```
States: CLOSED --> OPEN --> HALF_OPEN --> CLOSED
                                 |
                          (probe fails) --> OPEN

CLOSED:  failureCount < threshold (3). All calls go through.
OPEN:    failureCount >= 3, within cooldown window.
         Calls fail fast. Retry-After computed and logged.
HALF_OPEN: cooldown expired. One probe attempt allowed.
           Success --> CLOSED (failureCount reset to 0)
           Failure --> OPEN (openedAt refreshed)
```

Sub-flows:
- `circuit-breaker-before-call`: reads state from `circuitBreakerObjectStore`, sets `vars.circuitOpen`
- `circuit-breaker-on-failure`: increments failureCount, opens if >= threshold
- `circuit-breaker-on-success`: resets state to CLOSED

**Variables initialized in `initialize-orchestration-context`:**
```
circuitFailureThreshold = 3
circuitCooldownMs = 60000
circuitKey = null  (set to "ai-gateway" at the start of assess-risk)
circuitOpen = false
circuitRetryAfter = null
```

---

### Slide 5.10 — BedrockDirectInvoker: Level 2 Fallback

File: `src/main/java/com/feroz/orchestrator/BedrockDirectInvoker.java`

Called from DataWeave via the `java!` module:

```
java!com::feroz::orchestrator::BedrockDirectInvoker::invoke(
    region, accessKeyId, secretAccessKey,
    agentId, agentAliasId,
    sessionId, inputText
)
```

The method signature:
```java
public static Map<String, Object> invoke(
    String region, String accessKeyId, String secretAccessKey,
    String agentId, String agentAliasId,
    String sessionId, String inputText)
```

Returns a `Map<String, Object>` with keys: `success`, `decision`, `response`, `riskLevel`, `riskScore`.

Internally:
- Builds a `BedrockAgentRuntimeAsyncClient` with `StaticCredentialsProvider`
- Calls `invokeAgent` via the streaming API with `enableTrace=true`
- Waits up to 75 seconds on a `CountDownLatch`
- Retries once on failure (250 ms delay)
- Extracts `decision` via regex: `"decision"\s*:\s*"(APPROVE|DENY|ESCALATE|CLARIFY)"`
- Falls back to heuristic keyword matching on the raw text if JSON keys absent
- Handles `ReturnControlPayload` (agent awaiting tool execution) → returns CLARIFY

The `agentId` and `agentAliasId` are injected from environment variables `BEDROCK_AGENT_ID` and
`BEDROCK_AGENT_ALIAS_ID` (Module 4 setup). If either is blank the method returns
`{success: false, error: "Missing Bedrock agentId/agentAliasId"}` without making a network call.

---

### Slide 5.11 — Level 3 Fallback: invoke-mimic-risk-fallback

When both AI Gateway and BedrockDirectInvoker are unavailable, the orchestrator does not fail the
Slack user with an error. It falls back to deterministic local rules:

```
normalizedOrderNumber starts with "999"?
    YES --> riskLevel=CRITICAL, riskScore=95, decision=ESCALATE
    NO  --> riskLevel=SAFE,    riskScore=14

intent == REFUND_REQUEST and riskLevel != CRITICAL?
    YES --> bedrockDecisionCandidate=APPROVE
    NO  (CRITICAL) --> bedrockDecisionCandidate=ESCALATE
    NO  (not REFUND) --> bedrockDecisionCandidate=CLARIFY

decisionSource = "mimic"
failureClassification = "BEDROCK_UNAVAILABLE"
```

The `agentResponse` is a canned human-readable string appropriate to each branch.

**Why this matters:** The system degrades gracefully. A Slack user still gets a response.
The `usedFallback` and `decisionSource` fields in the metadata tell the caller (and operators)
that AI was not involved in this decision.

---

### Slide 5.12 — Stage 5: enforce-policy

File: `business-policy.xml`, sub-flow `enforce-policy`

Policy enforcement happens after the AI has run (or fallen back). It normalizes the decision and
applies four gates.

**Decision normalization:**

```
bedrockDecisionCandidate present?
    YES --> decision = upper(bedrockDecisionCandidate)
    NO  --> deterministic rules:
            startsWith(normalizedOrderNumber, "999") --> ESCALATE
            identityMissing                          --> CLARIFY
            intent != REFUND_REQUEST                 --> CLARIFY
            orderIdAmbiguous                         --> CLARIFY
            not hasValidOrderId                      --> CLARIFY
            (all other cases)                        --> CLARIFY
```

**The allowMutation gate — all four conditions must be true:**

```
decision == "APPROVE"
AND shouldIssueCredit == true
AND identityMissing == false
AND mutationPayloadComplete == true
                                    --> allowMutation = true
```

`mutationPayloadComplete` is true only when `normalizedOrderNumber` is not blank and not "UNKNOWN".

**Guard:** If decision is APPROVE and shouldIssueCredit is true but `mutationPayloadComplete` is
false, the guard fires: `shouldIssueCredit` is reset to false, `allowMutation` stays false, and
the user gets "Missing required mutation fields (orderNumber)."

**DataWeave library functions (policy-rules.dwl):**

```
fun computePolicyRuleMatched(decision, intent, orderIdAmbiguous,
                              hasValidOrderId, hasReason, hasCustomerId): Boolean

fun computeAllowMutation(decision, shouldIssueCredit,
                          identityMissing, mutationPayloadComplete): Boolean
```

These are the canonical definitions. `enforce-policy` implements equivalent inline DataWeave that
references the same logic.

---

### Slide 5.13 — Stage 6: execute-mutation

File: `business-mutation.xml`, sub-flow `execute-mutation`

Only runs if `allowMutation == true` and `agentError == false`.

```
allowMutation AND NOT agentError?
    YES -->
        Build MCP Request:
          customerId, orderNumber, reason, amount (from Salesforce query),
          fraudScore (riskScore), orchestratorContext, flowId, requestId,
          sessionId, product, amountSource

        HTTP POST serviceCloudMcpRequestConfig /mcp/tool/issue_credit
          headers: x-user-id, x-flow-id, x-request-id, x-session-id

        creditResult.status == "SUCCESS" AND caseId not blank?
            YES --> stageServiceCloud=OK
                    Invalidate profileCacheObjectStore for this userId
                    agentResponse appended with "\n\nCase Reference: {caseId}"
            NO  --> shouldIssueCredit=false, failureClassification=SERVICE_CLOUD_REJECTED

        on-error-continue (ANY):
            stageServiceCloud=FAIL
            decision=CLARIFY, shouldIssueCredit=false, allowMutation=false
            failureClassification=SERVICE_CLOUD_UNAVAILABLE
            Persist to DLQ (workflowDlqObjectStore)
            Increment dlqMetricsObjectStore counter

    NO  --> stageServiceCloud=SKIPPED
```

---

### Slide 5.14 — Dead Letter Queue

File: `business-mutation.xml` (error handler inside `execute-mutation`)

When the Service Cloud MCP call fails:

```xml
<os:store key='#["dlq::" ++ (vars.requestId default correlationId)]'
          objectStore="workflowDlqObjectStore">
  <os:value>
    {
      timestamp, flowId, requestId, sessionId, userId,
      orderNumber, stageServiceCloud,
      compensationNeeded: true,
      errorType, errorMessage, payload
    }
  </os:value>
</os:store>
```

Object store: `workflowDlqObjectStore` — persistent, max 5 000 entries, TTL 7 days.

`compensationNeeded: true` is the flag operators look for in a manual replay script.

**DLQ monitor** (`ai-orchestrator-papi.xml`, `dlq-monitor-flow`): a scheduler runs every 5 minutes,
reads `dlq.failure.count` from `dlqMetricsObjectStore`, logs an ERROR-level alert if count > 0,
then resets the counter to 0.

---

### Slide 5.15 — Structured Observability

Every significant moment in the pipeline emits a log line in a consistent key=value format:

```
telemetry stage=X flowId=Y requestId=Z sessionId=W userId=U
          orderNumber=V decision=D caseId=C
          [stage-specific fields]
```

Stage values observed across the pipeline:
```
START               VALIDATION_FAIL         DATA_CLOUD_OK
DATA_CLOUD_FALLBACK SCANNER_REMOVED         BEDROCK_GATEWAY_RETRY
BEDROCK_GATEWAY_OK  BEDROCK_GATEWAY_FAIL    BEDROCK_DIRECT_RUNTIME
MIMIC_RISK_FALLBACK DECISION_MODEL          SERVICE_CLOUD_OK
SERVICE_CLOUD_REJECTED SERVICE_CLOUD_FAIL   MUTATION_BLOCKED
DUPLICATE_REQUEST   CIRCUIT_OPEN            AMOUNT_LOOKUP_FALLBACK
FINAL               DLQ_ALERT
```

The `stageStatus` map is also returned in the HTTP response metadata:

```json
"stageStatus": {
  "dataCloud": "OK",
  "scanner": "REMOVED",
  "gateway": "OK",
  "serviceCloud": "OK"
}
```

This lets `slack-agent-router` (and instructors) see exactly what ran, what was skipped, and what
degraded — without parsing logs.

---

### Slide 5.16 — DataWeave Library Files

Three DWL files in `src/main/resources/dw/`:

**policy-rules.dwl** — canonical gate logic
```
fun computePolicyRuleMatched(decision, intent, orderIdAmbiguous,
                              hasValidOrderId, hasReason, hasCustomerId): Boolean
fun computeAllowMutation(decision, shouldIssueCredit,
                          identityMissing, mutationPayloadComplete): Boolean
```

**risk-assessment.dwl** — AI response normalization
```
fun normalizeDecisionCandidate(payload): Null | String
    -- accepts: APPROVE | DENY | CLARIFY | ESCALATE  (else null)
fun normalizeRiskLevel(payload): String
    -- accepts: SAFE | LOW | CRITICAL | UNKNOWN       (else "UNKNOWN")
fun normalizeRiskScore(payload): Number
    -- numeric or numeric-string; -1 if unparseable
```

**response-envelope.dwl** — canonical response builder
```
fun buildFinalResponseEnvelope(vars): Object
    -- returns {response, metadata{...gates{...}, stageStatus{...}}}
```

**sanitize.dwl** — SOQL injection prevention
```
fun sanitizeOrderNumberForSoqlLike(value): String
    -- strips everything except [A-Za-z0-9 -], uppercases, trims
```

These functions are the testable unit of the orchestrator's logic. They can be tested with MUnit
DataWeave module without spinning up any HTTP connections.

---

### Slide 5.17 — Global Config: Object Stores

File: `global-config.xml`

Five Object Stores declared:

| Name | Persistent | Max Entries | TTL |
|---|---|---|---|
| `requestDedupeObjectStore` | true | 20 000 | 30 min |
| `profileCacheObjectStore` | true | 5 000 | 5 min |
| `circuitBreakerObjectStore` | true | 500 | (none) |
| `workflowDlqObjectStore` | true | 5 000 | 7 days |
| `dlqMetricsObjectStore` | true | 100 | 30 days |

All are persistent. In CloudHub 2.0 this means state survives a replica restart.

---

### Slide 5.18 — Global Config: HTTP Request Configs

```
dataCloudRequestConfig      HTTPS  ${data-cloud.host}:443
                            basePath=/api, pool x10, idle 30s, reconnect x3 @2s

serviceCloudMcpRequestConfig HTTPS ${service-cloud-mcp.host}:443
                             basePath=/mcp, pool x10, idle 30s, reconnect x3 @2s

aiGatewayRequestConfig      HTTPS  ${ai-gateway.host}:443
                             default headers: client_id, client_secret
                             pool x10, idle 30s, reconnect x3 @2s

bedrockProxyRequestConfig   HTTPS  ${bedrock-proxy.host}:443

salesforceConfig            basic-connection
                             username/password/token/url from ${sfdc.*}
```

TLS: `sharedTlsContext` uses `${tls.keystore.path}` (JKS, alias `localhost`).
HTTP listener: port 8081 (plain). HTTPS listener: port `${https.listener.port}` (default 8082).

---

### Slide 5.19 — RAML Contract: ai-orchestrator-papi.raml

```yaml
#%RAML 1.0
title: ai-orchestrator-papi
version: v1
baseUri: /apikit
mediaType: application/json

types:
  OrchestrateRequest:
    type: object
    properties:
      inputText?: string
      userId?: string
      sessionId?: string
      requestId?: string
      flowId?: string
      customerId?: string
      structured?:
        type: object
        properties:
          orderNumber?: string
          reason?: string
          amount?: number

  OrchestrateResponse:
    type: object
    properties:
      response: string
      metadata:
        type: object
        additionalProperties: true

/orchestrate:
  post:
    description: Orchestrate refund risk assessment and optional mutation flow.
    body:
      application/json:
        type: OrchestrateRequest
    responses:
      200: OrchestrateResponse
      400: object
      500: object
```

The `structured` block is the pre-extracted output from Module 3's AI extraction step in
`slack-agent-router`. When present, `orderNumber` and `reason` skip the regex fallback path.

---

### Slide 5.20 — Config YAML Structure

**shared-config.yaml** — defaults for local dev (all hosts = `localhost`)

**dev-config.yaml** — overrides with real CloudHub 2.0 hosts:
```yaml
data-cloud:
  host: "data-cloud-sapi-835dgu.wdob74.usa-e2.cloudhub.io"
service-cloud-mcp:
  host: "service-cloud-mcp-835dgu.wdob74.usa-e2.cloudhub.io"
ai-gateway:
  host: "agenticenterprisetraining-small-835dgu.wdob74.usa-e2.cloudhub.io"
  apiStyle: "openai"
  openaiPath: "/llmproxy2/chat/completions"
```

**config.yaml** — secure property references only (no plaintext secrets):
```yaml
sfdc:
  password: "${secure::sfdc.password}"
  token: "${secure::sfdc.token}"
ai-gateway:
  clientSecret: "${secure::ai-gateway.clientSecret}"
```

**global-config.xml** loads both:
```xml
<configuration-properties file="shared-config.yaml" />
<configuration-properties file="${env}-config.yaml" />
```

`env` is set to `dev`, `test`, or `prod` via a Maven property or CloudHub 2.0 app property.

---

### Slide 5.21 — The Final Response Envelope

Built in `orchestration-flow.xml`:

```json
{
  "response": "Your refund for order ORD-1001 has been approved.\n\nCase Reference: CS-00001234",
  "metadata": {
    "decision": "APPROVE",
    "shouldIssueCredit": true,
    "riskLevel": "SAFE",
    "riskScore": 14,
    "intent": "REFUND_REQUEST",
    "orderNumber": "ORD-1001",
    "orderIdAmbiguous": false,
    "hasValidOrderId": true,
    "flowId": "...",
    "requestId": "...",
    "caseId": "CS-00001234",
    "sessionId": "...",
    "usedFallback": false,
    "agentError": false,
    "decisionSource": "bedrock",
    "failureClassification": null,
    "refundAmount": 249.99,
    "refundAmountSource": "salesforce_query",
    "gates": {
      "allowMutation": true,
      "hasValidOrder": true,
      "hasReason": true,
      "hasCustomerId": true,
      "policyRuleMatched": true
    },
    "stageStatus": {
      "dataCloud": "OK",
      "scanner": "REMOVED",
      "gateway": "OK",
      "serviceCloud": "OK"
    }
  }
}
```

`slack-agent-router` reads `response` to compose the Slack message and reads `metadata.caseId` to
confirm the mutation succeeded.

---

### Slide 5.22 — VIDEO PLACEHOLDER: Live Pipeline Trace

```
[VIDEO — approximately 8 minutes]

Instructor demonstrates:
1. curl POST /api/orchestrate with valid userId, inputText, structured.orderNumber
2. Tail the app logs: show telemetry stage=START through stage=FINAL
3. Identify each of the 6 stage log lines
4. Show metadata.stageStatus in the response
5. Repeat with userId="unknown" — show VALIDATION_FAIL short-circuit
6. Repeat with duplicate requestId — show DUPLICATE_REQUEST path
7. Show the profileCacheObjectStore hit on the second request for the same userId
```

---

### Slide 5.23 — VIDEO PLACEHOLDER: Circuit Breaker Demo

```
[VIDEO — approximately 5 minutes]

Instructor demonstrates:
1. Point ai-gateway.host at an invalid hostname in dev-config.yaml
2. Send 3 requests — watch circuit open on the third (BEDROCK_GATEWAY_FAIL x3)
3. Show stageGateway=DEGRADED and decisionSource=bedrock (direct fallback succeeded)
4. Send a 4th request within cooldown — show CIRCUIT_OPEN log, retryAfter in log
5. Wait for cooldown, send 5th request — show HALF_OPEN transition, then CLOSED on success
```

---

### Slide 5.24 — VIDEO PLACEHOLDER: DLQ Demo

```
[VIDEO — approximately 4 minutes]

Instructor demonstrates:
1. Point service-cloud-mcp.host at an invalid hostname
2. Send a valid APPROVE-path request
3. Show stageServiceCloud=FAIL in the response
4. Show the DLQ entry written to workflowDlqObjectStore
5. Show dlq-monitor-flow firing in logs (stage=DLQ_ALERT)
6. Discuss compensationNeeded:true and what a replay script would do
```

---

### Slide 5.25 — Module 5 Summary

**What you built:**

- `orchestration-flow.xml` — HTTP listener + final response envelope
- `orchestration-context.xml` — context init + deduplication + pipeline dispatcher
- `business-validation.xml` — validate-identity + enrich-customer-profile
- `business-resolution.xml` — resolve-intent-and-order (structured extraction, regex fallback, SOQL)
- `business-resolution-refund.xml` — Salesforce amount lookup
- `business-risk.xml` — assess-risk with circuit breaker + 3-level Bedrock fallback
- `business-risk-gateway-handler.xml` — AI Gateway response normalization
- `circuit-breaker.xml` — CLOSED/OPEN/HALF_OPEN state machine + BedrockDirectInvoker wrapper
- `business-policy.xml` — enforce-policy with 4-gate allowMutation
- `business-mutation.xml` — execute-mutation + DLQ
- `global-config.xml` — all configs + 5 Object Stores
- `ai-orchestrator-papi.xml` — APIkit, MCP tool endpoint, health endpoints, DLQ monitor
- `dw/policy-rules.dwl`, `risk-assessment.dwl`, `response-envelope.dwl`, `sanitize.dwl`
- `src/main/java/com/feroz/orchestrator/BedrockDirectInvoker.java`
- `shared-config.yaml`, `dev-config.yaml`, `config.yaml`
- `src/main/resources/api/ai-orchestrator-papi.raml`

**Module 6 preview:** `service-cloud-mcp` — the MCP server that receives the credit mutation
request and writes a case to Service Cloud. You will see `POST /tool/issue_credit` from the
perspective of the server that handles it.
