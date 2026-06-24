### Slide 6.1 — Module 6: System APIs — Data Cloud and Service Cloud

**What this module covers**

- `data-cloud-sapi`: reads unified customer profile from Salesforce Data Cloud, returns grounding context to ai-orchestrator
- `service-cloud-mcp`: executes refund actions in Salesforce Service Cloud, exposes a tool contract any orchestrator can call

Both apps sit at the System layer of the API-led connectivity model. They do not decide anything. They execute against specific systems of record and report exactly what happened.

```
Slack
  |
slack-agent-router  (port 8081)
  |
ai-orchestrator     (port 8082)
  |         |
  |         +---> data-cloud-sapi  (port 8083)  <-- this module
  |
  +-----------> service-cloud-mcp  (port 8084)  <-- this module
```

---

### Slide 6.2 — The System API Contract

A System API has three rules:

1. **It executes, it never decides.** Deciding belongs to the Process layer.
2. **200 for every business outcome.** Use response fields to communicate what happened.
3. **5xx only for technical failures.** Infrastructure down, credentials invalid, Salesforce unreachable.

These rules matter because the orchestrator reads the response body to route next steps. If a business rejection returns 4xx, the MuleSoft error handler catches it and the response body is lost.

```
                  Orchestrator reads this field
                            |
POST /mcp/tool/issue_credit |
<--- HTTP 200 ------------- |
     {                      |
       "status": "REJECTED",
       "agentStatus": "REJECTED_RISK",
       "decisionHint": "REJECT_AND_ESCALATE_FRAUD_REVIEW",
       "retryable": false
     }
```

The orchestrator does not need to know that Salesforce exists. It reads `decisionHint` and decides what to tell the user.

---

### Slide 6.2b — MCP Bridge: REST APIs as MCP Servers Without Code

> [VIDEO REFERENCE: ~4:20 in "What's New with Agent Fabric" https://www.youtube.com/watch?v=jWwgboa_z8Y]

In this course we build service-cloud-mcp by hand — writing the MCP endpoint in Mule XML. Agent Fabric now offers **MCP Bridge** to create an MCP server from existing REST APIs without writing any code.

**The wizard flow:**

```
1. Select APIs & Operations   ← pick from Exchange-registered APIs (e.g. Incident Management API, Email API)
2. Select Instances           ← choose deployment (Production v3.8.0, Staging v2.3.0, etc.)
3. Review Tools               ← auto-generated tool schema from the API spec
4. Select Gateway             ← which Omni Gateway instance to deploy on
5. Configure Security         ← attach governance policies from the library
```

**Result**: A running MCP server endpoint — **"deploy an escalation MCP server without modifying any code."**

**Relevance to our stack:**

| Approach | When to use |
|----------|-------------|
| MCP Bridge (wizard) | Existing REST API in Exchange with a good spec; no custom logic needed |
| Hand-built MCP in Mule (our approach) | Need custom logic — idempotency checks, risk gate, Salesforce connector OAuth CC, business-rule enforcement before execution |

> service-cloud-mcp uses the hand-built approach because it needs to: verify the fraud score gate, look up the Contact ID, create the Case, and update the Opportunity — all in a single tool call with proper error handling. MCP Bridge can't express that logic.

---

### Slide 6.3 — data-cloud-sapi: Purpose and Position

`data-cloud-sapi` answers one question: *Who is this Slack user, and what does Data Cloud know about them?*

The response directly enriches the Amazon Bedrock prompt in `ai-orchestrator`. That is called **grounding** — giving the model factual context before it reasons.

```
ai-orchestrator
  |
  |  GET /api/profile/{slackId}
  |  x-user-id: U0AA9JSR2AD
  |
  v
data-cloud-sapi
  |
  |  1. Resolve slackId -> email
  |     (static map, then Slack users.info API as fallback)
  |
  |  2. Query Data Cloud: email -> ssot__PartyId__c
  |     (ssot__ContactPointEmail__dlm)
  |
  |  3. Query Data Cloud: partyId -> LoyaltyTier__c, ChurnRisk__c
  |     (ssot__Individual__dlm)
  |
  |  4. Build grounding response
  |
  v
  {
    "groundingVersion": "1.0",
    "customerTier": "Platinum",
    "churnRisk": "Low",
    "identityConfidence": "HIGH",
    "recommendedAction": "CONTINUE",
    "knownUnknowns": []
  }
```

---

### Slide 6.4 — data-cloud-sapi: Connector and Authentication

The Salesforce Data Cloud connector (`mule4-sdc-connector`) uses OAuth 2.0 Client Credentials. There is no user session. The Mule application itself authenticates as a connected app.

```xml
<sdc:sdc-config name="salesforceDataCloudConfig">
    <sdc:oauth-client-credentials-connection
        consumerKey="${secure::sfdc.clientId}"
        consumerSecret="${secure::sfdc.clientSecret}"
        tokenEndpoint="${secure::sfdc.tokenEndpoint}">
        <reconnection>
            <reconnect count="3" frequency="2000" />
        </reconnection>
    </sdc:oauth-client-credentials-connection>
</sdc:sdc-config>
```

Key points:
- `consumerKey` / `consumerSecret` — not `clientId` / `clientSecret`. The SDC connector uses OAuth terminology from the Salesforce connected app model.
- `${secure::...}` — the secure properties prefix. These values are encrypted at rest in `secure-properties.yaml` and decrypted at runtime using the key passed as a system property.
- The `reconnect` block retries 3 times with 2-second gaps before failing. Without it, a transient token expiry causes an immediate 503.

---

### Slide 6.5 — data-cloud-sapi: Secure Properties and TLS

**Secure properties** protect credentials in source control. The encrypted values live in `secure-properties.yaml`. The decryption key is passed at runtime — never committed.

```xml
<secure-properties:config name="securePropertiesConfig"
    file="secure-properties.yaml"
    key="#[p('secure.key') default 'local-dev-secure-key']" />
```

**TLS** is configured for two directions:

```xml
<!-- Inbound: key-store for the app's own certificate -->
<tls:context name="listenerTlsContext">
    <tls:key-store type="${tls.keystore.type}"
                   path="${tls.keystore.path}"
                   alias="${tls.keystore.alias}"
                   password="${secure::tls.keystorePassword}"
                   keyPassword="${secure::tls.keyPassword}" />
</tls:context>

<!-- Outbound: trust-store for validating upstream certs -->
<tls:context name="requesterTlsContext" enabledProtocols="TLSv1.2,TLSv1.3">
    <tls:trust-store insecure="false" />
</tls:context>
```

**CloudHub consideration:** The HTTP listener uses plain HTTP on `${http.port}`. CloudHub 2.0 terminates TLS at the ingress proxy. The app never sees a raw TLS handshake in production. The `listenerTlsContext` is defined for local development only.

```xml
<http:listener-config name="httpListenerConfig">
    <http:listener-connection host="0.0.0.0" port="${http.port}" />
</http:listener-config>
```

---

### Slide 6.6 — data-cloud-sapi: Object Store Caching

Data Cloud queries are not free. A profile lookup involves two SOQL-equivalent queries. Caching avoids hammering Data Cloud on every message in a conversation thread.

```xml
<ee:object-store-caching-strategy name="profileLookupCachingStrategy"
    keyGenerationExpression="#[vars.profileLookupCacheKey]">
    <os:private-object-store alias="profileLookupCacheStore"
        persistent="true"
        maxEntries="10000"
        entryTtl="5"
        entryTtlUnit="MINUTES"
        expirationInterval="1"
        expirationIntervalUnit="MINUTES" />
</ee:object-store-caching-strategy>
```

How it is used in the flow:

```
1. Set vars.profileLookupCacheKey = "profileLookup::" ++ safeTargetEmail
2. Wrap the two sdc:query calls inside <ee:cache cachingStrategy-ref="...">
3. On cache hit:  skip both queries, return cached result
4. On cache miss: execute queries, store result, set TTL=5min
```

The 5-minute TTL balances freshness against cost. If a customer's tier changes, the old profile is served for at most 5 minutes. For a live refund conversation that is acceptable.

`persistent="true"` means the store survives a worker restart on CloudHub. This matters for rolling deployments.

---

### Slide 6.7 — data-cloud-sapi: Data Cloud Query Pattern

Data Cloud uses a SQL-like query language over Data Lake Objects (DLOs). The connector sends a JSON body with a `sql` key.

**Step 1 — Resolve slackId to partyId:**

```sql
SELECT ssot__PartyId__c
FROM ssot__ContactPointEmail__dlm
WHERE ssot__EmailAddress__c = '<email>'
```

`ssot__ContactPointEmail__dlm` is the standard Data Cloud object that links email addresses to party identifiers.

**Step 2 — Fetch individual profile:**

```sql
SELECT ssot__Id__c, ssot__FirstName__c, ssot__LastName__c,
       LoyaltyTier__c, ChurnRisk__c
FROM ssot__Individual__dlm
WHERE ssot__Id__c = '<partyId>'
```

`ssot__Individual__dlm` is the unified individual profile object. `LoyaltyTier__c` and `ChurnRisk__c` are custom fields populated by Data Cloud's unification and segmentation jobs.

**SQL injection prevention:**

```dataweave
import sanitizeSqlLiteral from dw::common::sanitize
var safeTargetEmail = sanitizeSqlLiteral(vars.targetEmail)
```

The DataWeave standard library's `sanitizeSqlLiteral` function escapes single quotes in user-controlled strings before they are concatenated into the query body.

---

### Slide 6.8 — data-cloud-sapi: Grounding Response

The `build-grounding-response-subflow` translates raw Data Cloud fields into a vocabulary the orchestrator understands.

```
Raw Data Cloud fields          Grounding response fields
--------------------------     ---------------------------
LoyaltyTier__c = "Platinum" -> customerTier = "Platinum"
ChurnRisk__c = "High"        -> churnRisk = "High"
resolutionSource = "MAP"     -> identityConfidence = "HIGH"
partyId = ""                 -> recommendedAction = "CLARIFY"
```

`identityConfidence` is derived from how the email was resolved:
- `MAP` (static map) + partyId found = `HIGH`
- `SLACK_API` + partyId found = `MEDIUM`
- partyId not found = `LOW`

`recommendedAction` drives the orchestrator's behaviour:
- `CLARIFY` — insufficient identity data, ask the user to confirm
- `ESCALATE` — high churn risk, route to a human agent
- `CONTINUE` — proceed with automated refund evaluation

`knownUnknowns` is an explicit list of gaps. If `return_window_not_computed_in_data_cloud_sapi` appears, the orchestrator knows not to hallucinate a return window calculation.

---

### Slide 6.9 — data-cloud-sapi: APIkit and Flow Structure

```
src/main/mule/
  global.xml          -- connector configs, caching, TLS, secure properties
  main.xml            -- get-unified-profile-flow (HTTP listener + orchestration)
  main-support.xml    -- resolve-customer-context-subflow
                      -- build-grounding-response-subflow
  api.xml             -- APIkit router, health check, readiness probe
  error.xml           -- global-default-error-handler
src/main/resources/
  api/data-cloud-sapi.raml
  config.yaml
  {env}-config.yaml
  secure-properties.yaml
```

The main flow in `main.xml` extracts OBO headers, calls the context sub-flow, then calls the grounding response sub-flow:

```
get-unified-profile-flow
  |-- extract OBO headers (x-user-id, x-flow-id, x-request-id, x-session-id)
  |-- set MDC tracing variables (tracing:set-logging-variable)
  |-- try: resolve-customer-context-subflow
  |     on-error-continue -> graceful fallback (empty profile, FALLBACK source)
  |-- build-grounding-response-subflow
  |-- logger: log recommendedAction
```

The `on-error-continue` on the context resolution means a Data Cloud outage returns a degraded-but-valid response rather than a 500. The orchestrator sees `identityConfidence: "LOW"` and `recommendedAction: "CLARIFY"` and handles it gracefully.

---

### Slide 6.10 — service-cloud-mcp: What MCP Means Here

MCP stands for Model Context Protocol. It defines a contract for tools that an AI model can call: a fixed endpoint, a defined input shape, a defined output shape.

`service-cloud-mcp` exposes one tool:

```
POST /mcp/tool/issue_credit
```

Any orchestrator that knows this contract can issue a refund. It does not need to know:
- That the backing system is Salesforce
- That a Case object is being created
- That the Opportunity object is being updated
- How OAuth authentication works with Service Cloud

The tool contract is the interface. Salesforce internals are the implementation.

```
ai-orchestrator                service-cloud-mcp
      |                              |
      | POST /mcp/tool/issue_credit  |
      | {customerId, orderNumber,    |
      |  amount, reason, fraudScore} |
      |----------------------------> |
      |                              | -- validate inputs
      |                              | -- risk gate
      |                              | -- idempotency check
      |                              | -- create Case
      |                              | -- update Opportunity
      |                              |
      | <--------------------------- |
      | {status, caseId,             |
      |  agentStatus, decisionHint}  |
```

---

### Slide 6.11 — service-cloud-mcp: Connector and Authentication

```xml
<salesforce:sfdc-config name="Salesforce_Config">
    <salesforce:oauth-client-credentials-connection>
        <salesforce:oauth-client-credentials
            clientId="${sfdc.clientId}"
            clientSecret="${sfdc.clientSecret}"
            tokenUrl="${sfdc.tokenEndpoint}" />
    </salesforce:oauth-client-credentials-connection>
</salesforce:sfdc-config>
```

This is the Salesforce connector (not SDC). The attribute names differ from SDC: `clientId` / `clientSecret` / `tokenUrl` instead of `consumerKey` / `consumerSecret` / `tokenEndpoint`.

Credentials are not wrapped in `${secure::...}` here — they are injected as plain CloudHub 2.0 deployment properties. Compare with `data-cloud-sapi` which uses the full secure properties module. Both approaches are valid; the difference reflects the app's deployment configuration.

---

### Slide 6.12 — service-cloud-mcp: The Five Execution Stages

```
POST /mcp/tool/issue_credit
         |
         v
[1] mcp-init-context
    Extract: customerId, orderNumber, amount, reason, fraudScore
    Extract OBO headers: x-request-id, x-flow-id, x-session-id, x-user-id
    Derive idempotencyKey = customerId|orderNumber|amount
    Set MDC tracing variables
         |
         v
[2] Input Validation
    Guard: customerId, orderNumber, amount all present?
    No  -> agentStatus=REJECTED_INPUT, failureClass=BUSINESS_VALIDATION
    Yes -> continue
         |
         v
[3] Risk Gate
    Guard: orderNumber starts with "999" AND fraudScore >= 70?
    Yes -> agentStatus=REJECTED_RISK, failureClass=BUSINESS_REJECTION
    No  -> continue
         |
         v
[4] Idempotency Check
    SOQL: SELECT Id FROM Case WHERE Subject = 'Return Request - Key <key>'
    Found -> caseId=<existing>, agentStatus=CASE_REUSED
    Not found -> continue to case creation
         |
         v
[5a] Opportunity Query
    SELECT Id FROM Opportunity WHERE StageName != 'Closed Won'
      AND StageName != 'Closed Lost' ORDER BY LastModifiedDate DESC LIMIT 1
    Found -> vars.opportunityId = Id
    Not found -> vars.opportunityId = "" (non-fatal)
         |
         v
[5b] Case Creation (if no existing case)
    until-successful maxRetries="2" millisBetweenRetries="1000"
      salesforce:create type="Case"
        Subject: "Return Request - Key <idempotencyKey>"
        Status: "New", Priority: "High", Origin: "Web"
    -> caseId = SaveResult.id, agentStatus=CASE_CREATED
         |
         v
[5c] Opportunity Update (if caseId and opportunityId both present)
    salesforce:update type="Opportunity"
      Refund_Order_Number__c, Refund_Reason__c,
      Refund_Case_Id__c, Refund_Agent_Status__c
    -> agentStatus=OPPORTUNITY_UPDATED
         |
         v
[6] mcp-format-response
    Build final JSON response
```

---

### Slide 6.13 — service-cloud-mcp: The 200-for-Business-Outcomes Rule

This is the most important design decision in `service-cloud-mcp`.

**Why not return 4xx for rejected inputs?**

When MuleSoft receives a non-2xx from a downstream call, its error handler activates and the response body from the downstream app is lost. The orchestrator cannot read `decisionHint` or `errorCode`. It only knows "something went wrong."

By returning HTTP 200 for all business outcomes, the full response body reaches the orchestrator intact.

```
Business outcome             HTTP status   agentStatus field
-----------------------------  ----------   ------------------
Missing required fields        200          REJECTED_INPUT
Fraud risk blocked             200          REJECTED_RISK
Duplicate request              200          CASE_REUSED
Case created successfully      200          CASE_CREATED
Case created, opp update fail  200          OPPORTUNITY_UPDATED
Salesforce down                500          FAILED
```

The orchestrator distinguishes success from rejection by reading `status` and `decisionHint`, not the HTTP status code.

---

### Slide 6.14 — service-cloud-mcp: Idempotency

If the Slack user submits the same refund request twice — or if the orchestrator retries after a network timeout — the system must not create two Cases for the same order.

The idempotency key is: `customerId|orderNumber|amount`

```xml
<salesforce:query config-ref="Salesforce_Config">
    <salesforce:salesforce-query>
        SELECT Id FROM Case
        WHERE Subject = 'Return Request - Key <idempotencyKey>'
        ORDER BY CreatedDate DESC LIMIT 1
    </salesforce:salesforce-query>
</salesforce:query>
```

If a case with that Subject already exists, the existing `caseId` is returned with `agentStatus=CASE_REUSED`. No second case is created. The orchestrator receives the same response as the first call.

This is idempotency at the System API layer. The orchestrator does not need to implement deduplication logic — it delegates that responsibility to the system that owns the data.

---

### Slide 6.15 — service-cloud-mcp: Case Creation with Retry

```xml
<until-successful maxRetries="2" millisBetweenRetries="1000">
    <salesforce:create type="Case" config-ref="Salesforce_Config">
        <salesforce:records>#[[{
            "Subject":   "Return Request - Key " ++ vars.idempotencyKey,
            "Description": vars.reason,
            "Origin":    "Web",
            "Status":    "New",
            "Priority":  "High"
        }]]</salesforce:records>
    </salesforce:create>
</until-successful>
```

`until-successful` retries the enclosed block on failure. Combined with idempotency, this is safe: if the first attempt partially succeeded (Salesforce created the case but the response was lost), the second attempt finds the existing case in the idempotency check and returns `CASE_REUSED` without creating a duplicate.

The Subject field carries the idempotency key. This doubles as a human-readable case title in the Service Cloud agent console.

---

### Slide 6.16 — service-cloud-mcp: Opportunity Linkage

When a case is created for an order, the associated Opportunity in Service Cloud is updated with four custom fields:

| Field | Value |
|---|---|
| `Refund_Order_Number__c` | The order number from the request |
| `Refund_Reason__c` | The reason text from the request |
| `Refund_Case_Id__c` | The ID of the newly created Case |
| `Refund_Agent_Status__c` | The final `agentStatus` value |

This creates a traceable link between the Opportunity, the Case, and the agent action. A human service agent opening the Opportunity record can see the full context of what the AI agent did.

Opportunity update failure is non-fatal. If it fails, `agentStatus` is set to a partial state and `decisionHint` becomes `ACCEPT_CASE_RETRY_OPPORTUNITY_UPDATE`. The case still exists; only the Opportunity link is missing.

---

### Slide 6.17 — service-cloud-mcp: Response Contract

Every response from `/mcp/tool/issue_credit` has this shape:

```json
{
  "status":       "SUCCESS | PARTIAL_SUCCESS | FAILED | REJECTED",
  "caseId":       "<Salesforce Case ID or empty>",
  "opportunityId":"<Salesforce Opportunity ID or empty>",
  "actionType":   "CREATE_CASE | REUSE_CASE | NOOP",
  "agentStatus":  "CASE_CREATED | CASE_REUSED | OPPORTUNITY_UPDATED |
                   REJECTED_INPUT | REJECTED_RISK | FAILED",
  "failureClass": "NONE | BUSINESS_VALIDATION | BUSINESS_REJECTION |
                   TECHNICAL_SALESFORCE | TECHNICAL_PARTIAL",
  "retryable":    true | false,
  "decisionHint": "REJECT_AND_REQUEST_MISSING_FIELDS |
                   REJECT_AND_ESCALATE_FRAUD_REVIEW |
                   ACCEPT_CASE_RETRY_OPPORTUNITY_UPDATE |
                   RETRY_TECHNICAL_FAILURE | NONE",
  "errorCode":    "VALIDATION_MISSING_FIELDS | RISK_POLICY_BLOCK |
                   SFDC_CREATE_TECHNICAL_FAILURE | ...",
  "idempotencyKey": "<key used for this request>",
  "requestId":    "<from x-request-id header>",
  "flowId":       "<from x-flow-id header>",
  "sessionId":    "<from x-session-id header>"
}
```

`decisionHint` is the field the orchestrator uses to determine what to tell the user and what to do next. It is machine-readable but also human-readable when surfaced in a Slack message.

---

### Slide 6.18 — System API Design Principles: Summary

These two apps illustrate the core System API principles in practice:

```
Principle                     data-cloud-sapi            service-cloud-mcp
-----------------------------  -------------------------  --------------------------
Execute, never decide          Returns grounding data.    Returns caseId.
                               Orchestrator decides        Orchestrator decides
                               recommendedAction.          what to tell user.

200 for business outcomes      recommendedAction=CLARIFY   agentStatus=REJECTED_RISK
                               is a 200, not a 404.        is a 200, not a 403.

Idempotency                    Cache by email key (5min)   Query Case by Subject key
                               prevents redundant queries. prevents duplicate cases.

OAuth CC (no user session)     sdc:oauth-client-           salesforce:oauth-client-
                               credentials-connection      credentials-connection

Caller ignorance of internals  Orchestrator calls          Orchestrator calls
                               /api/profile/{slackId}.     /mcp/tool/issue_credit.
                               No SOQL knowledge needed.   No Salesforce knowledge needed.
```

These properties — combined with the MCP tool contract in `service-cloud-mcp` — mean that the Process layer can be swapped out for a different orchestrator without touching either System API.

---

### Slide 6.19 — Module 6 Summary

**data-cloud-sapi (port 8083)**
- Resolves slackId to email, email to Data Cloud party, party to unified profile
- Caches results in Object Store (5-minute TTL, 10,000 entries)
- Returns grounding context that shapes the Bedrock prompt
- Handles identity resolution failures gracefully with fallback response

**service-cloud-mcp (port 8084)**
- Exposes a single MCP tool: `POST /mcp/tool/issue_credit`
- Validates inputs, applies risk policy, checks idempotency
- Creates Salesforce Case with `until-successful` retry
- Links the case to the open Opportunity via four custom fields
- Returns a structured response with `agentStatus`, `decisionHint`, and `retryable`

**The rule that ties them together:**
System APIs return 200 for every business outcome. HTTP 5xx signals technical failure. The calling layer reads the response body to understand what happened.
