> **Missed earlier exercises? Catch up first:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 3
> ```
> Runs CP1 (Salesforce), CP2 (Slack app), and CP3 (Lambda + Bedrock Agent + Bedrock alias).
> Then continue at [Part A](#part-a-iam-and-aws-setup) below.

# Exercise 3: AWS Bedrock Agent + MuleSoft AI Gateway

## Objective

Configure Amazon Bedrock as the enterprise fraud-detection engine and connect it to MuleSoft's AI Gateway. By the end of this exercise you will have:

- An IAM user with permissions for Bedrock and the MuleSoft Agent Scanner
- A Lambda function that simulates enterprise fraud scoring
- A Bedrock Agent ("MuleSoft-Returns-Agent") with two Action Groups enforcing a mandatory tool order
- An Agent and Tool Instance in Anypoint API Manager providing governed LLM access (field extraction + risk queries)
- An Agent Scanner in Anypoint Exchange that discovers and catalogs the Bedrock Agent for governance
- The ai-orchestrator configured to invoke the Bedrock Agent directly via the AWS SDK (fraud scoring path)

## Background

The enterprise has years of call center data in AWS. That historical data powers a fraud-detection engine (Amazon Bedrock) that evaluates whether a refund request is legitimate before any action is taken.

Bedrock serves **two distinct purposes** in this architecture:

1. **Foundation model access** (Claude Haiku via the AI Gateway) — the `slack-agent-router` uses this for natural-language extraction: parsing order numbers and reasons from free-text messages
2. **Agent invocation** (MuleSoft-Returns-Agent via AWS SDK) — the `ai-orchestrator` calls the Bedrock Agent directly to trigger the Fraud_Scorer Lambda and get a risk decision

MuleSoft provides governance across both paths:

- The **AI Gateway** (an Agent and Tool Instance on the Omni Gateway) handles SigV4 signing, Client-ID-Enforcement, rate limiting, and message logging for the foundation model
- The **Agent Scanner** discovers the Bedrock Agent and publishes it to Exchange — providing enterprise-wide visibility into what AI agents exist, what models they use, and what data they can access

**Architecture flow:**

```
Slack → slack-agent-router
              │
              │  ① EXTRACTION (governed via AI Gateway)
              ▼
┌──────────────────────────────────────────────┐
│  Omni Gateway (Agent and Tool Instance)       │
│  Path: /llmproxy2/chat/completions           │
│  Policies: Client-ID-Enforcement, Logging    │
│  SigV4 signing → bedrock-runtime             │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
              Claude Haiku (foundation model)
              → extracts: {"orderNumber": "ORD-123", "reason": "damaged"}
              
              │
              ▼
        ai-orchestrator
              │
              │  ② FRAUD SCORING (direct SDK invocation)
              ▼
┌──────────────────────────────────────────────┐
│  Amazon Bedrock Agent Runtime (AWS SDK)       │
│  Agent: MuleSoft-Returns-Agent               │
│  Action Groups:                              │
│    Fraud_Scorer → Lambda → risk assessment   │
│    Process_Refund (if SAFE)                  │
└──────────────────────────────────────────────┘

              │
              │  ③ GOVERNANCE (Scanner)
              ▼
┌──────────────────────────────────────────────┐
│  Anypoint Exchange (Agent Registry)           │
│  Scanner-published metadata:                 │
│    • Agent ID, model, instructions           │
│    • Endpoint URL, version, status           │
│    • Continuous daily sync                   │
└──────────────────────────────────────────────┘
```

**Why two paths?** The Bedrock InvokeAgent API requires AWS SigV4 signing and uses a streaming protocol incompatible with the LLM Proxy's OpenAI-compatible request format. The AI Gateway governs foundation model access (extraction, summarization). The agent invocation uses the AWS SDK directly for full Action Group support (tool calling, multi-turn, Lambda execution). Scanner provides the governance layer — visibility, compliance, and metadata sync — without requiring the agent to speak A2A protocol.

---

## Prerequisites

| Item | Value |
|------|-------|
| AWS Account | Free tier eligible; credit card required |
| AWS Region | **US East 2 (Ohio)** — `us-east-2` |
| Anypoint Platform | Access to API Manager and Exchange |
| Anypoint Environment | Sandbox |
| Model Access | Claude Sonnet must be enabled in Bedrock Model Access |

---

## Part A: AWS IAM User Setup

### A.1 — Create an IAM User

1. Sign in to the AWS Management Console
2. Navigate to **IAM** (search "IAM" in the top search bar)
3. In the left navigation, click **Users**
4. Click **Create user**
5. Enter a **User name**: `mulesoft-bedrock-user`
6. Check **Provide user access to the AWS Management Console** (optional — only needed if you want this user to sign in to console)
7. Click **Next**
8. On the **Set permissions** page, select **Attach policies directly**
9. Search for and check: **AmazonBedrockFullAccess**
10. Click **Next**, then **Create user**

### A.2 — Create Access Keys

1. Click into the user `mulesoft-bedrock-user`
2. Click the **Security credentials** tab
3. Under **Access keys**, click **Create access key**
4. Select **Third-party service** as the use case
5. Acknowledge the warning and click **Next**
6. (Optional) Add a description tag: `MuleSoft AI Gateway`
7. Click **Create access key**
8. **Record both values immediately** — the Secret Access Key is shown only once:

| Credential | Store Securely |
|-----------|---------------|
| Access Key ID | `AKIA...` |
| Secret Access Key | (shown once — copy now) |

### A.3 — Create a Custom Policy for Agent Scanner

The MuleSoft Agent Scanner needs specific permissions to discover Bedrock agents. Create a least-privilege policy:

1. In IAM, click **Policies** in the left navigation
2. Click **Create policy**
3. Click the **JSON** tab
4. Paste the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentDiscoveryPermissions",
            "Effect": "Allow",
            "Action": [
                "bedrock:ListAgents",
                "bedrock:GetAgent",
                "bedrock:ListAgentAliases",
                "bedrock:GetAgentAlias",
                "bedrock:InvokeModel",
                "bedrock:InvokeAgent"
            ],
            "Resource": "*"
        }
    ]
}
```

5. Click **Next**
6. Name the policy: `bedrock_for_scanner`
7. Click **Create policy**

### A.4 — Attach the Scanner Policy

1. Go back to **Users** → `mulesoft-bedrock-user`
2. Click **Add permissions** → **Attach policies directly**
3. Search for `bedrock_for_scanner` and check it
4. Click **Add permissions**

**Final policy summary for this user:**

| Policy | Type | Purpose |
|--------|------|---------|
| AmazonBedrockFullAccess | AWS Managed | Full Bedrock access (agent creation, model invocation) |
| bedrock_for_scanner | Customer Managed | Least-privilege for MuleSoft Agent Scanner discovery |

---

## Part B: Create the Fraud Scoring Lambda Function

### B.1 — Create the Lambda Function

1. Navigate to **Lambda** in the AWS Console (search "Lambda")
2. Verify region is **US East 2 (Ohio)** in the top-right dropdown
3. Click **Create function**
4. Select **Author from scratch**
5. Configure:

| Field | Value |
|-------|-------|
| Function name | `Fraud_Scorer_Lambda` |
| Runtime | Python 3.12 |
| Architecture | x86_64 |
| Execution role | Create a new role with basic Lambda permissions |

6. Click **Create function**

### B.2 — Deploy the Function Code

1. In the **Code source** editor, replace the contents of `lambda_function.py` with:

```python
import json

def lambda_handler(event, context):
    print(f"Incoming Event: {json.dumps(event)}")
    order_number = ""
    if 'parameters' in event:
        for param in event['parameters']:
            if param['name'] == 'orderNumber':
                order_number = param['value']

    is_velocity_anomaly = str(order_number).startswith("999")
    if is_velocity_anomaly:
        risk_score = 95
        risk_level = "CRITICAL"
        message = "Velocity Anomaly: High frequency of orders detected from this account prefix."
    else:
        risk_score = 14
        risk_level = "SAFE"
        message = "Telemetry nominal. IP and velocity within normal bounds."

    stringified_data = json.dumps({
        "orderNumber": order_number,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "fraudEngineMessage": message
    })

    response_body = {"TEXT": {"body": stringified_data}}
    action_response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get('actionGroup', 'Fraud_Scorer_Group'),
            "function": event.get('function', 'Amazon_Fraud_Scorer'),
            "functionResponse": {"responseBody": response_body}
        }
    }
    return action_response
```

2. Click **Deploy**

**Logic explanation:**
- Orders starting with `999` are flagged as CRITICAL (risk score 95) — simulates velocity anomaly detection
- All other orders return SAFE (risk score 14)
- The response format follows Bedrock's required Lambda response structure: `messageVersion` + `response` with `actionGroup`, `function`, and `functionResponse`

### B.3 — Test the Lambda Function

1. Click **Test** (orange button)
2. Create a new test event named `SafeOrder`:

```json
{
    "messageVersion": "1.0",
    "actionGroup": "Fraud_Scorer_Group",
    "function": "Fraud_Scorer",
    "parameters": [
        {
            "name": "orderNumber",
            "type": "string",
            "value": "ORD-12345"
        }
    ]
}
```

3. Click **Test** — verify the response includes `"riskLevel": "SAFE"`
4. Create a second test event named `FraudulentOrder`:

```json
{
    "messageVersion": "1.0",
    "actionGroup": "Fraud_Scorer_Group",
    "function": "Fraud_Scorer",
    "parameters": [
        {
            "name": "orderNumber",
            "type": "string",
            "value": "999-SUSPICIOUS"
        }
    ]
}
```

5. Click **Test** — verify the response includes `"riskLevel": "CRITICAL"`

### B.4 — Record the Lambda ARN

1. At the top of the function page, copy the **Function ARN**:
   - Format: `arn:aws:lambda:us-east-2:<ACCOUNT_ID>:function:Fraud_Scorer_Lambda`
2. Record this — you will need it when creating the Bedrock Action Group

---

## Part C: Create the Bedrock Agent

### C.1 — Enable Model Access

Before creating an agent, the foundation model must be enabled:

1. Navigate to **Amazon Bedrock** in the AWS Console
2. In the left navigation under **Bedrock configurations**, click **Model access**
3. Click **Modify model access**
4. Find **Anthropic** → check **Claude Sonnet** (or the Claude model available in your region)
5. Click **Next** → **Submit**
6. Wait for the Access status to show **Access granted**

### C.2 — Create the Agent

1. In the Bedrock left navigation under **Build**, click **Agents**
2. Click **Create Agent**
3. Enter:

| Field | Value |
|-------|-------|
| Agent name | `MuleSoft-Returns-Agent` |
| Agent description | `Training` |

4. Click **Create** — this opens the **Agent builder**

### C.3 — Configure the Agent Builder

In the Agent builder page:

1. **Agent resource role**: Leave as "Create and use a new service role" (auto-generates a role named `AmazonBedrockExecutionRoleForAgents_<ID>`)
2. **Select model**: Click the pencil icon and select **Claude Sonnet** (Anthropic)
3. **Instructions for the Agent** — paste the following:

```
You are the MuleSoft Returns Service. You act as an agent responsible for securely processing customer returns. You have access to AWS Bedrock risk tools and enterprise validation tools via MuleSoft.

Your primary directive is SECURITY and COMPLIANCE. You must act as the cognitive permission for this enterprise.

MANDATORY TOOL ORDER FOR EVERY REFUND REQUEST:
1. FIRST call function 'Fraud_Scorer' to get a fraud risk assessment for the order.
2. ONLY if the Fraud_Scorer returns riskLevel "SAFE" may you proceed to call 'Process_Refund'.
3. NEVER process a refund without a Fraud_Scorer result first.
4. If Fraud_Scorer returns riskLevel "CRITICAL", DENY the refund and explain why.

Your job is to ask the customer for their Order Number and the Reason for the return. Once you have both pieces of information, confidently tell the customer that their return has been processed and a refund will be issued.
```

4. Under **Additional settings**:
   - **User input**: Disabled
   - **Idle session timeout**: 600 seconds

5. Click **Save** (top-right of the Agent builder)

### C.4 — Add Action Group: Fraud_Scorer

1. In the **Action groups** section, click **Add**
2. Configure the **Action group details**:

| Field | Value |
|-------|-------|
| Action group name | (auto-generated — leave default or rename to identify as Fraud_Scorer group) |
| Description | (optional) |

3. **Action group type**: Select **Define with function details**
4. **Action group invocation**: Select **Select an existing Lambda function**
5. Choose `Fraud_Scorer_Lambda` from the dropdown and select the `$LATEST` version

> **Note**: If this is the first time connecting Bedrock to this Lambda, a resource-based policy will be automatically added granting `bedrock.amazonaws.com` permission to invoke the function.

6. Under **Action group function 1**, configure:

| Field | Value |
|-------|-------|
| Function name | `Fraud_Scorer` |
| Description | (optional) |
| Enable confirmation | Unchecked |

7. Under **Parameters**, click **Add parameter**:

| Name | Description | Type | Required |
|------|-------------|------|----------|
| `orderNumber` | The order number | string | True |

8. Click **Add** (save the action group)

### C.5 — Add Action Group: Process_Refund

1. Back in the Agent builder, click **Add** in the Action groups section again
2. Configure:

| Field | Value |
|-------|-------|
| Action group name | (auto-generated) |
| Description | (optional) |

3. **Action group type**: Select **Define with function details**
4. **Action group invocation**: Select **Quick create a new Lambda function (recommended)**

> This creates a placeholder Lambda. In the real implementation, the ai-orchestrator handles process routing — this function exists to let the Bedrock agent complete its reasoning chain.

5. Under **Action group function 1**, configure:

| Field | Value |
|-------|-------|
| Function name | `Process_Refund` |
| Description | (optional) |
| Enable confirmation | Unchecked |

6. Under **Parameters**, add two parameters:

| Name | Description | Type | Required |
|------|-------------|------|----------|
| `reason` | The exact reason the user is returning the item. This field is mandatory. | string | True |
| `orderNumber` | Order number. This field is mandatory. | string | True |

7. Click **Add**

### C.6 — Prepare and Test the Agent

1. In the Agent builder, click **Prepare** (top-right)
2. Wait for the status to show **Prepared** (green badge)
3. In the **Test** panel on the right, type:

```
I'd like to return order ORD-12345 because it arrived damaged.
```

4. Verify the agent:
   - First calls `Fraud_Scorer` with orderNumber "ORD-12345"
   - Gets back riskLevel "SAFE"
   - Then calls `Process_Refund` with the reason and order number
   - Responds confirming the refund

5. Test the fraud detection by typing:

```
I need a refund for order 999-BULK-RETURN
```

6. Verify the agent:
   - Calls `Fraud_Scorer` with orderNumber "999-BULK-RETURN"
   - Gets back riskLevel "CRITICAL"
   - DENIES the refund and explains the velocity anomaly

### C.7 — Create a Version and Alias

1. Navigate back to the **Agent Details** page (click the agent name in the breadcrumb)
2. In the **Versions** section, note that Version 1 may already exist
3. In the **Aliases** section, click **Create**
4. Configure:

| Field | Value |
|-------|-------|
| Alias name | `Production-v1` |
| Description | (optional) |
| Associate a version | Create a new version and associate it to this alias |

5. Click **Create alias**

### C.8 — Record Agent Details

From the Agent Details page, record:

| Detail | Value | Where to Find |
|--------|-------|---------------|
| Agent ID | `LBD334EPJY` (yours will differ) | Agent overview → ID |
| Agent ARN | `arn:aws:bedrock:us-east-2:<ACCOUNT_ID>:agent/<AGENT_ID>` | Agent overview → Agent ARN |
| Alias ID | Shown in the Aliases table | Aliases section → Alias ID column |
| Alias name | `Production-v1` | Aliases section → Alias name column |
| Status | PREPARED | Agent overview → Status |

---

## Part D: MuleSoft AI Gateway — Agent and Tool Instance

The AI Gateway provides governed access to the Bedrock foundation model through an Agent and Tool Instance deployed on the Omni Gateway. This instance handles AWS SigV4 credential signing, Client-ID-Enforcement, rate limiting, and message logging — so individual MuleSoft apps never hold AWS credentials directly.

### D.1 — Navigate to Agent and Tool Instances

1. Log in to **Anypoint Platform** at `https://anypoint.mulesoft.com`
2. From the top navigation, go to **Agents & Tools** → **API Manager**
3. In the left navigation, click **Agent and Tool Instances**
4. Verify you are in the **Sandbox** environment (toggle in the left panel if needed)

### D.2 — Create an Instance

1. Click **Add** (or **Add Protect Agent server**)
2. You will see a Settings page with **Runtime**, **Downstream**, and **Upstream** sections

### D.3 — Configure the Runtime Section

| Field | Value |
|-------|-------|
| Runtime type | Omni Gateway |
| Target type | Managed Gateway in CloudHub 2 |
| Gateway | Select your Omni Gateway (e.g., `agenticenterprisetraining-small`) |

### D.4 — Configure the Downstream Section

| Field | Value |
|-------|-------|
| Origin of request traffic | Private Space Ingress |
| Port | `8081 (ingress)` |
| Base path | `/llmproxy2` |
| Client provider | Anypoint |
| Manual approval | Unchecked (requests approved automatically) |
| Consumer endpoint | (optional — displays the consumer-facing URL) |

> **Why `/llmproxy2`?** The base path is the unique identifier for this instance on the gateway. Multiple instances can coexist on the same gateway with different paths. Your MuleSoft apps will call `https://<gateway-host>/llmproxy2/chat/completions`.

### D.5 — Configure the Upstream Section

Add an upstream URL that routes to the Bedrock foundation model:

| Field | Value |
|-------|-------|
| Upstream URL | `https://bedrock-runtime.us-east-2.amazonaws.com/` |
| Upstream Label | `bedrockanthropic` |
| TLS Context | (click Add TLS Context if prompted) |
| Route | Route A |

> **Important**: This upstream targets `bedrock-runtime` (foundation model inference) — NOT `bedrock-agent-runtime` (agent invocation). The AI Gateway handles model calls for extraction and summarization. Agent invocation (with Action Groups and Lambda) goes through the AWS SDK directly.

### D.6 — Configure the Outbound Route

After saving the instance, navigate to the route configuration:

| Field | Value |
|-------|-------|
| Routing strategy | Model-based |
| LLM Provider | Bedrock Anthropic |
| AWS Access Key ID | (from Part A.2 — Static mode) |
| AWS Secret Access Key | (from Part A.2) |
| URL | `https://bedrock-runtime.us-east-2.amazonaws.com/` |
| AWS Session Token | (leave empty unless using temporary credentials) |
| AWS Region | US East 2 (Ohio) |
| Target Model | `us.anthropic.claude-3-haiku-20240307-v1:0` |

Click **Save** or **Apply**.

> A banner may appear: "Applying a new configuration will trigger a redeployment, which may cause a brief service interruption." This is expected.

### D.7 — Apply Client-ID-Enforcement Policy

1. In the left navigation, click **Policies**
2. Click **Add Policy**
3. Select **Client-ID-Enforcement**
4. Configure to require `client_id` and `client_secret` headers
5. Apply the policy

> This ensures only authorized MuleSoft apps (with Exchange application credentials) can call the AI Gateway.

### D.8 — Apply LLM Token Rate Limit Policy

This is where the Anypoint Platform governance story becomes concrete: the **same policy framework** used for REST APIs now governs LLM traffic. Token-based rate limiting prevents a runaway `assess-risk` loop or a misconfigured client from exhausting your Bedrock quota.

1. In the left navigation, click **Policies**
2. Click **Add Policy**
3. Search for and select **LLM Token Based Rate Limit**
4. Configure:

| Field | Value |
|-------|-------|
| Maximum tokens | `100000` (100k tokens per window) |
| Time period | `60000` ms (1 minute) |
| Key selector | `#[authentication.clientId]` (per client ID — each app gets its own bucket) |
| Clusterizable | Checked |
| Expose headers | Checked (returns `x-ratelimit-*` headers so callers can see their remaining quota) |

5. Click **Apply**

> **Why per client ID?** The `slack-agent-router` and any future app each get their own 100k token/min allowance. A misbehaving app doesn't starve others. Exposing the rate-limit headers lets MuleSoft apps back off gracefully before hitting the limit.

**Alternatively — apply via API:**

```bash
TOKEN=$(curl -s -X POST "https://anypoint.mulesoft.com/accounts/api/v2/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=<YOUR_CLIENT_ID>&client_secret=<YOUR_CLIENT_SECRET>" \
  | jq -r '.access_token')

curl -s -X POST \
  "https://anypoint.mulesoft.com/apimanager/api/v1/organizations/<ORG_ID>/environments/<ENV_ID>/apis/<API_INSTANCE_ID>/policies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "groupId": "68ef9520-24e9-4cf2-b2f5-620025690913",
    "assetId": "llm-token-rate-limit",
    "assetVersion": "1.0.1",
    "pointcutData": null,
    "implementationAsset": {
      "groupId": "68ef9520-24e9-4cf2-b2f5-620025690913",
      "assetId": "llm-token-rate-limit-policy-flex",
      "version": "1.0.2",
      "technology": "flexGateway"
    },
    "configurationData": {
      "maximumTokens": 100000,
      "timePeriodInMilliseconds": 60000,
      "keySelector": "#[authentication.clientId]",
      "clusterizable": true,
      "exposeHeaders": true
    }
  }'
```

### D.9 — Apply LLM PII Detection Policy

The Bedrock prompts sent through this gateway contain customer email addresses, order data, and loyalty tier information. The PII Detection policy intercepts outbound prompts and applies masking before they reach the model — a defence-in-depth layer on top of the DataWeave `sanitize.dwl` in `ai-orchestrator`.

1. In the left navigation, click **Policies**
2. Click **Add Policy**
3. Search for and select **LLM PII Detection**
4. Configure:

| Field | Value |
|-------|-------|
| Entities to detect | `Email`, `Credit Card`, `Phone Number` |
| Action | `Log and mask` |

5. Click **Apply**

> **Action options explained:**
> - `Reject` — blocks the entire request if PII is detected (use for strict compliance environments)
> - `Log` — logs the detection event without modifying the prompt
> - `Log and mask` — redacts matches in the prompt before forwarding to Bedrock, and logs that it did so. This is the right default for training — the model still gets a useful prompt, and you have an audit trail.

**Alternatively — apply via API:**

```bash
curl -s -X POST \
  "https://anypoint.mulesoft.com/apimanager/api/v1/organizations/<ORG_ID>/environments/<ENV_ID>/apis/<API_INSTANCE_ID>/policies" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "groupId": "68ef9520-24e9-4cf2-b2f5-620025690913",
    "assetId": "llm-pii-detection-policy",
    "assetVersion": "1.0.0",
    "pointcutData": null,
    "implementationAsset": {
      "groupId": "68ef9520-24e9-4cf2-b2f5-620025690913",
      "assetId": "llm-pii-detection-policy-flex",
      "version": "1.0.1",
      "technology": "flexGateway"
    },
    "configurationData": {
      "entities": ["Email", "Credit Card", "Phone Number"],
      "action": "Log and mask"
    }
  }'
```

**Final policy stack on the AI Gateway (in order):**

| Order | Policy | Purpose |
|-------|--------|---------|
| 1 | CORS | Cross-origin access control |
| 2 | DataWeave Headers Transformation | `apikey` header → `client_id` / `client_secret` split |
| 3 | Client-ID-Enforcement | Only authorized Exchange apps may call |
| 4 | LLM Proxy Core | Token counting, request enrichment |
| 5 | Model-Based Routing | Routes to Claude Haiku via `bedrockanthropic` header |
| 6 | Bedrock Anthropic Transcoding | OpenAI format → Bedrock Anthropic format |
| 7 | Bedrock LLM Provider | AWS SigV4 signing, region config |
| 8 | **LLM Token Rate Limit** | 100k tokens/min per client ID ← *just added* |
| 9 | **LLM PII Detection** | Mask Email, Credit Card, Phone Number; Log and mask ← *just added* |

> This is the enterprise value of Anypoint Platform: the same governance layer that applies Client-ID-Enforcement and rate limiting to your REST APIs now applies to every LLM call — without modifying a single line of application code.

### D.10 — Verify the AI Gateway

Test the endpoint from your terminal:

```bash
curl -s -X POST "https://<your-gateway-host>/llmproxy2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "client_id: <your-exchange-app-client-id>" \
  -H "client_secret: <your-exchange-app-client-secret>" \
  -d '{
    "model": "us.anthropic.claude-3-haiku-20240307-v1:0",
    "messages": [
      {"role": "system", "content": "Extract refund fields as JSON: {\"orderNumber\": string|null, \"reason\": string|null}. Return JSON only."},
      {"role": "user", "content": "I need a refund for order ORD-12345 because it arrived damaged"}
    ],
    "max_tokens": 200
  }'
```

Expected response (OpenAI-compatible format):
```json
{
  "choices": [{
    "message": {
      "content": "{\"orderNumber\": \"ORD-12345\", \"reason\": \"arrived damaged\"}"
    }
  }]
}
```

**Record the following for MuleSoft app configuration:**

| Property | Value |
|----------|-------|
| `ai-gateway.host` | `<your-gateway-host>` (e.g., `agenticenterprisetraining-small-835dgu.wdob74.usa-e2.cloudhub.io`) |
| `ai-gateway.basePath` | `/llmproxy2` |
| `ai-gateway.modelId` | `us.anthropic.claude-3-haiku-20240307-v1:0` |
| `ai-gateway.clientId` | Your Exchange application's Client ID |
| `ai-gateway.clientSecret` | Your Exchange application's Client Secret |

---

## Part E: MuleSoft Exchange — Agent Scanner

The Agent Scanner automatically discovers Bedrock agents and publishes them as governed assets in Anypoint Exchange. Its purpose is **governance and visibility** — answering "what AI agents exist in our enterprise, what models do they use, and what can they do?" It continuously syncs metadata so the registry stays accurate as agents evolve.

> **What Scanner does NOT do**: Scanner does not create an invocation endpoint. Bedrock agents use AWS's proprietary InvokeAgent API (not A2A protocol), so they are classified as `protocol: "other"` in the registry. Invocation is handled by the AWS SDK in the ai-orchestrator. Scanner provides the governance layer — ensuring these agents are visible, tracked, and auditable.

### E.1 — Navigate to Agent Scanners

1. In Anypoint Platform, navigate to **Agents & Tools** → **Exchange**
2. In the left navigation, click **Scanners**

### E.2 — Create a Scanner

1. Click **Add Scanner**
2. Configure:

| Field | Value |
|-------|-------|
| Scanner name | (your name or descriptive label) |
| Agent Provider | Amazon Bedrock |
| Authentication Method | Access Keys |
| Access Key ID | (from Part A.2) |
| Secret Access Key | (from Part A.2) |
| AWS Region | `us-east-2` |

3. Click **Test Connection**
4. Verify the message: **"Connection verified successfully"**
5. Click **Add Scanner**

### E.3 — Run the Scanner

1. The scanner starts in **Scheduled** status (next automatic run is daily)
2. From the **actions menu** (three dots or dropdown next to the scanner), select **Run Now**
3. Wait for the scanner status to change:
   - **Importing** → **Scheduled** (scan complete)
4. Verify **Total agents imported** shows at least **1**

### E.4 — Verify the Agent in Exchange

1. Click on the scanner name to view scan history
2. Click on the scan history output
3. Under the scan review, you should see the asset: **MuleSoft-Returns-Agent**
4. Click on the asset name — this opens the Exchange asset page

**What the scanner published:**

| Field | Value |
|-------|-------|
| Asset name | MuleSoft-Returns-Agent |
| Type | Bedrock Agents |
| Agent ID | LBD334EPJY (your ID) |
| Status | PREPARED |
| Foundation Model | `arn:aws:bedrock:us-east-2:<ACCOUNT_ID>:inference-profile/us.anthropic.claude-sonnet-4-v1:0` |
| Region | us-east-2 |
| URL | `https://bedrock-agent-runtime.us-east-2.amazonaws.com/agents/<ID>/agentAliases/<ALIAS_ID>/sessions` |

> This asset is **managed by the scanner** — any future scan can update this asset automatically.

### E.5 — Verify My Applications

1. In Exchange, click **My applications** in the left navigation
2. Confirm you see: `Salesforce_Integrations_Client_Application_<ORG_ID>`
3. This is the client application that will request access to the AI Gateway Proxy API

### E.6 — Request Access to the AI Gateway Proxy

1. Navigate to the **MuleSoft-Returns-Agent** asset in Exchange (or the AI Gateway Proxy API asset)
2. Click **Request access**
3. Select the existing application: `Salesforce_Integrations_Client_Application_<ORG_ID>`
4. Complete the request access flow
5. Once approved, the application can invoke the Bedrock agent through the governed AI Gateway

---

## Part F: Verification

### F.1 — Test the Bedrock Agent Directly

In the AWS Console:

1. Navigate to **Amazon Bedrock** → **Agents** → **MuleSoft-Returns-Agent**
2. Click **Test** (top-right)
3. In the test panel, type:

```
I want to return order ORD-7890 because the product was defective.
```

4. Verify the agent follows the mandatory tool order:
   - **Step 1**: Calls `Fraud_Scorer` → receives `riskLevel: "SAFE"`, `riskScore: 14`
   - **Step 2**: Calls `Process_Refund` → confirms the return
   - **Step 3**: Responds to the user confirming the refund

5. Test fraud detection:

```
Refund order 999-RAPID-FIRE please, it was wrong item.
```

6. Verify:
   - Calls `Fraud_Scorer` → receives `riskLevel: "CRITICAL"`, `riskScore: 95`
   - DOES NOT call `Process_Refund`
   - Explains the request was flagged

### F.2 — Verify LLM Proxy is Receiving Traffic

1. In Anypoint API Manager → **LLM Proxies** → select **bedrock**
2. Click **Message Log** in the left navigation
3. If you have configured the Message Logging policy (optional), you will see logged messages here
4. Alternatively, check **Logs** for proxy activity

### F.3 — Verify Scanner Keeps Assets in Sync

1. Return to **Exchange** → **Scanners**
2. Confirm your scanner shows status **Scheduled** with the last run successful
3. Note the **Service Capacity Used** counter (e.g., `2 / 10000`)

---

## Checkpoint

Before proceeding to the next exercise, confirm:

| Check | Status |
|-------|--------|
| IAM user has AmazonBedrockFullAccess + bedrock_for_scanner policies | |
| Lambda function Fraud_Scorer_Lambda returns SAFE for normal orders | |
| Lambda function Fraud_Scorer_Lambda returns CRITICAL for 999-prefix orders | |
| Bedrock Agent MuleSoft-Returns-Agent is in PREPARED status | |
| Agent enforces tool order: Fraud_Scorer BEFORE Process_Refund | |
| Agent alias exists and points to latest version (record alias ID from URL) | |
| AI Gateway at `/llmproxy2/chat/completions` returns 200 with valid credentials | |
| AI Gateway returns 401 ("Client ID is not present") without credentials | |
| LLM Token Rate Limit policy applied (order 8) — `x-ratelimit-*` headers visible in response | |
| LLM PII Detection policy applied (order 9) — action: Log and mask | |
| Agent Scanner discovered and published MuleSoft-Returns-Agent to Exchange | |
| Exchange asset shows correct Agent ID, model, and bedrock-agent-runtime URL | |

---

## Key Credentials to Record

| Credential | Where Used |
|-----------|-----------|
| AWS Access Key ID | AI Gateway (Upstream route), Agent Scanner, ai-orchestrator |
| AWS Secret Access Key | AI Gateway (Upstream route), Agent Scanner, ai-orchestrator |
| Bedrock Agent ID | ai-orchestrator property: `bedrock.agentId` |
| Bedrock Agent Alias ID | ai-orchestrator property: `bedrock.agentAliasId` (from Exchange URL) |
| AI Gateway host | `ai-gateway.host` property for slack-agent-router and ai-orchestrator |
| AI Gateway base path | `ai-gateway.basePath` = `/llmproxy2` |
| Exchange App Client ID | `ai-gateway.clientId` — passed as `client_id` header |
| Exchange App Client Secret | `ai-gateway.clientSecret` — passed as `client_secret` header |
| AWS Region (us-east-2) | All AWS connections |

> **Tip**: The Bedrock Agent Alias ID is embedded in the Exchange asset's URL field:
> `https://bedrock-agent-runtime.us-east-2.amazonaws.com/agents/<AGENT_ID>/agentAliases/<ALIAS_ID>/sessions/`

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Access denied" when creating agent | Model not enabled | Bedrock → Model access → Enable Claude Sonnet |
| Lambda timeout during agent test | Function not deployed | Lambda → Deploy → wait for "Changes deployed" |
| Scanner "Connection failed" | Wrong credentials or region | Verify Access Key, Secret Key, and region match |
| Agent calls Process_Refund without Fraud_Scorer | Instructions not saved | Re-paste instructions, click Save, then Prepare |
| LLM Proxy returns 403 | Credentials not valid | Verify AWS keys in Outbound tab are correct |
| Scanner imports 0 agents | Agent not PREPARED | Agent must be in PREPARED status to be discoverable |
| "Resource-based policy" error on Lambda | Permissions not set | Re-add the action group — Bedrock auto-adds the Lambda invoke policy |

---

## Architecture Decisions

| Decision | Why |
|----------|-----|
| Lambda for fraud scoring (not direct model call) | Deterministic logic; doesn't require LLM reasoning for rule-based checks |
| Agent enforces tool ordering via instructions | The model respects natural-language constraints — no code needed for sequencing |
| AI Gateway for foundation model access | Governance: SigV4 signing centralized, Client-ID-Enforcement, logging, rate limiting — apps never hold AWS keys |
| AWS SDK for agent invocation (not via gateway) | Bedrock InvokeAgent uses a streaming protocol with Action Groups that the LLM Proxy's OpenAI-compatible parser cannot forward. The SDK handles the full agent conversation loop |
| Two Bedrock paths (model + agent) | Each serves a different purpose: Haiku (fast, cheap) extracts fields; Sonnet Agent (powerful, instrumented) makes fraud decisions with tool calling |
| Agent Scanner for governance (not invocation) | Scanner answers "what agents exist?" — continuous sync keeps metadata accurate. Bedrock agents are `protocol: "other"` (not A2A), so scanner catalogs them without claiming protocol interop |
| Separate scanner policy (not AmazonBedrockFullAccess alone) | Least privilege — production scanners should have read-only discovery permissions |
| Model-based routing strategy | Routes to specific model versions; prevents unintended model drift |
| Client-ID-Enforcement on gateway | Only authorized Exchange applications (with approved credentials) can call the AI Gateway — prevents credential sprawl |
| LLM Token Rate Limit (100k tokens/min per client) | Prevents quota exhaustion from a runaway agent loop or misconfigured app; keyed per client ID so apps don't starve each other |
| LLM PII Detection (Log and mask) | Defence-in-depth: masks Email, Credit Card, Phone Number in prompts before they reach Bedrock — on top of `sanitize.dwl` in ai-orchestrator. Same governance framework as REST API policies, zero app code changes |
