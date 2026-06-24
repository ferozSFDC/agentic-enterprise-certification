> **Missed Exercise 1? Catch up first:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 2
> ```
> Runs CP1 (Salesforce setup) and CP2 (Slack app manifest — one manual browser step).
> Then continue at [Part A](#part-a) below.

## Exercise 2: Create and Configure the Slack Workspace and App

**Timing**: ~75 minutes  
**Purpose**: Set up the Slack workspace and Slack app, then build the `slack-agent-router` MuleSoft application that receives Slack events, extracts structured data using the AI Gateway, opens a confirmation modal, and calls the `ai-orchestrator`. By the end of this exercise the Experience Layer is complete.

---

### Prerequisites

| Item | Value |
|------|-------|
| Personal (non-work) email | Needed to create the workspace (corporate email restrictions prevent direct creation) |
| Work email (Salesforce) | Will become the primary owner after transfer |
| MuleSoft app URL | The deployed `slack-agent-router` base URL (e.g., `https://slack-agent-router-xxxxx.region.cloudhub.io`) |

---

### Part A: Create the Slack Workspace (~10 min)

#### Step 1: Create a Free Workspace

> **Why personal email first?** Enterprise Slack orgs restrict workspace creation from corporate emails. You must create with a personal email, then transfer ownership to your work account.

1. Open an incognito/private browser window
2. Go to https://slack.com/get-started#/createnew
3. Sign in with your **personal (non-work) email address**
4. Click **Create a Workspace**
5. Workspace name: `Agentic Enterprise Training` (or similar)
6. Complete the onboarding wizard (skip inviting others for now)
7. Note your workspace URL (e.g., `agentic-enterprise-training.slack.com`)

#### Step 2: Add Your Work Email and Transfer Ownership

8. In the workspace, go to **Settings & administration** → **Manage members**
9. Click **Invite people** → enter your **work email** (e.g., `yourname@salesforce.com`)
10. Accept the invitation from your work email and join the workspace
11. From your personal account: **Settings & administration** → **Workspace settings** → **Transfer ownership**
12. Transfer primary ownership to your work email address

#### Step 3: Upgrade the Workspace (Salesforce Employees Only)

> **Skip this step** if you're not a Salesforce employee. The free tier is sufficient for basic testing, but some features (custom app distribution, higher rate limits) require a paid plan.

13. In Slack, navigate to the **#slack-ce-trial-and-sandbox-requests** channel (in the Salesforce corporate Slack)
14. Complete the workflow to request an upgrade for your new workspace
15. Set expiration to **360 days**
16. Wait for approval (typically same day)

---

### Part B: Create the Slack App (~15 min)

#### Step 4: Create a New App

1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Select **From scratch** (not from a manifest)
4. App Name: `Agent Fabric`
5. Pick workspace: select the workspace you just created
6. Click **Create App**

#### Step 5: Configure Bot Token Scopes

The bot needs permissions to read messages, post responses, and open modals.

7. In the left sidebar, click **OAuth & Permissions**
8. Scroll down to **Scopes** → **Bot Token Scopes**
9. Click **Add an OAuth Scope** and add ALL of the following:

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Detect when users @mention the bot |
| `chat:write` | Post messages and responses to channels |
| `commands` | Handle slash commands (e.g., `/refund`) |
| `im:history` | Read DM history for context |
| `im:read` | Access DM channel info |
| `im:write` | Send DMs to users |
| `users:read` | Look up user profiles (email for OBO identity) |
| `users:read.email` | Access user email addresses (critical for Data Cloud lookup) |

#### Step 6: Install the App to Your Workspace

10. Scroll back up to **OAuth Tokens for Your Workspace**
11. Click **Install to Workspace**
12. Review the permissions and click **Allow**
13. Copy the **Bot User OAuth Token** (starts with `xoxb-`) — this is your `slack.botToken`
14. **Store it securely** — this goes into the MuleSoft app's configuration

#### Step 7: Configure Event Subscriptions

This tells Slack where to send events when users interact with the bot.

15. In the left sidebar, click **Event Subscriptions**
16. Toggle **Enable Events** to **On**
17. For **Request URL**, enter: `https://<YOUR-MULESOFT-APP-URL>/slack/events`
    - Example: `https://slack-agent-router-835dgu.wdob74.usa-e2.cloudhub.io/slack/events`
    - Slack will send a verification challenge — the MuleSoft app must be running to respond
18. Under **Subscribe to bot events**, click **Add Bot User Event** and add:

| Event | Purpose |
|-------|---------|
| `app_mention` | Fires when someone @mentions the bot in a channel |
| `message.im` | Fires when someone sends a DM to the bot |

19. Click **Save Changes**

> **Important**: The Request URL verification will FAIL if the MuleSoft `slack-agent-router` app is not deployed and running. You may need to come back to this step after deploying the MuleSoft apps. The app responds to the challenge at `POST /slack/events` by echoing back the `challenge` field.

#### Step 8: Configure Interactivity & Shortcuts

This handles modal submissions and button clicks.

20. In the left sidebar, click **Interactivity & Shortcuts**
21. Toggle **Interactivity** to **On**
22. For **Request URL**, enter: `https://<YOUR-MULESOFT-APP-URL>/slack/interactivity`
23. Click **Save Changes**

#### Step 9: Configure Slash Commands

24. In the left sidebar, click **Slash Commands**
25. Click **Create New Command**
26. Configure:
    - Command: `/refund`
    - Request URL: `https://<YOUR-MULESOFT-APP-URL>/slack/commands`
    - Short Description: `Request a customer refund`
    - Usage Hint: `[describe the refund request]`
27. Click **Save**

#### Step 10: Enable App Home (Optional)

28. In the left sidebar, click **App Home**
29. Under **Show Tabs**, ensure **Messages Tab** is enabled
30. Check **Allow users to send Slash commands and messages from the messages tab**

This lets users DM the bot directly instead of only @mentioning it in channels.

---

### Part C: Record the Credentials (~5 min)

#### Step 11: Gather All Required Values

Navigate to **Basic Information** in the left sidebar and record:

| Credential | Where to Find | MuleSoft Property |
|------------|---------------|-------------------|
| Bot Token | OAuth & Permissions → Bot User OAuth Token (`xoxb-...`) | `slack.botToken` |
| Signing Secret | Basic Information → App Credentials → Signing Secret | _(used if implementing request verification)_ |
| App ID | Basic Information → App ID | _(reference only)_ |

> **The only credential the MuleSoft app currently requires is the Bot Token** (`slack.botToken`). The Signing Secret would be used for request signature verification (a security best practice for production but not currently implemented in the app).

---

### Part D: Build the slack-agent-router MuleSoft App (~45 min)

This is where the Slack configuration comes alive. You build the MuleSoft application that receives Slack events, extracts structured data using the AI Gateway, opens a confirmation modal, and calls `ai-orchestrator`.

The app has five source files. Create each one exactly as shown.

#### Step 12: Create the Mule Project

1. In Anypoint Studio, select **File > New > Mule Project**
2. Set:
   - Project name: `slack-agent-router`
   - Mule runtime: `4.11.3`
   - Maven: enabled
3. Click **Finish**

#### Step 13: Edit pom.xml

Replace `<dependencies>` with:

```xml
<dependencies>
    <dependency>
        <groupId>org.mule.connectors</groupId>
        <artifactId>mule-http-connector</artifactId>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>org.mule.connectors</groupId>
        <artifactId>mule-objectstore-connector</artifactId>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>com.mulesoft.modules</groupId>
        <artifactId>mule-secure-configuration-property-module</artifactId>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>org.mule.modules</groupId>
        <artifactId>mule-tracing-module</artifactId>
        <classifier>mule-plugin</classifier>
    </dependency>
</dependencies>
```

Add inside `<properties>`:
```xml
<app.name>slack-agent-router</app.name>
```

> The versions are inherited from the parent pom you created in Exercise 5. If you haven't done Exercise 5 yet, add explicit versions: `mule-http-connector 1.9.3`, `mule-objectstore-connector 1.2.3`, `mule-secure-configuration-property-module 1.2.7`, `mule-tracing-module 1.2.0`.

#### Step 14: Create config.yaml

Create `src/main/resources/config.yaml`:

```yaml
contract.version: "1.2"
otel.logs.enabled: "false"
circuit.failureThreshold: "3"
circuit.cooldownMs: "60000"
readiness.timeoutMs: "2000"
api.id: "0"
anypoint.platform.client_id: "${anypoint.platform.client_id}"
anypoint.platform.client_secret: "${anypoint.platform.client_secret}"
slack:
  botToken: "${slack.botToken}"

orchestrator:
  host: "localhost"
  responseTimeoutMs: "120000"

ai-gateway:
  host: "localhost"
  basePath: "/llmproxy2"
  clientId: "local-dev"
  clientSecret: "local-dev"
  modelId: "us.anthropic.claude-3-haiku-20240307-v1:0"

agent:
  ingressHost: "localhost"

otel:
  logs:
    authHeader: "${otel.logs.authHeader}"
    serviceName: "slack-agent-router"
    environment: "sandbox"
```

Create `src/main/resources/dev-config.yaml` (fill in your CloudHub hostnames after deploy):

```yaml
orchestrator:
  host: "{your-ai-orchestrator-host}"
readiness:
  orchestrator:
    protocol: "HTTPS"
    host: "{your-ai-orchestrator-host}"
    port: "443"
ai-gateway:
  host: "{your-gateway-host}"
agent:
  ingressHost: "{your-slack-agent-router-host}"
```

#### Step 15: Create global-config.xml

Create `src/main/mule/global-config.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <!-- Port 8081 — the only app that binds to 8081 locally -->
    <http:listener-config name="httpListenerConfig">
        <http:listener-connection host="0.0.0.0" port="8081" protocol="HTTP" />
    </http:listener-config>

    <!-- Readiness: probes ai-orchestrator health (port 8082 locally) -->
    <http:request-config name="readinessOrchestratorRequestConfig">
        <http:request-connection protocol="${readiness.orchestrator.protocol}"
                                 host="${readiness.orchestrator.host}"
                                 port="${readiness.orchestrator.port}">
            <reconnection><reconnect count="1" frequency="250" /></reconnection>
        </http:request-connection>
    </http:request-config>

    <global-property name="env" value="dev" />
    <configuration-properties file="config.yaml" />
    <configuration-properties file="${env}-config.yaml" />

    <os:object-store name="CircuitBreakerStore" persistent="true"
                     maxEntries="1000" entryTtl="24" entryTtlUnit="HOURS" />
    <os:object-store name="SlackEventDedupeStore" persistent="true"
                     maxEntries="5000" entryTtl="30" entryTtlUnit="MINUTES" />

    <secure-properties:config name="securePropertiesConfig"
                              file="secure-properties.yaml"
                              key="#[p('secure.key') default 'local-dev-secure-key-override']" />

    <!-- Slack API — all calls use the Bot Token in Authorization header -->
    <http:request-config name="slackApiRequestConfig" basePath="/api">
        <http:request-connection protocol="HTTPS" host="slack.com" port="443">
            <reconnection><reconnect count="3" frequency="2000" /></reconnection>
        </http:request-connection>
        <http:default-headers>
            <http:default-header key="Authorization"
                value="#['Bearer ' ++ ((p('slack.botToken') default p('secure::slack.botToken')) as String)]" />
            <http:default-header key="Content-Type" value="application/json" />
        </http:default-headers>
    </http:request-config>

    <!-- ai-orchestrator — OBO headers set here, applied to every call -->
    <http:request-config name="orchestratorRequestConfig" basePath="/api">
        <http:request-connection protocol="HTTPS" host="${orchestrator.host}" port="443">
            <reconnection><reconnect count="3" frequency="2000" /></reconnection>
        </http:request-connection>
        <http:default-headers>
            <http:default-header key="Content-Type" value="application/json" />
            <http:default-header key="x-user-id" value='#[vars.slackUserId default "unknown"]' />
            <http:default-header key="x-request-id" value='#[vars.requestId default "unknown"]' />
            <http:default-header key="x-flow-id" value='#[vars.flowId default vars.requestId default "unknown"]' />
            <http:default-header key="x-session-id" value='#[vars.sessionId default vars.flowId default "unknown"]' />
            <http:default-header key="x-source-app" value="slack-agent-router" />
            <http:default-header key="x-source-type" value='#[vars.sourceType default "unknown"]' />
            <http:default-header key="x-contract-version" value='#[p("contract.version") default "1.2"]' />
        </http:default-headers>
    </http:request-config>

    <!-- AI Gateway — Client-ID-Enforcement headers + OBO correlation -->
    <http:request-config name="aiGatewayRequestConfig" basePath="${ai-gateway.basePath}">
        <http:request-connection protocol="HTTPS" host="${ai-gateway.host}" port="443">
            <reconnection><reconnect count="3" frequency="2000" /></reconnection>
        </http:request-connection>
        <http:default-headers>
            <http:default-header key="Content-Type" value="application/json" />
            <http:default-header key="client_id"
                value="#[(p('ai-gateway.clientId') default p('secure::ai-gateway.clientId')) as String]" />
            <http:default-header key="client_secret"
                value="#[(p('ai-gateway.clientSecret') default p('secure::ai-gateway.clientSecret')) as String]" />
            <http:default-header key="x-user-id" value='#[vars.slackUserId default "unknown"]' />
            <http:default-header key="x-request-id" value='#[vars.requestId default "unknown"]' />
            <http:default-header key="x-flow-id" value='#[vars.flowId default vars.requestId default "unknown"]' />
            <http:default-header key="x-session-id" value='#[vars.sessionId default vars.flowId default "unknown"]' />
            <http:default-header key="x-source-app" value="slack-agent-router" />
        </http:default-headers>
    </http:request-config>

    <configuration defaultErrorHandler-ref="globalDefaultErrorHandler" />
</mule>
```

> **Why two Object Stores?** `CircuitBreakerStore` tracks failure counts for the AI Gateway and orchestrator (24-hour TTL — circuit state outlives a single request). `SlackEventDedupeStore` records seen event IDs to suppress Slack retries (30-minute TTL — matches Slack's retry window).

#### Step 16: Create health-flows.xml

Create `src/main/mule/health-flows.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <flow name="health-liveness-flow">
        <http:listener config-ref="httpListenerConfig" path="/health">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
        </http:listener>
        <set-payload value='#[output application/json --- {status: "ok", probe: "liveness", service: "slack-agent-router"}]' />
    </flow>

    <flow name="health-readiness-flow">
        <http:listener config-ref="httpListenerConfig" path="/health/ready">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 500]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>
        <set-variable variableName="httpStatus" value="#[200]" />
        <set-variable variableName="readyStatus" value="#['UP']" />
        <set-variable variableName="readyError" value="#[null]" />
        <try>
            <http:request method="GET" config-ref="readinessOrchestratorRequestConfig"
                          path="/health" responseTimeout="${readiness.timeoutMs}" />
            <error-handler>
                <on-error-continue type="ANY" logException="false">
                    <set-variable variableName="readyStatus" value="#['DOWN']" />
                    <set-variable variableName="readyError"
                        value="#[error.description default error.errorType.identifier default 'unreachable']" />
                </on-error-continue>
            </error-handler>
        </try>
        <choice>
            <when expression="#[vars.readyStatus != 'UP']">
                <set-variable variableName="httpStatus" value="#[503]" />
            </when>
        </choice>
        <ee:transform>
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  status: if ((vars.httpStatus default 200) == 200) "ready" else "not_ready",
  probe: "readiness",
  service: "slack-agent-router",
  dependencies: [{
    name: "ai-orchestrator",
    status: vars.readyStatus default "DOWN",
    error: if ((vars.readyError default null) != null) vars.readyError else null
  }]
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>
    </flow>
</mule>
```

#### Step 17: Create slack-events-flow.xml

This file handles the main Slack webhook — URL verification challenges, deduplication, and @mention processing.

Create `src/main/mule/slack-events-flow.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <flow name="slack-events-webhook-flow">
        <http:listener config-ref="httpListenerConfig" path="/slack/events">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 500]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>

        <!-- Capture Slack's retry header — if present, this is a duplicate delivery -->
        <set-variable variableName="slackRetryNum"
            value="#[attributes.headers.'x-slack-retry-num' default null]" />

        <!-- Build stable correlation IDs from Slack event envelope -->
        <set-variable variableName="requestId"
            value="#[payload.event_id default ((payload.event.ts default now() as String) ++ '-' ++ (payload.event.user default 'unknown'))]" />
        <set-variable variableName="flowId" value="#[vars.requestId]" />
        <set-variable variableName="sessionId"
            value="#[payload.event.thread_ts default payload.event.ts default vars.requestId]" />
        <set-variable variableName="sourceType"
            value="#[if (payload.'type' == 'url_verification') 'url_verification'
                      else if (payload.event.'type' == 'app_mention') 'app_mention'
                      else 'unknown']" />

        <!-- Persistent dedup: store event_id in Object Store for 30 min -->
        <flow-ref name="slack-dedupe-check-and-store-subflow" />

        <choice doc:name="Event Type Router">
            <!-- Slack retries: return 200 immediately, do nothing -->
            <when expression="#[(vars.slackRetryNum default null) != null]">
                <ee:transform>
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{status: "received", dedupe: "duplicate_ignored", flowId: vars.flowId}]]></ee:set-payload>
                    </ee:message>
                </ee:transform>
            </when>

            <!-- Persistent duplicate from Object Store -->
            <when expression="#[(vars.isDuplicateRequest default false)]">
                <ee:transform>
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{status: "received", dedupe: "persistent_duplicate_ignored", flowId: vars.flowId}]]></ee:set-payload>
                    </ee:message>
                </ee:transform>
            </when>

            <!-- URL verification challenge — must respond within 3s or Slack disables the endpoint -->
            <when expression="#[payload.'type' == 'url_verification']">
                <ee:transform>
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{challenge: payload.challenge}]]></ee:set-payload>
                    </ee:message>
                </ee:transform>
            </when>

            <!-- @mention — extract fields via AI Gateway, show confirmation prompt -->
            <when expression="#[payload.event.'type' == 'app_mention']">
                <flow-ref name="normalize-app-mention-subflow" />
                <!-- Return 200 immediately — process async to avoid Slack's 3s timeout -->
                <async>
                    <flow-ref name="extract-fields-with-ai-gateway-subflow" />
                    <ee:transform doc:name="Build Confirmation Prompt">
                        <ee:message>
                            <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  channel: vars.slackChannel,
  thread_ts: vars.slackThreadTs,
  text: "Please confirm the extracted details before I continue.",
  blocks: [
    {
      "type": "section",
      text: {"type": "mrkdwn", text: "*Confirm details before processing refund*"}
    },
    {
      "type": "section",
      fields: [
        {"type": "mrkdwn", text: "*Order:* " ++ (vars.orderNumber default "Not detected")},
        {"type": "mrkdwn", text: "*Reason:* " ++ (vars.reason default "Not detected")}
      ]
    },
    {
      "type": "actions",
      elements: [{
        "type": "button",
        text: {"type": "plain_text", text: "Review and Confirm"},
        style: "primary",
        action_id: "open_refund_confirm_modal",
        value: write({
          requestId: vars.requestId, flowId: vars.flowId, sessionId: vars.sessionId,
          sourceType: vars.sourceType, slackThreadTs: vars.slackThreadTs,
          slackUserId: vars.slackUserId, channel: vars.slackChannel,
          timestamp: vars.timestamp, rawText: vars.rawText, inputText: vars.inputText,
          orderNumber: vars.orderNumber, reason: vars.reason,
          ambiguityDetected: vars.ambiguityDetected default false
        }, "application/json")
      }]
    }
  ]
}]]></ee:set-payload>
                        </ee:message>
                    </ee:transform>
                    <http:request method="POST" config-ref="slackApiRequestConfig" path="/chat.postMessage" />
                </async>
                <ee:transform>
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{status: "received"}]]></ee:set-payload>
                    </ee:message>
                </ee:transform>
            </when>

            <otherwise>
                <ee:transform>
                    <ee:message>
                        <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{status: "ignored", flowId: vars.flowId, sourceType: vars.sourceType}]]></ee:set-payload>
                    </ee:message>
                </ee:transform>
            </otherwise>
        </choice>
    </flow>
</mule>
```

#### Step 18: Create slack-interactions-flow.xml

This handles button clicks (opens modal) and modal submissions (confirms the request).

Create `src/main/mule/slack-interactions-flow.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <!-- /slack/commands — slash command handler -->
    <flow name="slack-commands-flow">
        <http:listener config-ref="httpListenerConfig" path="/slack/commands">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": if ((vars.httpStatus default 200) >= 400) "application/json" else "text/plain"}]</http:headers>
            </http:response>
        </http:listener>
        <set-variable variableName="slackRetryNum"
            value="#[attributes.headers.'x-slack-retry-num' default null]" />
        <!-- Slash commands arrive as application/x-www-form-urlencoded -->
        <set-variable variableName="formPayloadParseAttempt"
            value="#[output application/java import try from dw::Runtime ---
                if (payload is Object) {success: true, result: payload}
                else try(() -> read((payload default '') as String, 'application/x-www-form-urlencoded'))]" />
        <set-variable variableName="formPayload"
            value="#[output application/java ---
                if ((vars.formPayloadParseAttempt.success default false) as Boolean)
                    vars.formPayloadParseAttempt.result else {}]" />
        <choice>
            <when expression="#[(vars.slackRetryNum default null) != null]">
                <set-payload value="status=received&amp;dedupe=duplicate_ignored" />
            </when>
            <otherwise>
                <set-variable variableName="requestId"
                    value="#[vars.formPayload.trigger_id default ((vars.formPayload.user_id default 'unknown') ++ '-' ++ (now() as String))]" />
                <set-variable variableName="flowId" value="#[vars.requestId]" />
                <set-variable variableName="sessionId" value="#[vars.requestId]" />
                <set-variable variableName="sourceType" value="#['slash_command']" />
                <set-variable variableName="slackUserId" value="#[vars.formPayload.user_id]" />
                <set-variable variableName="slackChannel" value="#[vars.formPayload.channel_id]" />
                <set-variable variableName="slackThreadTs" value="#[null]" />
                <set-variable variableName="timestamp" value="#[now() as String]" />
                <set-variable variableName="rawText" value="#[vars.formPayload.text default '']" />
                <set-variable variableName="inputText" value="#[vars.rawText]" />
                <flow-ref name="extract-fields-with-ai-gateway-subflow" />
                <set-variable variableName="triggerId" value="#[vars.formPayload.trigger_id]" />
                <flow-ref name="open-confirmation-modal-subflow" />
                <set-payload value="status=received" />
            </otherwise>
        </choice>
    </flow>

    <!-- /slack/interactivity — button clicks and modal submissions -->
    <flow name="slack-interactivity-flow">
        <http:listener config-ref="httpListenerConfig" path="/slack/interactivity">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 500]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>
        <set-variable variableName="formPayloadParseAttempt"
            value="#[output application/java import try from dw::Runtime ---
                if (payload is Object) {success: true, result: payload}
                else try(() -> read((payload default '') as String, 'application/x-www-form-urlencoded'))]" />
        <set-variable variableName="formPayload"
            value="#[output application/java ---
                if ((vars.formPayloadParseAttempt.success default false) as Boolean)
                    vars.formPayloadParseAttempt.result else {}]" />
        <set-variable variableName="interactionPayloadParseAttempt"
            value="#[output application/java import try from dw::Runtime ---
                if ((vars.formPayload.payload default null) is Object) {success: true, result: vars.formPayload.payload}
                else try(() -> read((vars.formPayload.payload default '{}') as String, 'application/json'))]" />
        <set-variable variableName="interactionPayload"
            value="#[output application/java ---
                if ((vars.interactionPayloadParseAttempt.success default false) as Boolean)
                    vars.interactionPayloadParseAttempt.result else {}]" />

        <choice doc:name="Interaction Router">
            <!-- Button click: open the confirmation modal -->
            <when expression="#[vars.interactionPayload.'type' == 'block_actions' and vars.interactionPayload.actions[0].action_id == 'open_refund_confirm_modal']">
                <set-variable variableName="metaParseAttempt"
                    value="#[output application/java import try from dw::Runtime ---
                        try(() -> read((vars.interactionPayload.actions[0].value default '{}') as String, 'application/json'))]" />
                <set-variable variableName="meta"
                    value="#[output application/java ---
                        if ((vars.metaParseAttempt.success default false) as Boolean) vars.metaParseAttempt.result else {}]" />
                <set-variable variableName="requestId" value="#[vars.meta.requestId]" />
                <set-variable variableName="flowId" value="#[vars.meta.flowId]" />
                <set-variable variableName="sessionId" value="#[vars.meta.sessionId]" />
                <set-variable variableName="sourceType" value="#[vars.meta.sourceType]" />
                <set-variable variableName="slackUserId" value="#[vars.meta.slackUserId]" />
                <set-variable variableName="slackChannel" value="#[vars.meta.channel]" />
                <set-variable variableName="slackThreadTs" value="#[vars.meta.slackThreadTs default null]" />
                <set-variable variableName="timestamp" value="#[vars.meta.timestamp]" />
                <set-variable variableName="rawText" value="#[vars.meta.rawText]" />
                <set-variable variableName="inputText" value="#[vars.meta.inputText]" />
                <set-variable variableName="orderNumber" value="#[vars.meta.orderNumber]" />
                <set-variable variableName="reason" value="#[vars.meta.reason]" />
                <set-variable variableName="triggerId" value="#[vars.interactionPayload.trigger_id]" />
                <flow-ref name="open-confirmation-modal-subflow" />
                <set-payload value='#[output application/json --- {status: "received"}]' />
            </when>

            <!-- Modal submission: validate, then process async -->
            <when expression="#[vars.interactionPayload.'type' == 'view_submission' and vars.interactionPayload.view.callback_id == 'refund_confirm_v1']">
                <set-variable variableName="metaParseAttempt"
                    value="#[output application/java import try from dw::Runtime ---
                        try(() -> read((vars.interactionPayload.view.private_metadata default '{}') as String, 'application/json'))]" />
                <set-variable variableName="meta"
                    value="#[output application/java ---
                        if ((vars.metaParseAttempt.success default false) as Boolean) vars.metaParseAttempt.result else {}]" />
                <set-variable variableName="requestId"
                    value="#[vars.meta.requestId default vars.interactionPayload.trigger_id]" />
                <set-variable variableName="flowId"
                    value="#[vars.meta.flowId default vars.requestId]" />
                <set-variable variableName="sessionId"
                    value="#[vars.meta.sessionId default vars.flowId]" />
                <set-variable variableName="sourceType"
                    value="#[vars.meta.sourceType default 'modal_submission']" />
                <set-variable variableName="slackUserId"
                    value="#[vars.meta.slackUserId default vars.interactionPayload.user.id]" />
                <set-variable variableName="slackChannel" value="#[vars.meta.channel]" />
                <set-variable variableName="slackThreadTs"
                    value="#[vars.meta.slackThreadTs default null]" />
                <set-variable variableName="timestamp"
                    value="#[vars.meta.timestamp default now() as String]" />
                <set-variable variableName="rawText"
                    value="#[vars.meta.rawText default '']" />
                <set-variable variableName="inputText"
                    value="#[vars.meta.inputText default vars.rawText]" />
                <!-- Modal fields override whatever AI extracted -->
                <set-variable variableName="orderNumber"
                    value="#[vars.interactionPayload.view.state.values.order_block.order_value.value default vars.meta.orderNumber default null]" />
                <set-variable variableName="reason"
                    value="#[vars.interactionPayload.view.state.values.reason_block.reason_value.value default vars.meta.reason default null]" />
                <!-- Validation: both fields required before calling orchestrator -->
                <set-variable variableName="validationError"
                    value="#[if ((vars.orderNumber default '') == '') 'Order number is required'
                               else if ((vars.reason default '') == '') 'Reason is required'
                               else null]" />
                <choice>
                    <when expression="#[(vars.validationError default null) != null]">
                        <ee:transform>
                            <ee:message>
                                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  response_action: "errors",
  errors: {
    order_block: if ((vars.orderNumber default '') == '') "Order number is required" else null,
    reason_block: if ((vars.reason default '') == '') "Reason is required" else null
  }
}]]></ee:set-payload>
                            </ee:message>
                        </ee:transform>
                    </when>
                    <otherwise>
                        <!-- Close the modal immediately; update via chat.update asynchronously -->
                        <async>
                            <flow-ref name="process-confirmed-request-subflow" />
                        </async>
                        <ee:transform>
                            <ee:message>
                                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{response_action: "clear"}]]></ee:set-payload>
                            </ee:message>
                        </ee:transform>
                    </otherwise>
                </choice>
            </when>

            <otherwise>
                <set-payload value='#[output application/json --- {status: "ignored"}]' />
            </otherwise>
        </choice>
    </flow>
</mule>
```

> **Timing constraint**: Slack requires a response to `view_submission` within 3 seconds or it shows the user an error. The `<async>` block closes the modal instantly with `{response_action: "clear"}` while the full orchestration pipeline (up to 30 seconds) runs in the background and updates the Slack thread via `chat.update`.

#### Step 19: Create slack-context-subflows.xml

This file contains three sub-flows: app mention normalization, AI Gateway field extraction, and the confirmation modal builder.

Create `src/main/mule/slack-context-subflows.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <!-- Normalizes the @mention event into standard routing variables -->
    <sub-flow name="normalize-app-mention-subflow">
        <set-variable variableName="slackChannel" value="#[payload.event.channel]" />
        <set-variable variableName="slackThreadTs"
            value="#[payload.event.thread_ts default payload.event.ts]" />
        <set-variable variableName="rawText" value="#[payload.event.text default '']" />
        <!-- Strip the bot mention prefix so AI extraction sees clean text -->
        <set-variable variableName="inputText"
            value="#[(vars.rawText default '') replace /&lt;@[^&gt;]+&gt;\s*/ with '']" />
        <set-variable variableName="slackUserId" value="#[payload.event.user]" />
        <set-variable variableName="timestamp"
            value="#[payload.event.ts default now() as String]" />
    </sub-flow>

    <!--
        Calls AI Gateway (Claude Haiku via Omni Gateway) to extract orderNumber and reason
        from free-form text.  Falls back to null for both fields on any error.
        Circuit breaker key: 'ai-gateway' — shared with orchestrator's gateway calls.
    -->
    <sub-flow name="extract-fields-with-ai-gateway-subflow">
        <set-variable variableName="orderNumber" value="#[null]" />
        <set-variable variableName="reason" value="#[null]" />
        <!-- Regex pre-scan to detect ambiguous order numbers before AI call -->
        <set-variable variableName="orderCandidates"
            value='#[output application/java ---
                (((vars.inputText default "") scan /(ORD-[A-Za-z0-9-]+|[0-9]{3}-[0-9]{3}|[0-9]{3}-[0-9]{2,4}-[0-9])/)
                    map (($[1] default "") as String) filter ($ != "") distinctBy $)]' />
        <set-variable variableName="ambiguityDetected"
            value="#[sizeOf(vars.orderCandidates default []) > 1]" />
        <try>
            <set-variable variableName="circuitKey" value="#['ai-gateway']" />
            <flow-ref name="circuit-breaker-before-call-subflow" />
            <ee:transform doc:name="Build Extraction Prompt">
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  model: "${ai-gateway.modelId}",
  messages: [
    {
      role: "system",
      content: "Extract refund fields as JSON: {\"orderNumber\": string|null, \"reason\": string|null}. Return JSON only."
    },
    {role: "user", content: vars.inputText}
  ],
  max_tokens: 200
}]]></ee:set-payload>
                </ee:message>
            </ee:transform>
            <http:request method="POST" config-ref="aiGatewayRequestConfig" path="/chat/completions" />
            <flow-ref name="circuit-breaker-mark-success-subflow" />
            <set-variable variableName="aiExtractRaw"
                value="#[payload.choices[0].message.content default '']" />
            <set-variable variableName="aiExtractParseAttempt"
                value="#[output application/java import try from dw::Runtime ---
                    try(() -> read((vars.aiExtractRaw default '{}') as String, 'application/json'))]" />
            <set-variable variableName="aiExtractParsed"
                value="#[output application/java ---
                    if ((vars.aiExtractParseAttempt.success default false) as Boolean)
                        vars.aiExtractParseAttempt.result else {}]" />
            <set-variable variableName="orderNumber"
                value="#[output application/java --- vars.aiExtractParsed.orderNumber default null]" />
            <set-variable variableName="reason"
                value="#[output application/java --- vars.aiExtractParsed.reason default null]" />
            <!-- Ambiguity gate: if multiple order patterns detected, force user to type manually -->
            <choice>
                <when expression="#[(vars.ambiguityDetected default false)]">
                    <set-variable variableName="orderNumber" value="#[null]" />
                </when>
            </choice>
            <error-handler>
                <on-error-propagate type="MULE:CONNECTIVITY" logException="false">
                    <flow-ref name="circuit-breaker-mark-failure-subflow" />
                </on-error-propagate>
                <on-error-continue type="ANY" logException="true">
                    <flow-ref name="circuit-breaker-mark-failure-subflow" />
                    <set-variable variableName="orderNumber" value="#[null]" />
                    <set-variable variableName="reason" value="#[null]" />
                </on-error-continue>
            </error-handler>
        </try>
    </sub-flow>

    <!-- Opens a Slack modal with pre-filled order/reason from AI extraction -->
    <sub-flow name="open-confirmation-modal-subflow">
        <ee:transform doc:name="Build views.open payload">
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  trigger_id: vars.triggerId,
  view: {
    "type": "modal",
    callback_id: "refund_confirm_v1",
    title: {"type": "plain_text", text: "Confirm Refund"},
    submit: {"type": "plain_text", text: "Confirm"},
    close: {"type": "plain_text", text: "Cancel"},
    private_metadata: write({
      requestId: vars.requestId, flowId: vars.flowId, sessionId: vars.sessionId,
      sourceType: vars.sourceType, slackThreadTs: vars.slackThreadTs,
      slackUserId: vars.slackUserId, channel: vars.slackChannel,
      timestamp: vars.timestamp, rawText: vars.rawText, inputText: vars.inputText,
      ambiguityDetected: vars.ambiguityDetected default false
    }, "application/json"),
    blocks: [
      {
        "type": "input",
        block_id: "order_block",
        label: {"type": "plain_text", text: "Order Number"},
        element: {
          "type": "plain_text_input",
          action_id: "order_value",
          initial_value: vars.orderNumber default ""
        }
      },
      {
        "type": "input",
        block_id: "reason_block",
        label: {"type": "plain_text", text: "Reason"},
        element: {
          "type": "plain_text_input",
          action_id: "reason_value",
          multiline: true,
          initial_value: vars.reason default ""
        }
      }
    ]
  }
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>
        <http:request method="POST" config-ref="slackApiRequestConfig" path="/views.open" />
    </sub-flow>
</mule>
```

> **Why serialize context into `private_metadata`?** Slack modal submissions arrive as new HTTP requests — there's no session state. The entire correlation context (requestId, flowId, sessionId, slackUserId) is serialized as JSON into the modal's `private_metadata` string and recovered on submission. This is how Slack's stateless model forces you to carry state forward.

#### Step 20: Create support-subflows.xml

Circuit breaker and deduplication sub-flows used across all the main flows.

Create `src/main/mule/support-subflows.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
                          http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
                          http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <!--
        CIRCUIT BREAKER — 3-state (CLOSED / OPEN / HALF_OPEN)
        Stored in CircuitBreakerStore keyed by circuitKey (e.g. 'ai-gateway', 'ai-orchestrator').
        Callers must set vars.circuitKey before calling these sub-flows.
    -->
    <sub-flow name="circuit-breaker-before-call-subflow">
        <set-variable variableName="circuitFailureThreshold"
            value="#[(p('circuit.failureThreshold') default 3) as Number]" />
        <set-variable variableName="circuitCooldownMs"
            value="#[(p('circuit.cooldownMs') default 60000) as Number]" />
        <try>
            <os:retrieve key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                         objectStore="CircuitBreakerStore" target="circuitState" />
            <error-handler>
                <on-error-continue type="OS:KEY_NOT_FOUND" logException="false">
                    <set-variable variableName="circuitState"
                        value="#[{status: 'CLOSED', failures: 0, openedAt: 0}]" />
                </on-error-continue>
            </error-handler>
        </try>
        <set-variable variableName="circuitNowMs"
            value="#[now() as Number {unit: 'milliseconds'}]" />
        <choice>
            <when expression="#[upper((vars.circuitState.status default 'CLOSED') as String) == 'OPEN']">
                <set-variable variableName="circuitElapsedMs"
                    value="#[(vars.circuitNowMs default 0) - ((vars.circuitState.openedAt default 0) as Number)]" />
                <choice>
                    <when expression="#[(vars.circuitElapsedMs default 0) &lt; (vars.circuitCooldownMs default 60000)]">
                        <set-variable variableName="retryAfter"
                            value="#[ceil((((vars.circuitCooldownMs default 60000) - (vars.circuitElapsedMs default 0)) as Number) / 1000)]" />
                        <raise-error type="MULE:CONNECTIVITY"
                            description="#['Circuit is open for ' ++ ((vars.circuitKey default 'downstream') as String)]" />
                    </when>
                    <otherwise>
                        <!-- Cooldown elapsed — try once in HALF_OPEN state -->
                        <os:store key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                                  objectStore="CircuitBreakerStore">
                            <os:value><![CDATA[#[{status: "HALF_OPEN", failures: (vars.circuitState.failures default 0), openedAt: (vars.circuitState.openedAt default vars.circuitNowMs)}]]]></os:value>
                        </os:store>
                    </otherwise>
                </choice>
            </when>
        </choice>
    </sub-flow>

    <sub-flow name="circuit-breaker-mark-success-subflow">
        <os:store key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                  objectStore="CircuitBreakerStore">
            <os:value><![CDATA[#[{status: "CLOSED", failures: 0, openedAt: 0, lastSuccessAt: (now() as Number {unit: "milliseconds"})}]]]></os:value>
        </os:store>
        <set-variable variableName="retryAfter" value="#[null]" />
    </sub-flow>

    <sub-flow name="circuit-breaker-mark-failure-subflow">
        <set-variable variableName="circuitFailureThreshold"
            value="#[(p('circuit.failureThreshold') default 3) as Number]" />
        <set-variable variableName="circuitCooldownMs"
            value="#[(p('circuit.cooldownMs') default 60000) as Number]" />
        <try>
            <os:retrieve key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                         objectStore="CircuitBreakerStore" target="circuitState" />
            <error-handler>
                <on-error-continue type="OS:KEY_NOT_FOUND" logException="false">
                    <set-variable variableName="circuitState"
                        value="#[{status: 'CLOSED', failures: 0, openedAt: 0}]" />
                </on-error-continue>
            </error-handler>
        </try>
        <!-- HALF_OPEN failure immediately re-opens -->
        <set-variable variableName="circuitFailureCount"
            value="#[if (upper((vars.circuitState.status default 'CLOSED') as String) == 'HALF_OPEN')
                        (vars.circuitFailureThreshold as Number)
                      else ((vars.circuitState.failures default 0) as Number) + 1]" />
        <choice>
            <when expression="#[(vars.circuitFailureCount default 0) >= (vars.circuitFailureThreshold default 3)]">
                <set-variable variableName="retryAfter"
                    value="#[ceil((vars.circuitCooldownMs as Number) / 1000)]" />
                <os:store key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                          objectStore="CircuitBreakerStore">
                    <os:value><![CDATA[#[{status: "OPEN", failures: vars.circuitFailureCount, openedAt: (now() as Number {unit: "milliseconds"})}]]]></os:value>
                </os:store>
            </when>
            <otherwise>
                <os:store key="#['circuit:' ++ ((vars.circuitKey default 'unknown') as String)]"
                          objectStore="CircuitBreakerStore">
                    <os:value><![CDATA[#[{status: "CLOSED", failures: vars.circuitFailureCount, openedAt: 0}]]]></os:value>
                </os:store>
            </otherwise>
        </choice>
    </sub-flow>

    <!-- Dedup check: store event ID in Object Store; set isDuplicateRequest=true if already seen -->
    <sub-flow name="slack-dedupe-check-and-store-subflow">
        <set-variable variableName="isDuplicateRequest" value="#[false]" />
        <set-variable variableName="dedupeKey"
            value="#['slack-event:' ++ ((vars.requestId default 'unknown') as String)]" />
        <os:contains key="#[vars.dedupeKey]" objectStore="SlackEventDedupeStore" target="dedupeExists" />
        <choice>
            <when expression="#[(vars.dedupeExists default false)]">
                <set-variable variableName="isDuplicateRequest" value="#[true]" />
            </when>
            <otherwise>
                <os:store key="#[vars.dedupeKey]" objectStore="SlackEventDedupeStore">
                    <os:value><![CDATA[#[{storedAt: now() as String, sourceType: vars.sourceType default "unknown"}]]]></os:value>
                </os:store>
            </otherwise>
        </choice>
    </sub-flow>
</mule>
```

#### Step 21: Create slack-processing-subflow.xml

This is the async worker that posts the in-progress message, calls the orchestrator, and updates the thread with the final result.

Create `src/main/mule/slack-processing-subflow.xml` — use the full XML from the source repo at:
`slack-agent-router/src/main/mule/slack-processing-subflow.xml`

This file is the longest in the app (200 lines) and should be copied verbatim rather than typed. In Anypoint Studio, right-click the project → Import → select the file directly from the instructor's source.

Key behaviors to understand before proceeding:

| Behaviour | Where it lives |
|-----------|---------------|
| Posts "🎬 Initializing refund mission control..." immediately | Lines 12–28 |
| Updates with timing estimate while orchestrator runs | Lines 30–42 |
| Calls `POST {orchestrator.host}/api/orchestrate` with canonical payload | Lines 46–72 |
| Extracts `decision`, `caseId`, `stageStatus` from response | Lines 74–102 |
| Builds the final Slack message with pipeline view trace | Lines 117–145 |
| On error: graceful fallback message, circuit-breaker trip | Lines 148–168 |

#### Step 22: Create error.xml

Create `src/main/mule/error.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
                          http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
                          http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <error-handler name="globalDefaultErrorHandler">
        <on-error-continue type="ANY" logException="true">
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  status: "error",
  errorType: (error.errorType.identifier default "UNKNOWN") as String,
  message: error.description default "An unexpected error occurred"
}]]></ee:set-payload>
                </ee:message>
                <ee:variables>
                    <ee:set-variable variableName="httpStatus"><![CDATA[%dw 2.0
output application/java
---
if ((error.errorType.identifier default "UNKNOWN") contains "BAD_REQUEST") 400
else if ((error.errorType.identifier default "UNKNOWN") contains "NOT_FOUND") 404
else 500]]></ee:set-variable>
                </ee:variables>
            </ee:transform>
        </on-error-continue>
    </error-handler>
</mule>
```

#### Step 23: Run Locally (Optional)

Start locally on port 8081. The app will start cleanly even if `ai-orchestrator` is not running — the circuit breaker will handle it gracefully.

```bash
# From the slack-agent-router project directory
mvn clean package -DskipTests
# Then start in Anypoint Studio (Run As → Mule Application)
# OR use the local runtime wrapper if configured

# Verify health
curl -s http://localhost:8081/health
# Expected: {"status":"ok","probe":"liveness","service":"slack-agent-router"}

# Verify URL challenge handler
curl -s -X POST http://localhost:8081/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test-challenge-abc123"}'
# Expected: {"challenge":"test-challenge-abc123"}
```

### Part E: Test the Integration (~5 min)

> **Prerequisite**: The `slack-agent-router` MuleSoft app must be deployed and running with the Bot Token configured before these tests will work.

#### Step 12: Verify Bot Responds

1. In your Slack workspace, invite the bot to a channel: type `/invite @Agent Fabric`
2. Mention the bot: `@Agent Fabric what is the loyalty tier for student-slack-test@globaltech.com?`
3. **Expected**: The bot acknowledges the message (the exact response depends on the full agent network being deployed)

#### Step 13: Verify Slash Command

4. Type `/refund customer complained about late delivery for order ORD-123`
5. **Expected**: The bot responds with a confirmation modal or acknowledgment message

> If the bot doesn't respond, check:
> - Is `slack-agent-router` deployed and healthy? (`curl https://<app-url>/health`)
> - Is the Bot Token correct in the MuleSoft config?
> - Is the Request URL in Event Subscriptions verified (green checkmark)?
> - Is the bot invited to the channel?

---

### Verification Checklist

**Slack Configuration**
- [ ] Slack workspace created and ownership transferred to work email
- [ ] Slack app created with name "Agent Fabric"
- [ ] Bot Token Scopes configured (8 scopes)
- [ ] App installed to workspace — Bot Token (`xoxb-...`) obtained
- [ ] Event Subscriptions enabled — URL verified (green tick)
- [ ] Bot events subscribed: `app_mention`, `message.im`
- [ ] Interactivity enabled — Request URL set to `/slack/interactivity`
- [ ] Slash command `/refund` configured with correct Request URL

**MuleSoft App**
- [ ] `slack-agent-router` project created with all 7 XML files + 2 config YAML files
- [ ] `GET /health` returns `{"status":"ok","probe":"liveness","service":"slack-agent-router"}`
- [ ] `POST /slack/events` with `url_verification` type echoes back `challenge`
- [ ] Circuit breaker sub-flows present in `support-subflows.xml`
- [ ] Dedup Object Store (`SlackEventDedupeStore`) configured with 30-minute TTL

---

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Can't create workspace with work email | Corporate Slack restricts workspace creation | Use a personal email first, then transfer ownership |
| Event Subscriptions URL verification fails | MuleSoft app not running or wrong URL | Deploy slack-agent-router first, verify /health responds, then retry |
| Bot doesn't respond to @mention | Bot not invited to channel, or event not subscribed | `/invite @Agent Fabric` in the channel; verify `app_mention` event is subscribed |
| Bot doesn't respond to DM | `message.im` event not subscribed | Add `message.im` under Subscribe to bot events |
| Slash command returns "dispatch_failed" | Request URL wrong or app not running | Verify URL matches exactly: `https://<app>/slack/commands` |
| Modal doesn't appear after slash command | Interactivity URL not configured | Check Interactivity & Shortcuts → Request URL is set |
| "missing_scope" error in logs | Required scope not added | Check OAuth & Permissions → Bot Token Scopes for missing scope |
| "invalid_auth" in MuleSoft logs | Bot Token expired or wrong | Reinstall app to workspace to get a new token |

---

### Instructor Notes

- The Bot Token is the ONLY Slack credential the MuleSoft app needs. Everything else (Signing Secret, App Token) is optional for this course.
- If the workspace upgrade is not approved in time, the free tier works fine for all exercises. The main limitation is 90 days of message history.
- The three MuleSoft endpoint paths that Slack calls are:
  - `POST /slack/events` — Event Subscriptions (mentions, DMs)
  - `POST /slack/commands` — Slash Commands (`/refund`)
  - `POST /slack/interactivity` — Modal submissions, button clicks
- Students don't need their own Slack apps — they all use the same workspace and bot. The bot's behavior is determined by the MuleSoft app, not Slack configuration.
