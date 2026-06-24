> **Missed earlier exercises? Catch up first:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 6
> ```
> Runs CP1–CP5 and CP6 (deploys all 4 apps to CloudHub with correct secrets).
> Then continue at [Part A](#part-a) below to verify end-to-end flow.

# Exercise 6: Deployment and End-to-End Validation

## Objective

Deploy all four MuleSoft applications to CloudHub 2.0 and verify the complete agent flow from a Slack message through to a Salesforce Case creation.

By the end of this exercise you will have:
- All four apps deployed and healthy on CloudHub 2.0
- Runtime secrets patched via the Anypoint Platform API (not stored in source)
- The AI Gateway verified for field extraction
- The orchestrator verified for all decision paths (APPROVE, ESCALATE, CLARIFY)
- A full Slack-to-Case flow working end-to-end

**Prerequisites**: Exercises 1–5 complete. You have:
- Salesforce org with Data Cloud and Service Cloud configured
- Slack app with bot token and signing secret
- Bedrock agent (`LBD334EPJY`) with alias (`WQ0CS1HYDE`)
- Omni Gateway running with Agent and Tool Instance at `/llmproxy2`
- AI Gateway client ID and secret (from API Manager)

---

## Background

The four apps have dependencies. Deploy in this order to avoid broken health checks:

```
1. data-cloud-sapi        → no Mule dependencies
2. service-cloud-mcp      → no Mule dependencies
3. ai-orchestrator        → depends on data-cloud-sapi, service-cloud-mcp, AI Gateway
4. slack-agent-router     → depends on ai-orchestrator, AI Gateway
```

Each app is deployed with non-secret properties in `pom.xml`. Secrets are patched via the Anypoint Application Manager REST API after deploy — they are never committed to source.

---

## Part A: Pre-deployment Checklist

Gather all values you will need before starting:

| Value | Where to find it | Variable name used below |
|-------|-----------------|--------------------------|
| Anypoint org ID | Anypoint Platform → Access Management → Organisation | `{orgId}` |
| Anypoint environment ID | Access Management → Environments → Sandbox | `{envId}` |
| Connected App client ID | Access Management → Connected Apps | `{anypointClientId}` |
| Connected App client secret | Same | `{anypointClientSecret}` |
| CloudHub target name | Runtime Manager → Shared Spaces | `{targetName}` (e.g. `agentic-enterprise-training`) |
| Slack bot token | Slack API → Your App → OAuth & Permissions | `{slackBotToken}` |
| Slack signing secret | Slack API → Your App → Basic Information | `{slackSigningSecret}` |
| Salesforce client ID | Setup → Connected Apps | `{sfdcClientId}` |
| Salesforce client secret | Same | `{sfdcClientSecret}` |
| Salesforce token endpoint | `https://{yourDomain}.my.salesforce.com/services/oauth2/token` | `{sfdcTokenEndpoint}` |
| Data Cloud instance URL | Setup → Data Cloud → Settings | `{sdcInstanceUrl}` |
| AWS region | Your Bedrock setup | `{awsRegion}` (e.g. `us-east-2`) |
| AWS access key ID | IAM → Users → mulesoft-bedrock-user | `{awsAccessKeyId}` |
| AWS secret access key | Same | `{awsSecretAccessKey}` |
| Bedrock agent ID | Bedrock Console → Agents | `{bedrockAgentId}` (e.g. `LBD334EPJY`) |
| Bedrock agent alias ID | Bedrock Console → Agents → Aliases | `{bedrockAgentAliasId}` (e.g. `WQ0CS1HYDE`) |
| AI Gateway client ID | API Manager → Agent and Tool Instance → Client ID | `{aiGatewayClientId}` |
| AI Gateway client secret | Same | `{aiGatewayClientSecret}` |
| Omni Gateway hostname | Runtime Manager → Gateways | `{gatewayHost}` |
| Secure properties key | Choose a strong passphrase | `{secureKey}` |
| OpenTelemetry auth header | Your observability platform → API key (format: `Bearer <token>`) | `{otelLogsAuthHeader}` |

---

## Part B: Get an Anypoint Access Token

All REST calls to Anypoint use a Bearer token. Obtain one using your Connected App:

```bash
TOKEN=$(curl -s -X POST https://anypoint.mulesoft.com/accounts/api/v2/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id={anypointClientId}&client_secret={anypointClientSecret}" \
  | jq -r '.access_token')
echo $TOKEN
```

Store this as `$TOKEN` in your shell. It expires in 3600 seconds — re-run if you get 401 responses.

---

## Part C: Deploy data-cloud-sapi

### C.1 — Build and deploy

From the `data-cloud-sapi` project directory:

```bash
mvn clean deploy -DskipTests \
  -Danypoint.platform.client_id={anypointClientId} \
  -Danypoint.platform.client_secret={anypointClientSecret}
```

This uses the `<cloudhub2Deployment>` block in `pom.xml`. Wait for the deployment to reach `RUNNING` status (approximately 2–3 minutes).

### C.2 — Verify it started

```bash
curl -s https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items[] | select(.name == "data-cloud-sapi-v1") | {name, status}'
```

Expected: `"status": "RUNNING"`

### C.3 — Patch secrets

```bash
# Get the deployment ID first
DEPLOY_ID=$(curl -s "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[] | select(.name == "data-cloud-sapi-v1") | .id')

curl -s -X PATCH \
  "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments/$DEPLOY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "mule.agent.application.properties.service": {
        "applicationName": "data-cloud-sapi-v1",
        "properties": {
          "sfdc.clientId": "{sfdcClientId}",
          "sfdc.clientSecret": "{sfdcClientSecret}",
          "sfdc.tokenEndpoint": "{sfdcTokenEndpoint}",
          "sfdc.datacloud.instanceUrl": "{sdcInstanceUrl}",
          "secure.key": "{secureKey}"
        }
      }
    }
  }'
```

The app will restart automatically after the property patch.

### C.4 — Health check

Once restarted (allow 60–90 seconds):

```bash
# Get the public URL from Runtime Manager, then:
curl -s https://{data-cloud-sapi-host}/health
# Expected: {"status":"ok","app":"data-cloud-sapi"}
```

---

## Part D: Deploy service-cloud-mcp

### D.1 — Build and deploy

```bash
cd service-cloud-mcp
mvn clean deploy -DskipTests \
  -Danypoint.platform.client_id={anypointClientId} \
  -Danypoint.platform.client_secret={anypointClientSecret}
```

### D.2 — Verify it started and patch secrets

```bash
DEPLOY_ID=$(curl -s "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[] | select(.name == "service-cloud-mcp") | .id')

curl -s -X PATCH \
  "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments/$DEPLOY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "mule.agent.application.properties.service": {
        "applicationName": "service-cloud-mcp",
        "properties": {
          "sfdc.clientId": "{sfdcClientId}",
          "sfdc.clientSecret": "{sfdcClientSecret}",
          "sfdc.tokenEndpoint": "{sfdcTokenEndpoint}"
        }
      }
    }
  }'
```

### D.3 — Verify the MCP tool

```bash
# Valid request — expect status=SUCCESS, agentStatus=CASE_CREATED
curl -s -X POST https://{service-cloud-mcp-host}/mcp/tool/issue_credit \
  -H "Content-Type: application/json" \
  -H "x-user-id: deploy-test-user" \
  -d '{
    "customerId": "DEPLOY-TEST-001",
    "orderNumber": "ORD-DEPLOY-001",
    "amount": 25.00,
    "reason": "deployment verification test"
  }' | jq '{status, agentStatus, caseId}'

# Run the same command again — expect agentStatus=CASE_REUSED with the same caseId
```

---

## Part E: Deploy ai-orchestrator

### E.1 — Build and deploy

```bash
cd ai-orchestrator
mvn clean deploy -DskipTests \
  -Danypoint.platform.client_id={anypointClientId} \
  -Danypoint.platform.client_secret={anypointClientSecret}
```

### E.2 — Patch secrets

> **Note**: The deployed application name in `pom.xml` is `ai-orchestrator-recovery-20260604c`. The `startswith` filter below handles this automatically.

```bash
DEPLOY_ID=$(curl -s "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[] | select(.name | startswith("ai-orchestrator")) | .id')

curl -s -X PATCH \
  "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments/$DEPLOY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "mule.agent.application.properties.service": {
        "applicationName": "ai-orchestrator-recovery-20260604c",
        "properties": {
          "sfdc.username": "{sfdcUsername}",
          "sfdc.password": "{sfdcPassword}",
          "sfdc.token": "{sfdcToken}",
          "aws.accessKeyId": "{awsAccessKeyId}",
          "aws.secretAccessKey": "{awsSecretAccessKey}",
          "bedrock.agentId": "{bedrockAgentId}",
          "bedrock.agentAliasId": "{bedrockAgentAliasId}",
          "ai-gateway.clientId": "{aiGatewayClientId}",
          "ai-gateway.clientSecret": "{aiGatewayClientSecret}",
          "secure.key": "{secureKey}"
        }
      }
    }
  }'
```

### E.3 — Readiness check

```bash
curl -s https://{orchestrator-host}/health/ready | jq .
# Expected: both downstream health checks return status < 500
# {"dataCloud":"UP","serviceCloud":"UP"}
```

### E.4 — Test identity validation

```bash
# Missing x-user-id — should return decision=CLARIFY immediately
curl -s -X POST https://{orchestrator-host}/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"contractVersion":"1.2","requestId":"test-identity","inputText":"refund ORD-001"}' \
  | jq '{response, "decision": .metadata.decision, "failureClassification": .metadata.failureClassification}'
# Expected: decision=CLARIFY, failureClassification=POLICY_REJECTED
```

### E.5 — Test fraud escalation path

```bash
curl -s -X POST https://{orchestrator-host}/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: test-user-001" \
  -d '{
    "contractVersion": "1.2",
    "requestId": "test-fraud-001",
    "flowId": "test-fraud-001",
    "sessionId": "test-fraud-001",
    "inputText": "refund order 999-001 wrong item",
    "structured": {"orderNumber": "999-001", "reason": "wrong item"}
  }' | jq '{response, "decision": .metadata.decision, "riskLevel": .metadata.riskLevel, "decisionSource": .metadata.decisionSource}'
# Expected: decision=ESCALATE, riskLevel=CRITICAL
```

### E.6 — Test happy path (approve)

Find a real order number in your Salesforce org that has an Opportunity with an Amount. Replace `ORD-TEST` below:

```bash
curl -s -X POST https://{orchestrator-host}/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: test-user-001" \
  -d '{
    "contractVersion": "1.2",
    "requestId": "test-approve-001",
    "flowId": "test-approve-001",
    "sessionId": "test-approve-001",
    "inputText": "refund order ORD-TEST wrong item delivered",
    "structured": {"orderNumber": "ORD-TEST", "reason": "wrong item delivered"}
  }' | jq '{
    response,
    decision: .metadata.decision,
    riskLevel: .metadata.riskLevel,
    caseId: .metadata.caseId,
    stageStatus: .metadata.stageStatus,
    decisionSource: .metadata.decisionSource
  }'
# Expected: decision=APPROVE, caseId non-null, stageStatus all OK
```

---

## Part F: Deploy slack-agent-router

### F.1 — Build and deploy

```bash
cd slack-agent-router
mvn clean deploy -DskipTests \
  -Danypoint.platform.client_id={anypointClientId} \
  -Danypoint.platform.client_secret={anypointClientSecret}
```

### F.2 — Patch secrets

```bash
DEPLOY_ID=$(curl -s "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments" \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[] | select(.name == "slack-agent-router") | .id')

curl -s -X PATCH \
  "https://anypoint.mulesoft.com/amc/application-manager/api/v2/organizations/{orgId}/environments/{envId}/deployments/$DEPLOY_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "mule.agent.application.properties.service": {
        "applicationName": "slack-agent-router",
        "properties": {
          "slack.botToken": "{slackBotToken}",
          "slack.signingSecret": "{slackSigningSecret}",
          "ai-gateway.clientId": "{aiGatewayClientId}",
          "ai-gateway.clientSecret": "{aiGatewayClientSecret}",
          "otel.logs.authHeader": "{otelLogsAuthHeader}",
          "secure.key": "{secureKey}"
        }
      }
    }
  }'
```

### F.3 — Update Slack Event Subscriptions URL

1. Go to your Slack app at `api.slack.com/apps`
2. Navigate to **Event Subscriptions**
3. Update the **Request URL** to: `https://{slack-agent-router-host}/slack/events`
4. Slack will send a challenge — the app must respond immediately with the `challenge` value
5. Wait for the green **Verified** tick

### F.4 — Update Slack Interactivity URL

1. Navigate to **Interactivity & Shortcuts**
2. Update the **Request URL** to: `https://{slack-agent-router-host}/slack/interactivity`
3. Save changes

> **Note**: The path is `/slack/interactivity` (matches the Mule listener). Exercise 2 also used this path — if you set it there, it is already correct.

### F.5 — Health check

```bash
curl -s https://{slack-agent-router-host}/health
# Expected: {"status":"ok","service":"slack-agent-router",...}
```

---

## Part G: End-to-End Slack Flow

### G.1 — Safe refund (happy path)

1. Open Slack and find a channel where your bot is present
2. Type: `@{botName} refund ORD-TEST wrong item delivered`
3. The bot should respond in the thread within 2–3 seconds with a confirmation modal
4. Review the pre-filled order number and reason — click **Confirm**
5. The bot updates the thread:
   ```
   🎬 *Refund pipeline is running...*
   • ✅ Intake confirmed (instant)
   • ☁️ Data Cloud context (~6-7s)
   • 🧠 Bedrock risk + decision (~23-26s)
   • 🛠️ Service Cloud mutation (~3s when eligible)
   ```
6. After ~30 seconds the message updates with the final result:
   ```
   *Refund decision:* APPROVE
   *Reason:* wrong item delivered
   *Risk:* SAFE (score 14)
   *Credit action:* Issue credit
   *Case Reference:* 5004K...
   ```
7. Verify in Salesforce: the Case exists, the Opportunity has the refund fields populated

### G.2 — Fraud escalation

1. Type: `@{botName} refund 999-001 unauthorized charge`
2. Confirm the modal
3. Expected response: `decision: ESCALATE`, `riskLevel: CRITICAL` — no Case created

### G.3 — Identity ambiguity test

This can only be simulated by calling the orchestrator directly without an `x-user-id` header (the router always sets one). See Part E.4 above.

---

## Part H: Local Runtime Verification (Optional)

If you want to run the full stack locally before CloudHub deployment, use the local runtime:

```bash
cd <your-projects-dir>/mule-local-runtime
./run.sh
```

This starts all four apps on ports 8081–8084 (with 8092 for the orchestrator HTTPS listener). The `wrapper.conf` supplies all secrets for local dev.

Verify locally:
```bash
# data-cloud-sapi
curl -s http://localhost:8083/api/profile/test-user | jq .

# service-cloud-mcp
curl -s -X POST http://localhost:8084/mcp/tool/issue_credit \
  -H "Content-Type: application/json" -H "x-user-id: test-user" \
  -d '{"customerId":"C001","orderNumber":"ORD-LOCAL-001","amount":10,"reason":"test"}' | jq .

# ai-orchestrator
curl -s -X POST http://localhost:8082/api/orchestrate \
  -H "Content-Type: application/json" -H "x-user-id: test-user" \
  -d '{"contractVersion":"1.2","requestId":"local-001","flowId":"local-001",
       "sessionId":"local-001","inputText":"refund ORD-LOCAL-001 wrong item",
       "structured":{"orderNumber":"ORD-LOCAL-001","reason":"wrong item"}}' | jq .
```

Note: the local runtime uses `scanner.enabled=false` and placeholder AI Gateway credentials. Bedrock calls go through `BedrockDirectInvoker` if `aws.accessKeyId` is set in `wrapper.conf`, otherwise fall back to mimic-risk.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Deploy fails: `401 Unauthorized` | Wrong connected app credentials in mvn command | Verify `-Danypoint.platform.client_id` value |
| App starts but health returns 503 | Downstream app not yet deployed/running | Deploy in order: data-cloud → service-cloud → orchestrator → router |
| Slack URL verification fails | App not yet running or wrong URL | Check app is RUNNING; URL must be `https://host/slack/events` exactly |
| Modal opens but Confirm does nothing | Interactivity URL wrong or not saved | Update and save Slack Interactivity URL |
| `decision=CLARIFY`, `failureClassification=POLICY_REJECTED` with valid request | `x-user-id` header not set | Router always sets it; if calling orchestrator directly, include `-H "x-user-id: somevalue"` |
| `stageDataCloud=FAIL` in response | Data Cloud credentials wrong or token endpoint wrong | Re-patch `sfdc.clientId/clientSecret/tokenEndpoint` on data-cloud-sapi |
| `stageServiceCloud=FAIL`, no caseId | Service Cloud credentials wrong or custom fields missing | Check fields `Refund_*__c` exist on Opportunity (Exercise 5 Part G.2) |
| `stageGateway=DEGRADED`, `decisionSource=bedrock` | AI Gateway down but Bedrock direct succeeded | Check Omni Gateway status; verify `/llmproxy2` route exists |
| `stageGateway=DEGRADED`, `decisionSource=mimic` | Both AI Gateway and direct Bedrock failed | Check AWS credentials; verify Bedrock agent is in PREPARED status |
| `refundAmountSource=unresolved_salesforce` | No Opportunity matching order number | Create an Opportunity in Salesforce with a Name containing the order number |
| Duplicate Slack responses | Slack event delivered twice, dedup store missed | Check `SlackEventDedupeStore` TTL (30 min); Slack retries for up to 3 attempts |
| Property patch returns 200 but secrets still wrong | App did not restart after patch | Manually restart from Runtime Manager |

---

## Key Properties Reference

### slack-agent-router

| Property | Source | Description |
|----------|--------|-------------|
| `slack.botToken` | Runtime Manager (secret) | Slack Bot OAuth token (`xoxb-...`) |
| `slack.signingSecret` | Runtime Manager (secret) | Slack request signature verification |
| `ai-gateway.host` | `dev-config.yaml` | Omni Gateway hostname |
| `ai-gateway.basePath` | `dev-config.yaml` | `/llmproxy2` |
| `ai-gateway.clientId` | Runtime Manager (secret) | Client-ID-Enforcement client ID |
| `ai-gateway.clientSecret` | Runtime Manager (secret) | Client-ID-Enforcement secret |
| `otel.logs.authHeader` | Runtime Manager (secret) | OpenTelemetry logs auth header (format: `Bearer <token>`) |
| `orchestrator.host` | `dev-config.yaml` | ai-orchestrator hostname |

### ai-orchestrator

| Property | Source | Description |
|----------|--------|-------------|
| `sfdc.username` | Runtime Manager (secret) | Salesforce username (basic auth — see issue #44) |
| `sfdc.password` | Runtime Manager (secret) | Salesforce password |
| `sfdc.token` | Runtime Manager (secret) | Salesforce security token |
| `aws.accessKeyId` | Runtime Manager (secret) | AWS IAM access key |
| `aws.secretAccessKey` | Runtime Manager (secret) | AWS IAM secret key |
| `bedrock.agentId` | Runtime Manager (secret) | Bedrock agent ID |
| `bedrock.agentAliasId` | Runtime Manager (secret) | Bedrock agent alias ID |
| `ai-gateway.clientId` | Runtime Manager (secret) | AI Gateway client ID (for risk assessment path) |
| `ai-gateway.clientSecret` | Runtime Manager (secret) | AI Gateway client secret |
| `data-cloud.host` | `dev-config.yaml` | data-cloud-sapi hostname |
| `service-cloud-mcp.host` | `dev-config.yaml` | service-cloud-mcp hostname |

### data-cloud-sapi

| Property | Source | Description |
|----------|--------|-------------|
| `sfdc.clientId` | Runtime Manager (secret) | Connected App client ID for Data Cloud |
| `sfdc.clientSecret` | Runtime Manager (secret) | Connected App client secret |
| `sfdc.tokenEndpoint` | Runtime Manager (secret) | OAuth token URL |
| `sfdc.datacloud.instanceUrl` | Runtime Manager (secret) | Data Cloud instance URL |

### service-cloud-mcp

| Property | Source | Description |
|----------|--------|-------------|
| `sfdc.clientId` | Runtime Manager (secret) | Connected App client ID for Service Cloud |
| `sfdc.clientSecret` | Runtime Manager (secret) | Connected App client secret |
| `sfdc.tokenEndpoint` | Runtime Manager (secret) | OAuth token URL |
