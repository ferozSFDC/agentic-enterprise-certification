> **Missed earlier exercises? Catch up first:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 4
> ```
> Runs CP1–CP3 (Salesforce, Slack, Bedrock) and CP4 (downloads ai-orchestrator JAR, writes config, starts on :8082).
> Then continue at [Part A](#part-a) below — the app will already be running.

# Exercise 4 — Building the Process Layer: ai-orchestrator

## Objective

Build `ai-orchestrator` from scratch. By the end of this exercise:

- A POST to `http://localhost:8082/api/orchestrate` with a valid Slack user ID and order number
  returns a structured JSON response including a `decision`, `riskLevel`, `caseId`, and
  `stageStatus` map.
- You can explain every variable in the response by pointing to the file that set it.
- You have seen the circuit breaker open and the DLQ write fire.

## Background

`ai-orchestrator` is the Process layer API. It sits between `slack-agent-router`
(Experience layer, port 8081) and two System APIs: `data-cloud-sapi` (port 8083) and
`service-cloud-mcp` (port 8084). It calls Amazon Bedrock through the AI Gateway built in Module 4.

**Local port assignments** (set by the local runtime wrapper — not the default app config):

| App | Local port |
|-----|-----------|
| `slack-agent-router` | 8081 |
| `ai-orchestrator` | 8082 |
| `data-cloud-sapi` | 8083 |
| `service-cloud-mcp` | 8084 |

The apps default to port 8081 when run standalone in Anypoint Studio. The `mule-local-runtime/run.sh` script patches each app's port at deploy time so all four can run simultaneously. When running in Studio individually (e.g. during this exercise), port 8081 is the default; when running via `run.sh`, use port 8082.

This exercise builds on the Salesforce org and AWS Bedrock resources set up in Exercises 1–3.
It does not repeat any setup from those exercises.

---

## Part A — Project Setup

### A.1 — Create the Maven project

1. In Anypoint Studio, select **File > New > Mule Project**.
2. Set:
   - Project name: `ai-orchestrator`
   - Mule runtime: `4.11.3`
   - Maven: enable (the wizard creates a `pom.xml`)
3. Click **Finish**.

### A.2 — Edit pom.xml

Open `pom.xml`. Replace the `<properties>` and `<dependencies>` sections with the following.
Leave `<groupId>`, `<artifactId>`, and `<version>` as the wizard generated them.

**Properties block** (add inside `<properties>`):
```xml
<app.runtime>4.11.3</app.runtime>
<mule.maven.plugin.version>4.7.0</mule.maven.plugin.version>
<munit.version>3.7.1</munit.version>
<env>dev</env>
<http.pool.maxConnections>10</http.pool.maxConnections>
<http.pool.connectionIdleTimeoutMs>30000</http.pool.connectionIdleTimeoutMs>
<https.listener.port>8082</https.listener.port>
<tls.keystore.path>certs/localhost-keystore.jks</tls.keystore.path>
<tls.keystore.type>JKS</tls.keystore.type>
<tls.keystore.alias>localhost</tls.keystore.alias>
<tls.keystore.password>changeit</tls.keystore.password>
<tls.keystore.keyPassword>changeit</tls.keystore.keyPassword>
<tls.truststore.path>certs/localhost-truststore.jks</tls.truststore.path>
<tls.truststore.type>JKS</tls.truststore.type>
<tls.truststore.password>changeit</tls.truststore.password>
<aws.region>us-east-2</aws.region>
<aws.accessKeyId>${env.AWS_ACCESS_KEY_ID}</aws.accessKeyId>
<aws.secretAccessKey>${env.AWS_SECRET_ACCESS_KEY}</aws.secretAccessKey>
<bedrock.agentId>${env.BEDROCK_AGENT_ID}</bedrock.agentId>
<bedrock.agentAliasId>${env.BEDROCK_AGENT_ALIAS_ID}</bedrock.agentAliasId>
<ai-gateway.host>localhost</ai-gateway.host>
<ai-gateway.openaiPath>/llmproxy2/chat/completions</ai-gateway.openaiPath>
<ai-gateway.anthropicPath>/llmproxy/v1/messages</ai-gateway.anthropicPath>
<ai-gateway.apiStyle>openai</ai-gateway.apiStyle>
<ai-gateway.clientId>local-dev</ai-gateway.clientId>
<ai-gateway.clientSecret>local-dev</ai-gateway.clientSecret>
<ai-gateway.connectTimeoutMs>10000</ai-gateway.connectTimeoutMs>
<ai-gateway.readTimeoutMs>30000</ai-gateway.readTimeoutMs>
<data-cloud.host>localhost</data-cloud.host>
<service-cloud-mcp.host>localhost</service-cloud-mcp.host>
<bedrock-proxy.host>localhost</bedrock-proxy.host>
<scanner.enabled>false</scanner.enabled>
<scanner.host>localhost</scanner.host>
<scanner.path>/api/v1/agent/chat</scanner.path>
<scanner.authHeader>none</scanner.authHeader>
<scanner.connectTimeoutMs>10000</scanner.connectTimeoutMs>
<scanner.readTimeoutMs>30000</scanner.readTimeoutMs>
```

**Dependencies block** (replace the entire `<dependencies>` element):
```xml
<dependencies>
    <dependency>
        <groupId>org.mule.connectors</groupId>
        <artifactId>mule-http-connector</artifactId>
        <version>1.9.3</version>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>com.mulesoft.connectors</groupId>
        <artifactId>mule-salesforce-connector</artifactId>
        <version>11.4.0</version>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>org.mule.modules</groupId>
        <artifactId>mule-apikit-module</artifactId>
        <version>1.10.0</version>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>org.mule.connectors</groupId>
        <artifactId>mule-objectstore-connector</artifactId>
        <version>1.2.1</version>
        <classifier>mule-plugin</classifier>
    </dependency>
    <dependency>
        <groupId>software.amazon.awssdk</groupId>
        <artifactId>bedrockagentruntime</artifactId>
        <version>2.26.22</version>
    </dependency>
    <dependency>
        <groupId>com.mulesoft.munit</groupId>
        <artifactId>munit-runner</artifactId>
        <version>${munit.version}</version>
        <classifier>mule-plugin</classifier>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>com.mulesoft.munit</groupId>
        <artifactId>munit-tools</artifactId>
        <version>${munit.version}</version>
        <classifier>mule-plugin</classifier>
        <scope>test</scope>
    </dependency>
</dependencies>
```

4. Save `pom.xml`. Studio will resolve dependencies. Wait for the Maven build to complete before
   proceeding.

### A.3 — Java source directory

1. Create directory: `src/main/java/com/feroz/orchestrator/`
2. Leave it empty for now. You will add `BedrockDirectInvoker.java` in Part G.

### A.4 — Copy TLS keystores

1. From the reference project (provided by your instructor or downloaded from the course repo),
   copy the contents of `ai-orchestrator/src/main/resources/certs/` into your project's
   `src/main/resources/certs/`.
2. Files to copy: `localhost-keystore.jks`, `localhost-truststore.jks`, `localhost.crt`.

**Checkpoint A:**
```bash
curl http://localhost:8081/health
```
Expected: project is not yet running. This is the baseline — confirm no other process occupies
port 8081 before you start.

> **Port note for this exercise**: All curl examples below use port 8081, which is the default when running `ai-orchestrator` standalone in Anypoint Studio. If you are using `mule-local-runtime/run.sh` to run all four apps simultaneously, `ai-orchestrator` runs on port 8082 — replace `8081` with `8082` in every curl command.

---

## Part B — RAML Spec

### B.1 — Create the API spec file

1. Create file: `src/main/resources/api/ai-orchestrator-papi.raml`
2. Paste exactly:

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
      200:
        body:
          application/json:
            type: OrchestrateResponse
      400:
        body:
          application/json:
            type: object
      500:
        body:
          application/json:
            type: object
```

**Checkpoint B:**
In Anypoint Studio, right-click the RAML file and choose **Mule > Generate Flows from RAML**.
Studio should create a scaffolded flow. You will replace it with your own in Part D, so discard
the scaffold afterward — the check is that the RAML parses without errors.

---

## Part C — Global Config

### C.1 — Create global-config.xml

Create `src/main/mule/global-config.xml` with the following content in full:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:apikit="http://www.mulesoft.org/schema/mule/mule-apikit"
      xmlns:tls="http://www.mulesoft.org/schema/mule/tls"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd
http://www.mulesoft.org/schema/mule/mule-apikit http://www.mulesoft.org/schema/mule/mule-apikit/current/mule-apikit.xsd
http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
http://www.mulesoft.org/schema/mule/tls http://www.mulesoft.org/schema/mule/tls/current/mule-tls.xsd">

    <tls:context name="sharedTlsContext" doc:name="Shared TLS Context">
        <tls:key-store path="${tls.keystore.path}"
                       type="${tls.keystore.type}"
                       alias="${tls.keystore.alias}"
                       password="${tls.keystore.password}"
                       keyPassword="${tls.keystore.keyPassword}" />
    </tls:context>

    <http:listener-config name="httpListenerConfig" doc:name="HTTP Listener config">
        <http:listener-connection host="0.0.0.0" port="8081" />
    </http:listener-config>

    <http:listener-config name="httpsListenerConfig" doc:name="HTTPS Listener config">
        <http:listener-connection protocol="HTTPS" host="0.0.0.0"
                                  port="${https.listener.port}"
                                  tlsContext="sharedTlsContext" />
    </http:listener-config>

    <configuration defaultErrorHandler-ref="Global_Default_Error_Handler"
                   doc:name="Global Error Configuration" />

    <http:request-config name="dataCloudRequestConfig" doc:name="Data Cloud SAPI" basePath="/api">
        <http:request-connection protocol="HTTPS" host="${data-cloud.host}" port="443"
                                 maxConnections="${http.pool.maxConnections}"
                                 connectionIdleTimeout="${http.pool.connectionIdleTimeoutMs}">
            <reconnection>
                <reconnect count="3" frequency="2000" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <http:request-config name="aiGatewayRequestConfig" doc:name="AI Gateway Request Config">
        <http:request-connection protocol="HTTPS" host="${ai-gateway.host}" port="443"
                                 maxConnections="${http.pool.maxConnections}"
                                 connectionIdleTimeout="${http.pool.connectionIdleTimeoutMs}">
            <reconnection>
                <reconnect count="3" frequency="2000" />
            </reconnection>
        </http:request-connection>
        <http:default-headers>
            <http:default-header key="Content-Type" value="application/json" />
            <http:default-header key="client_id" value="${ai-gateway.clientId}" />
            <http:default-header key="client_secret" value="${ai-gateway.clientSecret}" />
        </http:default-headers>
    </http:request-config>

    <http:request-config name="serviceCloudMcpRequestConfig" doc:name="Service Cloud MCP"
                         basePath="/mcp">
        <http:request-connection protocol="HTTPS" host="${service-cloud-mcp.host}" port="443"
                                 maxConnections="${http.pool.maxConnections}"
                                 connectionIdleTimeout="${http.pool.connectionIdleTimeoutMs}">
            <reconnection>
                <reconnect count="3" frequency="2000" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <http:request-config name="bedrockProxyRequestConfig" doc:name="Bedrock Proxy Request">
        <http:request-connection protocol="HTTPS" host="${bedrock-proxy.host}" port="443"
                                 maxConnections="${http.pool.maxConnections}"
                                 connectionIdleTimeout="${http.pool.connectionIdleTimeoutMs}">
            <reconnection>
                <reconnect count="3" frequency="2000" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <http:request-config name="readinessDataCloudRequestConfig"
                         doc:name="Readiness Data Cloud Request">
        <http:request-connection protocol="HTTPS" host="${data-cloud.host}" port="443"
                                 maxConnections="4" connectionIdleTimeout="15000">
            <reconnection>
                <reconnect count="1" frequency="250" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <http:request-config name="readinessServiceCloudRequestConfig"
                         doc:name="Readiness Service Cloud Request">
        <http:request-connection protocol="HTTPS" host="${service-cloud-mcp.host}" port="443"
                                 maxConnections="4" connectionIdleTimeout="15000">
            <reconnection>
                <reconnect count="1" frequency="250" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <http:request-config name="localOrchestratorRequestConfig"
                         doc:name="Local Orchestrator Request Config">
        <http:request-connection protocol="HTTP" host="127.0.0.1" port="8081">
            <reconnection>
                <reconnect count="3" frequency="2000" />
            </reconnection>
        </http:request-connection>
    </http:request-config>

    <configuration-properties file="shared-config.yaml"
                               doc:name="Common Configuration Properties" />
    <configuration-properties file="${env}-config.yaml"
                               doc:name="Environment Configuration Properties" />

    <apikit:config name="ai-orchestrator-apikit-config"
                   api="api/ai-orchestrator-papi.raml"
                   outboundHeadersMapName="outboundHeaders"
                   httpStatusVarName="httpStatus" />

    <salesforce:sfdc-config name="salesforceConfig" doc:name="Salesforce Config">
        <salesforce:basic-connection
            username="${sfdc.username}"
            password="${sfdc.password}"
            securityToken="${sfdc.token}"
            url="${sfdc.url}" />
    </salesforce:sfdc-config>

    <os:object-store name="circuitBreakerObjectStore"
                     persistent="true"
                     maxEntries="500"
                     doc:name="Circuit Breaker Object Store" />

    <os:object-store name="profileCacheObjectStore"
                     persistent="true"
                     maxEntries="5000"
                     entryTtl="5"
                     entryTtlUnit="MINUTES"
                     doc:name="Profile Cache Object Store" />

    <os:object-store name="workflowDlqObjectStore"
                     persistent="true"
                     maxEntries="5000"
                     entryTtl="7"
                     entryTtlUnit="DAYS"
                     doc:name="Workflow Dead Letter Object Store" />

    <os:object-store name="requestDedupeObjectStore"
                     persistent="true"
                     maxEntries="20000"
                     entryTtl="30"
                     entryTtlUnit="MINUTES"
                     doc:name="Request Dedupe Object Store" />

    <os:object-store name="dlqMetricsObjectStore"
                     persistent="true"
                     maxEntries="100"
                     entryTtl="30"
                     entryTtlUnit="DAYS"
                     doc:name="DLQ Metrics Object Store" />

</mule>
```

Note the `scannerRequestConfig` is present in the reference project but the scanner feature is
disabled (`scanner.enabled=false`). You may omit it; `assess-risk` does not reference it.

---

## Part D — The 6-Stage Pipeline

Create each file below in `src/main/mule/`. The namespace declarations are identical across all
files; copy them from the first file you create.

### D.1 — error.xml

Create `src/main/mule/error.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <error-handler name="Global_Default_Error_Handler">
        <on-error-propagate type="VALIDATION:*" logException="true" doc:name="Validation Error">
            <set-variable variableName="httpStatus" value="#[400]" doc:name="Set 400" />
            <set-payload value='#[output application/json ---
{
    error: {
        code: error.errorType.identifier default "BAD_REQUEST",
        message: error.description default "Validation failed",
        correlationId: correlationId
    }
}]' doc:name="Validation Envelope" />
        </on-error-propagate>
        <on-error-propagate type="HTTP:NOT_FOUND" logException="true" doc:name="Not Found Error">
            <set-variable variableName="httpStatus" value="#[404]" doc:name="Set 404" />
            <set-payload value='#[output application/json ---
{
    error: {
        code: error.errorType.identifier default "NOT_FOUND",
        message: error.description default "Resource not found",
        correlationId: correlationId
    }
}]' doc:name="Not Found Envelope" />
        </on-error-propagate>
        <on-error-propagate type="CONNECTIVITY:*" logException="true"
                            doc:name="Service Unavailable Error">
            <set-variable variableName="httpStatus" value="#[503]" doc:name="Set 503" />
            <set-payload value='#[output application/json ---
{
    error: {
        code: error.errorType.identifier default "SERVICE_UNAVAILABLE",
        message: error.description default "Downstream service unavailable",
        correlationId: correlationId
    }
}]' doc:name="Service Unavailable Envelope" />
        </on-error-propagate>
        <on-error-propagate type="ANY" logException="true" doc:name="Unhandled Error">
            <set-variable variableName="httpStatus" value="#[500]" doc:name="Set 500" />
            <set-payload value='#[output application/json ---
{
    error: {
        code: error.errorType.identifier default "INTERNAL_ERROR",
        message: error.description default "Unexpected internal error",
        correlationId: correlationId
    }
}]' doc:name="Unhandled Error Envelope" />
        </on-error-propagate>
    </error-handler>
</mule>
```

### D.2 — orchestration-context.xml

Create `src/main/mule/orchestration-context.xml`. This file has two sub-flows:
`initialize-orchestration-context` and `process-orchestration-request`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd">

    <sub-flow name="initialize-orchestration-context">
        <set-variable variableName="httpStatus" value="#[200]" doc:name="Default 200" />
        <!-- userId: prefer payload.slackUserId, then payload.userId, then x-user-id header -->
        <set-variable variableName="userId"
                      value='#[output application/java import try from dw::Runtime ---
do {
  var parsedUserId = try(() -> (payload.slackUserId default payload.userId
                               default attributes.headers."x-user-id" default "unknown") as String)
  ---
  if ((parsedUserId.success default false) as Boolean) parsedUserId.result else "unknown"
}]'
                      doc:name="Save User ID" />
        <set-variable variableName="inputText"
                      value='#[output application/java import try from dw::Runtime ---
do {
  var parsedInputText = try(() -> (payload.inputText default payload.rawText default "Hello") as String)
  ---
  if ((parsedInputText.success default false) as Boolean) parsedInputText.result else "Hello"
}]'
                      doc:name="Save Input Text" />
        <set-variable variableName="sessionId"
                      value='#[output application/java ---
(payload.sessionId default payload.slackThreadTs default payload.threadTs default now() as String) as String]'
                      doc:name="Save Session ID" />
        <set-variable variableName="flowId"
                      value='#[output application/java ---
(payload.flowId default attributes.headers."x-flow-id" default vars.sessionId default correlationId) as String]'
                      doc:name="Save Flow ID" />
        <set-variable variableName="requestId"
                      value='#[output application/java ---
(payload.requestId default attributes.headers."x-request-id" default correlationId) as String]'
                      doc:name="Save Request ID" />
        <!-- Deduplication key: "request::" + requestId -->
        <set-variable variableName="dedupeKey"
                      value='#[output application/java --- "request::" ++ ((vars.requestId default correlationId) as String)]'
                      doc:name="Build Dedupe Key" />
        <os:contains key="#[vars.dedupeKey]"
                     objectStore="requestDedupeObjectStore"
                     target="isDuplicateRequest"
                     doc:name="Check Duplicate Request" />
        <choice doc:name="Short Circuit Duplicate Request">
            <when expression="#[(vars.isDuplicateRequest default false) as Boolean]">
                <logger level="WARN" doc:name="Log Duplicate Request Detected"
                        message="telemetry stage=DUPLICATE_REQUEST flowId=#[vars.flowId] requestId=#[vars.requestId] dedupeKey=#[vars.dedupeKey]" />
            </when>
            <otherwise>
                <os:store key="#[vars.dedupeKey]" objectStore="requestDedupeObjectStore"
                          doc:name="Store Dedupe Marker">
                    <os:value><![CDATA[#[{
    createdAt: now() as String,
    flowId: vars.flowId default "",
    sessionId: vars.sessionId default ""
}]]]></os:value>
                </os:store>
            </otherwise>
        </choice>
        <!-- Structured extraction forwarded from slack-agent-router -->
        <set-variable variableName="contractVersion"
                      value='#[output application/java --- (payload.contractVersion default "1.2") as String]'
                      doc:name="Save Contract Version" />
        <set-variable variableName="structuredOrderNumber"
                      value='#[output application/java --- (payload.structured.orderNumber default null)]'
                      doc:name="Save Structured Order Number" />
        <set-variable variableName="structuredReason"
                      value='#[output application/java --- (payload.structured.reason default null)]'
                      doc:name="Save Structured Reason" />
        <!-- Safe defaults for every variable referenced downstream -->
        <set-variable variableName="scannerUsedFallback" value="#[false]" doc:name="Default Scanner Path" />
        <set-variable variableName="scannerEnabled"
                      value='#[output application/java --- lower((p("scanner.enabled") default "false") as String) == "true"]'
                      doc:name="Resolve Scanner Enabled" />
        <set-variable variableName="agentError" value="#[false]" doc:name="Default Agent Error" />
        <set-variable variableName="decision" value="ESCALATE" doc:name="Default Decision" />
        <set-variable variableName="shouldIssueCredit" value="#[false]" doc:name="Default Credit Decision" />
        <set-variable variableName="riskLevel" value="UNKNOWN" doc:name="Default Risk Level" />
        <set-variable variableName="riskScore" value="#[-1]" doc:name="Default Risk Score" />
        <set-variable variableName="caseId" value="#[null]" doc:name="Default Case ID" />
        <set-variable variableName="intent" value="UNKNOWN" doc:name="Default Intent" />
        <set-variable variableName="orderCandidates" value="#[[]]" doc:name="Default Order Candidates" />
        <set-variable variableName="orderIdAmbiguous" value="#[false]" doc:name="Default Order Ambiguity" />
        <set-variable variableName="hasValidOrderId" value="#[false]" doc:name="Default Order ID Validity" />
        <set-variable variableName="identityMissing" value="#[false]" doc:name="Default Identity Validation" />
        <set-variable variableName="validationMessage" value="#[null]" doc:name="Default Validation Message" />
        <set-variable variableName="validationCode" value="#[null]" doc:name="Default Validation Code" />
        <set-variable variableName="customerId" value="#[null]" doc:name="Default Customer ID" />
        <set-variable variableName="normalizedOrderNumber" value="UNKNOWN" doc:name="Default Normalized Order" />
        <set-variable variableName="normalizedReason" value="" doc:name="Default Normalized Reason" />
        <set-variable variableName="traceIdsComplete" value="#[false]" doc:name="Default Trace Completeness" />
        <set-variable variableName="mutationPayloadComplete" value="#[false]" doc:name="Default Mutation Completeness" />
        <set-variable variableName="hasReason" value="#[false]" doc:name="Default Has Reason" />
        <set-variable variableName="hasCustomerId" value="#[false]" doc:name="Default Has Customer ID" />
        <set-variable variableName="policyRuleMatched" value="#[false]" doc:name="Default Policy Rule Match" />
        <set-variable variableName="allowMutation" value="#[false]" doc:name="Default Mutation Gate" />
        <set-variable variableName="stageDataCloud" value="NOT_RUN" doc:name="Default Stage Data Cloud" />
        <set-variable variableName="stageScanner" value="NOT_RUN" doc:name="Default Stage Scanner" />
        <set-variable variableName="stageGateway" value="NOT_RUN" doc:name="Default Stage Gateway" />
        <set-variable variableName="stageServiceCloud" value="NOT_RUN" doc:name="Default Stage Service Cloud" />
        <set-variable variableName="decisionSource" value="policy" doc:name="Default Decision Source" />
        <set-variable variableName="decisionContractVersion" value="bedrock-v1" doc:name="Default Decision Contract Version" />
        <set-variable variableName="decisionPolicyVersion" value="orchestrator-policy-v2" doc:name="Default Decision Policy Version" />
        <set-variable variableName="failureClassification" value="#[null]" doc:name="Default Failure Classification" />
        <set-variable variableName="bedrockDecisionCandidate" value="#[null]" doc:name="Default Bedrock Decision Candidate" />
        <set-variable variableName="refundAmount" value="#[0]" doc:name="Default Refund Amount" />
        <set-variable variableName="refundAmountSource" value="unresolved" doc:name="Default Refund Amount Source" />
        <set-variable variableName="refundProduct" value="GENERAL_REFUND_CREDIT" doc:name="Default Refund Product" />
        <!-- Circuit breaker initialization -->
        <set-variable variableName="circuitFailureThreshold" value="#[3]" doc:name="Circuit Failure Threshold" />
        <set-variable variableName="circuitCooldownMs" value="#[60000]" doc:name="Circuit Cooldown Window" />
        <set-variable variableName="circuitKey" value="#[null]" doc:name="Circuit Key Placeholder" />
        <set-variable variableName="circuitOpen" value="#[false]" doc:name="Circuit Open Flag" />
        <set-variable variableName="circuitRetryAfter" value="#[null]" doc:name="Circuit Retry-After Seconds" />
    </sub-flow>

    <sub-flow name="process-orchestration-request">
        <logger level="INFO" doc:name="Log Entry"
                message="telemetry stage=START flowId=#[vars.flowId] requestId=#[vars.requestId] sessionId=#[vars.sessionId] userId=#[vars.userId] orderNumber=#[vars.orderNumber default 'UNKNOWN'] decision=#[vars.decision] caseId=#[vars.caseId default 'null'] contractVersion=#[vars.contractVersion] inputText=#[vars.inputText]" />
        <choice doc:name="Process Duplicate Or Normal Request">
            <when expression="#[(vars.isDuplicateRequest default false) as Boolean]">
                <set-variable variableName="decision" value="CLARIFY" doc:name="Set Duplicate Decision" />
                <set-variable variableName="shouldIssueCredit" value="#[false]" doc:name="Disable Credit Duplicate Request" />
                <set-variable variableName="allowMutation" value="#[false]" doc:name="Disable Mutation Duplicate Request" />
                <set-variable variableName="failureClassification" value="DUPLICATE_REQUEST" doc:name="Classify Duplicate Request" />
                <set-variable variableName="agentResponse"
                              value="This request was already received. Please wait for the previous outcome."
                              doc:name="Set Duplicate Response" />
                <set-variable variableName="stageDataCloud" value="SKIPPED" doc:name="Skip Data Cloud Duplicate Request" />
                <set-variable variableName="stageScanner" value="SKIPPED" doc:name="Skip Scanner Duplicate Request" />
                <set-variable variableName="stageGateway" value="SKIPPED" doc:name="Skip Gateway Duplicate Request" />
                <set-variable variableName="stageServiceCloud" value="SKIPPED" doc:name="Skip Service Cloud Duplicate Request" />
            </when>
            <otherwise>
                <flow-ref name="validate-identity" doc:name="validate-identity" />
                <flow-ref name="enrich-customer-profile" doc:name="enrich-customer-profile" />
                <flow-ref name="resolve-intent-and-order" doc:name="resolve-intent-and-order" />
                <flow-ref name="assess-risk" doc:name="assess-risk" />
                <flow-ref name="enforce-policy" doc:name="enforce-policy" />
                <flow-ref name="execute-mutation" doc:name="execute-mutation" />
            </otherwise>
        </choice>
    </sub-flow>
</mule>
```

### D.3 — orchestration-flow.xml

Create `src/main/mule/orchestration-flow.xml`. This is the entry point: HTTP listener + final
response assembly.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <flow name="orchestrate-ai-interaction-flow">
        <http:listener doc:name="POST /api/orchestrate"
                       config-ref="httpListenerConfig"
                       path="/api/orchestrate"
                       allowedMethods="POST">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[vars.outboundHeaders default {"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 500]">
                <http:headers>#[vars.outboundHeaders default {"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>

        <flow-ref name="initialize-orchestration-context"
                  doc:name="Initialize Orchestration Context" />
        <flow-ref name="process-orchestration-request"
                  doc:name="Process Orchestration Request" />

        <ee:transform doc:name="Build Final Response Envelope">
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
var baseResponse = vars.agentResponse default "I was unable to process your request."
---
{
    "response": if (((vars.caseId default null) != null) and (not isBlank((vars.caseId default "") as String)))
        baseResponse ++ "\n\nCase Reference: " ++ vars.caseId
    else
        baseResponse,
    "metadata": {
        "decision": vars.decision default "ESCALATE",
        "shouldIssueCredit": vars.shouldIssueCredit default false,
        "riskLevel": vars.riskLevel default "UNKNOWN",
        "riskScore": vars.riskScore default -1,
        "intent": vars.intent default "GENERAL_QUERY",
        "orderNumber": vars.orderNumber default "UNKNOWN",
        "orderIdAmbiguous": vars.orderIdAmbiguous default false,
        "hasValidOrderId": vars.hasValidOrderId default false,
        "flowId": vars.flowId default "",
        "requestId": vars.requestId default "",
        "caseId": vars.caseId default null,
        "sessionId": vars.sessionId default "",
        "usedFallback": vars.scannerUsedFallback default false,
        "agentError": vars.agentError default false,
        "contractVersion": vars.contractVersion default "legacy",
        "decisionSource": vars.decisionSource default "policy",
        "decisionContractVersion": vars.decisionContractVersion default "bedrock-v1",
        "decisionPolicyVersion": vars.decisionPolicyVersion default "orchestrator-policy-v2",
        "failureClassification": vars.failureClassification default null,
        "refundAmount": vars.refundAmount default 0,
        "refundAmountSource": vars.refundAmountSource default "fallback_random_product",
        "gates": {
            "allowMutation": vars.allowMutation default false,
            "hasValidOrder": vars.hasValidOrderId default false,
            "hasReason": vars.hasReason default false,
            "hasCustomerId": vars.hasCustomerId default false,
            "policyRuleMatched": vars.policyRuleMatched default false
        },
        "stageStatus": {
            "dataCloud": vars.stageDataCloud default "NOT_RUN",
            "scanner": vars.stageScanner default "NOT_RUN",
            "gateway": vars.stageGateway default "NOT_RUN",
            "serviceCloud": vars.stageServiceCloud default "NOT_RUN"
        },
        "validation": if ((vars.validationCode default null) != null)
            {
                "statusCode": vars.validationCode,
                "message": vars.validationMessage default ""
            }
        else
            null
    }
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>

        <logger level="INFO" doc:name="Log Final"
                message="telemetry stage=FINAL flowId=#[vars.flowId] requestId=#[vars.requestId] sessionId=#[vars.sessionId] userId=#[vars.userId] orderNumber=#[vars.orderNumber default 'UNKNOWN'] decision=#[vars.decision] caseId=#[vars.caseId default 'null'] fallback=#[vars.scannerUsedFallback] agentError=#[vars.agentError] decisionSource=#[vars.decisionSource] dataCloud=#[vars.stageDataCloud] scanner=#[vars.stageScanner] gateway=#[vars.stageGateway] serviceCloud=#[vars.stageServiceCloud]" />
    </flow>
</mule>
```

**Checkpoint D.3:** Start the app. Then:
```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"inputText":"test"}' | python3 -m json.tool
```
Expected: a JSON response with `"decision": "ESCALATE"` (from the default), `stageStatus` all
`NOT_RUN`, and no 500 error. The pipeline sub-flows do not exist yet — this confirms the listener
and context-init work.

### D.4 — business-validation.xml

Create `src/main/mule/business-validation.xml`. Contains `validate-identity` and
`enrich-customer-profile`.

The key sections:

**validate-identity sub-flow** — checks whether userId is blank or "unknown":

```xml
<sub-flow name="validate-identity">
    <choice doc:name="Validate Trusted Identity">
        <when expression='#[isBlank((vars.userId default "") as String)
                           or ((vars.userId default "unknown") as String) == "unknown"]'>
            <set-variable variableName="identityMissing" value="#[true]" />
            <set-variable variableName="decision" value="CLARIFY" />
            <set-variable variableName="shouldIssueCredit" value="#[false]" />
            <set-variable variableName="validationCode" value="#[400]" />
            <set-variable variableName="validationMessage"
                          value="Missing trusted identity (x-user-id/slackUserId). Cannot process a transactional request." />
            <set-variable variableName="failureClassification" value="POLICY_REJECTED" />
            <set-variable variableName="agentResponse" value="#[vars.validationMessage]" />
            <logger level="WARN"
                    message="telemetry stage=VALIDATION_FAIL flowId=#[vars.flowId] requestId=#[vars.requestId] sessionId=#[vars.sessionId] userId=#[vars.userId] orderNumber=#[vars.orderNumber default 'UNKNOWN'] decision=#[vars.decision] caseId=#[vars.caseId default 'null'] reason=missing-trusted-identity" />
        </when>
    </choice>
</sub-flow>
```

**enrich-customer-profile sub-flow** — cache-aside pattern:

```xml
<sub-flow name="enrich-customer-profile">
    <set-variable variableName="profileCacheKey"
                  value='#[output application/java --- "profile::" ++ ((vars.userId default "unknown") as String)]' />
    <os:contains key="#[vars.profileCacheKey]"
                 objectStore="profileCacheObjectStore"
                 target="profileCacheHit" />
    <choice doc:name="Use Cached Profile?">
        <when expression="#[(vars.profileCacheHit default false) as Boolean]">
            <os:retrieve key="#[vars.profileCacheKey]"
                         objectStore="profileCacheObjectStore"
                         target="customerProfile" />
            <set-variable variableName="stageDataCloud" value="CACHE_HIT" />
        </when>
        <otherwise>
            <try doc:name="Fetch Customer Profile">
                <set-variable variableName="stageDataCloud" value="START" />
                <http:request method="GET"
                              config-ref="dataCloudRequestConfig"
                              path='#["/profile/" ++ vars.userId]'>
                    <http:headers>#[{"x-user-id": vars.userId, "x-flow-id": vars.flowId,
                                     "x-request-id": vars.requestId, "x-session-id": vars.sessionId}]</http:headers>
                </http:request>
                <set-variable variableName="customerProfile" value="#[payload]" />
                <os:store key="#[vars.profileCacheKey]" objectStore="profileCacheObjectStore">
                    <os:value>#[vars.customerProfile]</os:value>
                </os:store>
                <set-variable variableName="stageDataCloud" value="OK" />
                <logger level="INFO"
                        message="telemetry stage=DATA_CLOUD_OK flowId=#[vars.flowId] requestId=#[vars.requestId] customerTier=#[vars.customerProfile.customerTier default 'Standard']" />
                <error-handler>
                    <on-error-continue type="ANY" logException="true">
                        <set-variable variableName="customerProfile"
                                      value='#[{"customerName": "Guest", "customerTier": "Standard", "churnRisk": "UNKNOWN"}]' />
                        <set-variable variableName="stageDataCloud" value="FAIL" />
                        <logger level="WARN"
                                message="telemetry stage=DATA_CLOUD_FALLBACK flowId=#[vars.flowId] requestId=#[vars.requestId] reason=data-cloud-unavailable" />
                    </on-error-continue>
                </error-handler>
            </try>
        </otherwise>
    </choice>
</sub-flow>
```

**Checkpoint D.4:**
```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"inputText":"I need a refund", "userId":""}' | python3 -m json.tool
```
Expected: `"decision": "CLARIFY"`, `metadata.validation.statusCode: 400`,
`metadata.validation.message` contains "Missing trusted identity".

### D.5 — business-resolution-refund.xml

Create `src/main/mule/business-resolution-refund.xml`. Contains sub-flow
`resolve-refund-amount-from-salesforce`.

```xml
<sub-flow name="resolve-refund-amount-from-salesforce">
    <try doc:name="Resolve Refund Amount From Salesforce">
        <salesforce:query doc:name="Query Salesforce Amount" config-ref="salesforceConfig">
            <salesforce:salesforce-query><![CDATA[#[
"SELECT Amount, Name FROM Opportunity WHERE Name LIKE '%"
++ (vars.sanitizedOrderSearchTerm default "UNKNOWN")
++ "%' ORDER BY LastModifiedDate DESC LIMIT 1"
]]]></salesforce:salesforce-query>
        </salesforce:query>
        <choice doc:name="Salesforce Amount Found?">
            <when expression='#[sizeOf(payload) > 0 and (payload[0].Amount default null) != null]'>
                <set-variable variableName="refundAmount"
                              value='#[output application/java --- (payload[0].Amount default 0) as Number]' />
                <set-variable variableName="refundAmountSource" value="salesforce_query" />
                <set-variable variableName="refundProduct"
                              value='#[output application/java ---
(payload[0].Name default vars.refundProduct default "GENERAL_REFUND_CREDIT") as String]' />
            </when>
            <otherwise>
                <set-variable variableName="decision" value="CLARIFY" />
                <set-variable variableName="shouldIssueCredit" value="#[false]" />
                <set-variable variableName="validationCode" value="#[400]" />
                <set-variable variableName="validationMessage"
                              value="Unable to resolve refund amount from Salesforce for this order." />
                <set-variable variableName="failureClassification" value="POLICY_REJECTED" />
                <set-variable variableName="agentResponse" value="#[vars.validationMessage]" />
            </otherwise>
        </choice>
        <error-handler>
            <on-error-continue type="ANY" logException="true">
                <set-variable variableName="decision" value="CLARIFY" />
                <set-variable variableName="shouldIssueCredit" value="#[false]" />
                <set-variable variableName="validationCode" value="#[502]" />
                <set-variable variableName="validationMessage"
                              value="Unable to resolve refund amount from Salesforce right now. Please try again." />
                <set-variable variableName="failureClassification" value="SALESFORCE_UNAVAILABLE" />
                <set-variable variableName="agentResponse" value="#[vars.validationMessage]" />
                <logger level="WARN"
                        message="telemetry stage=AMOUNT_LOOKUP_FALLBACK flowId=#[vars.flowId] requestId=#[vars.requestId] orderNumber=#[vars.normalizedOrderNumber default 'UNKNOWN'] reason=salesforce-lookup-failed" />
            </on-error-continue>
        </error-handler>
    </try>
</sub-flow>
```

### D.6 — business-resolution.xml

Create `src/main/mule/business-resolution.xml`. Contains sub-flow `resolve-intent-and-order`.

The sub-flow initializes its own defaults (it can be called independently), then performs intent
inference, order extraction, and calls `resolve-refund-amount-from-salesforce`.

Key DataWeave blocks to type exactly:

**Order extraction (structured takes priority, regex is fallback):**
```xml
<set-variable variableName="orderCandidatesParse"
              value='#[output application/java import try from dw::Runtime ---
try(() -> if ((vars.structuredOrderNumber default null) != null
             and !isBlank((vars.structuredOrderNumber as String)))
    [vars.structuredOrderNumber as String]
else
    (
        (
            (vars.inputText scan /\b(ORD-[A-Za-z0-9-]+|\d{3}-\d{3}|\d{3}-\d{2,4}-\d|\d{5,})\b/)
                map ((m) -> upper((m[0]) as String))
        )
            distinctBy ((x) -> x)
    ) default []
)]' />
```

**Intent inference:**
```xml
<set-variable variableName="intent"
              value='#[output application/java ---
if (upper((payload.structured.intent default payload.intent default "") as String) == "REFUND_REQUEST")
    "REFUND_REQUEST"
else if (upper((payload.structured.intent default payload.intent default "") as String) == "ORDER_INQUIRY")
    "ORDER_INQUIRY"
else if (contains(lower((vars.inputText default "") as String), "refund"))
    "REFUND_REQUEST"
else if (contains(lower((vars.inputText default "") as String), "order"))
    "ORDER_INQUIRY"
else
    "UNKNOWN"
]' />
```

**SOQL sanitization call:**
```xml
<set-variable variableName="sanitizedOrderSearchTerm"
              value='#[output application/java
---
dw::sanitize::sanitizeOrderNumberForSoqlLike(vars.normalizedOrderNumber default "UNKNOWN")
]' />
```

End the sub-flow with:
```xml
<flow-ref name="resolve-refund-amount-from-salesforce" />
```

### D.7 — circuit-breaker.xml

Create `src/main/mule/circuit-breaker.xml`. Four sub-flows:
`circuit-breaker-before-call`, `circuit-breaker-on-success`, `circuit-breaker-on-failure`,
`invoke-bedrock-direct-runtime`, and `invoke-mimic-risk-fallback`.

**circuit-breaker-before-call** — reads state, computes `circuitOpen`:

Key logic: circuit is open if status == "OPEN" and the elapsed time since `openedAt` is still
within `circuitCooldownMs`. If cooldown has expired, transition to HALF_OPEN.

```xml
<choice doc:name="Handle Open Circuit Window">
    <!-- Still within cooldown: fail fast -->
    <when expression='#[((vars.circuitState.status default "CLOSED") as String) == "OPEN"
                        and ((vars.circuitNowMs default 0) - (vars.circuitState.openedAt default 0))
                            &lt; (vars.circuitCooldownMs default 60000)]'>
        <set-variable variableName="circuitOpen" value="#[true]" />
        <set-variable variableName="circuitRetryAfter"
                      value='#[max([1,
    (((vars.circuitCooldownMs default 60000)
      - ((vars.circuitNowMs default 0) - (vars.circuitState.openedAt default 0))) / 1000)
    as Number]) as Number]' />
    </when>
    <!-- Cooldown expired: probe -->
    <when expression='#[((vars.circuitState.status default "CLOSED") as String) == "OPEN"]'>
        <set-variable variableName="circuitState"
                      value='#[{status: "HALF_OPEN",
                                failureCount: (vars.circuitState.failureCount default 0),
                                openedAt: (vars.circuitState.openedAt default 0)}]' />
        <os:store key="#[vars.circuitKey]" objectStore="circuitBreakerObjectStore">
            <os:value>#[vars.circuitState]</os:value>
        </os:store>
    </when>
</choice>
```

**circuit-breaker-on-failure** — increment failure count, open if >= threshold:

```xml
<set-variable variableName="circuitState"
              value='#[output application/java ---
do {
    var nextFailureCount = (vars.circuitState.failureCount default 0) + 1
    var shouldOpen = nextFailureCount >= (vars.circuitFailureThreshold default 3)
    ---
    {
        status: if (shouldOpen) "OPEN" else "CLOSED",
        failureCount: nextFailureCount,
        openedAt: if (shouldOpen) (vars.circuitNowMs default 0)
                  else (vars.circuitState.openedAt default 0)
    }
}
]' />
```

**invoke-bedrock-direct-runtime** — calls the Java class via DataWeave `java!`:

```xml
<sub-flow name="invoke-bedrock-direct-runtime">
    <set-variable variableName="bedrockDirectResult"
                  value='#[output application/java ---
java!com::feroz::orchestrator::BedrockDirectInvoker::invoke(
    (p("aws.region") default "us-east-2") as String,
    (p("aws.accessKeyId") default "") as String,
    (p("aws.secretAccessKey") default "") as String,
    (p("bedrock.agentId") default "") as String,
    (p("bedrock.agentAliasId") default "") as String,
    (vars.sessionId default vars.flowId default correlationId) as String,
    (
        if (((vars.intent default "UNKNOWN") as String) == "REFUND_REQUEST")
            "Please process a refund request for order "
            ++ (vars.normalizedOrderNumber default "UNKNOWN")
            ++ " because "
            ++ (vars.normalizedReason default vars.inputText default "Customer requested refund")
            ++ "."
        else
            (vars.inputText default "Help with customer request") as String
    ) as String
)
]' />
    <logger level="INFO"
            message="telemetry stage=BEDROCK_DIRECT_RUNTIME flowId=#[vars.flowId] requestId=#[vars.requestId] success=#[vars.bedrockDirectResult.success default false] decision=#[vars.bedrockDirectResult.decision default 'null']" />
</sub-flow>
```

**invoke-mimic-risk-fallback** — deterministic rules, no network:

```xml
<sub-flow name="invoke-mimic-risk-fallback">
    <set-variable variableName="riskLevel"
                  value='#[output application/java ---
if (startsWith((vars.normalizedOrderNumber default "") as String, "999")) "CRITICAL" else "SAFE"]' />
    <set-variable variableName="riskScore"
                  value='#[output application/java ---
if (((vars.riskLevel default "SAFE") as String) == "CRITICAL") 95 else 14]' />
    <set-variable variableName="bedrockDecisionCandidate"
                  value='#[output application/java ---
if (((vars.intent default "UNKNOWN") as String) != "REFUND_REQUEST") "CLARIFY"
else if (((vars.riskLevel default "SAFE") as String) == "CRITICAL") "ESCALATE"
else "APPROVE"
]' />
    <set-variable variableName="decisionSource" value="mimic" />
    <set-variable variableName="failureClassification" value="BEDROCK_UNAVAILABLE" />
    <set-variable variableName="agentResponse"
                  value='#[output application/java ---
if (((vars.riskLevel default "SAFE") as String) == "CRITICAL")
    "Velocity anomaly detected for this order pattern. Escalating for manual review."
else if (((vars.intent default "UNKNOWN") as String) != "REFUND_REQUEST")
    "I can clarify this request, but no refund action is being taken."
else
    "Refund request appears low risk based on fallback telemetry."
]' />
    <logger level="WARN"
            message="telemetry stage=MIMIC_RISK_FALLBACK flowId=#[vars.flowId] requestId=#[vars.requestId] decision=#[vars.bedrockDecisionCandidate default 'CLARIFY'] riskLevel=#[vars.riskLevel] decisionSource=#[vars.decisionSource]" />
</sub-flow>
```

### D.8 — business-risk-gateway-handler.xml

Create `src/main/mule/business-risk-gateway-handler.xml`. Sub-flow
`handle-gateway-response-or-fallback`. This handles the response from the AI Gateway after
`until-successful` completes.

Two branches:
1. `gatewayNonRetryableError == true` → skip response extraction, go to direct Bedrock fallback
2. Otherwise → extract `decision`, `riskLevel`, `riskScore` from `payload`, set `decisionSource=bedrock`,
   call `circuit-breaker-on-success`

Decision extraction from AI Gateway response:
```xml
<set-variable variableName="bedrockDecisionCandidate"
              value='#[if (upper(((payload.decision default payload.risk.decision
                                   default payload.model.decision default "") as String))
                            == "APPROVE"
                          or upper(((payload.decision default payload.risk.decision
                                     default payload.model.decision default "") as String))
                            == "DENY"
                          or upper(((payload.decision default payload.risk.decision
                                     default payload.model.decision default "") as String))
                            == "CLARIFY"
                          or upper(((payload.decision default payload.risk.decision
                                     default payload.model.decision default "") as String))
                            == "ESCALATE")
    upper(((payload.decision default payload.risk.decision
            default payload.model.decision default "") as String))
else null]' />
```

After extraction, add the success telemetry logger:
```
telemetry stage=BEDROCK_GATEWAY_OK ... shouldIssueCredit decisionSource decisionContractVersion
```

### D.9 — business-risk.xml

Create `src/main/mule/business-risk.xml`. Sub-flow `assess-risk`.

1. Set `scannerUsedFallback=false`, `stageScanner=REMOVED`, `circuitKey="ai-gateway"`
2. Call `circuit-breaker-before-call`
3. Three-branch `<choice>`:

**Branch 1 — circuit open:**
```xml
<when expression="#[vars.circuitOpen default false]">
    <set-variable variableName="stageGateway" value="DEGRADED" />
    <flow-ref name="invoke-bedrock-direct-runtime" />
    <choice doc:name="Handle Direct Bedrock Fallback Result">
        <when expression="#[(vars.bedrockDirectResult.success default false) as Boolean]">
            <!-- copy decision/response/riskLevel/riskScore/decisionSource from bedrockDirectResult -->
        </when>
        <otherwise>
            <flow-ref name="invoke-mimic-risk-fallback" />
        </otherwise>
    </choice>
    <logger level="WARN"
            message="telemetry stage=CIRCUIT_OPEN endpoint=ai-gateway ..." />
</when>
```

**Branch 2 — normal path (not circuit open, not identityMissing):**
```xml
<when expression="#[not vars.identityMissing]">
    <try>
        <set-variable variableName="stageGateway" value="START" />
        <set-variable variableName="gatewayAttempt" value="#[0]" />
        <set-variable variableName="gatewayNonRetryableError" value="#[false]" />
        <ee:transform doc:name="Build Bedrock Proxy Request">
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
    "inputText": "Refund request order " ++ (vars.normalizedOrderNumber default "UNKNOWN")
        ++ " reason " ++ (vars.normalizedReason default vars.inputText)
        ++ ". customerTier=" ++ ((vars.customerProfile.customerTier default "Standard") as String)
        ++ ", churnRisk=" ++ ((vars.customerProfile.churnRisk default "UNKNOWN") as String),
    "systemPrompt": "Return ONLY strict JSON with keys: decision (APPROVE|DENY|ESCALATE|CLARIFY), riskLevel (SAFE|LOW|CRITICAL|UNKNOWN), riskScore (number), response (string). Do not return free text outside JSON.",
    "sessionId": vars.sessionId default vars.flowId default correlationId,
    "enableTrace": true
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>
        <until-successful maxRetries="3" millisBetweenRetries="2000">
            <try>
                <set-variable variableName="gatewayAttempt"
                              value="#[(vars.gatewayAttempt default 0) + 1]" />
                <logger level="WARN"
                        message="telemetry stage=BEDROCK_GATEWAY_RETRY attempt=#[vars.gatewayAttempt] ..." />
                <http:request method="POST"
                              config-ref="aiGatewayRequestConfig"
                              path='#[if ((p("ai-gateway.apiStyle") default "anthropic") as String == "openai")
                                        p("ai-gateway.openaiPath") else p("ai-gateway.anthropicPath")]'
                              responseTimeout="#[(p("ai-gateway.readTimeoutMs") default 30000) as Number]">
                    <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
                </http:request>
                <error-handler>
                    <on-error-continue
                            type="HTTP:BAD_REQUEST,HTTP:UNAUTHORIZED,HTTP:FORBIDDEN">
                        <set-variable variableName="gatewayNonRetryableError" value="#[true]" />
                        <set-variable variableName="gatewayHttpErrorType"
                                      value="#[error.errorType.identifier default 'UNKNOWN']" />
                    </on-error-continue>
                </error-handler>
            </try>
        </until-successful>
        <flow-ref name="handle-gateway-response-or-fallback" />
        <error-handler>
            <on-error-continue type="ANY" logException="true">
                <flow-ref name="circuit-breaker-on-failure" />
                <set-variable variableName="stageGateway" value="DEGRADED" />
                <flow-ref name="invoke-bedrock-direct-runtime" />
                <!-- handle bedrockDirectResult same as Branch 1 -->
                <logger level="ERROR"
                        message="telemetry stage=BEDROCK_GATEWAY_FAIL ..." />
            </on-error-continue>
        </error-handler>
    </try>
</when>
```

**Branch 3 — identityMissing:**
```xml
<otherwise>
    <set-variable variableName="stageGateway" value="SKIPPED" />
</otherwise>
```

### D.10 — business-policy.xml

Create `src/main/mule/business-policy.xml`. Sub-flow `enforce-policy`.

Four sequential `<set-variable>` blocks are the core:

1. **Normalize decision:**
```xml
<set-variable variableName="decision"
              value='#[output application/java ---
if (!isBlank((vars.bedrockDecisionCandidate default "") as String))
    upper((vars.bedrockDecisionCandidate default "CLARIFY") as String)
else if (startsWith((vars.normalizedOrderNumber default "") as String, "999"))
    "ESCALATE"
else if (vars.identityMissing default false)
    "CLARIFY"
else if ((vars.intent default "GENERAL_QUERY") != "REFUND_REQUEST")
    "CLARIFY"
else if (vars.orderIdAmbiguous default false)
    "CLARIFY"
else if (not (vars.hasValidOrderId default false))
    "CLARIFY"
else
    "CLARIFY"
]' />
```

2. **Compute policyRuleMatched:**
```xml
<set-variable variableName="policyRuleMatched"
              value='#[output application/java ---
(((vars.decision default "ESCALATE") as String) == "APPROVE")
and (((vars.intent default "UNKNOWN") as String) == "REFUND_REQUEST")
and not ((vars.orderIdAmbiguous default false) as Boolean)
and ((vars.hasValidOrderId default false) as Boolean)
and not startsWith((vars.normalizedOrderNumber default "") as String, "999")
]' />
```

3. **Gate shouldIssueCredit:**
```xml
<set-variable variableName="shouldIssueCredit"
              value='#[output application/java ---
(upper((vars.decision default "ESCALATE") as String) == "APPROVE")
and ((vars.policyRuleMatched default false) as Boolean)
]' />
```

4. **Compute mutationPayloadComplete and allowMutation:**
```xml
<set-variable variableName="mutationPayloadComplete"
              value='#[output application/java ---
not isBlank((vars.normalizedOrderNumber default "") as String)
and ((vars.normalizedOrderNumber default "UNKNOWN") != "UNKNOWN")
]' />

<set-variable variableName="allowMutation"
              value='#[output application/java ---
(((vars.decision default "ESCALATE") as String) == "APPROVE")
and ((vars.shouldIssueCredit default false) as Boolean)
and not ((vars.identityMissing default false) as Boolean)
and ((vars.mutationPayloadComplete default false) as Boolean)
]' />
```

Add the mutation completeness guard immediately after:
```xml
<choice doc:name="Enforce Mutation Completeness Guard">
    <when expression='#[((vars.decision default "ESCALATE") == "APPROVE")
                        and (vars.shouldIssueCredit default false)
                        and not (vars.mutationPayloadComplete default false)]'>
        <set-variable variableName="shouldIssueCredit" value="#[false]" />
        <set-variable variableName="validationCode" value="#[400]" />
        <set-variable variableName="validationMessage"
                      value="Missing required mutation fields (orderNumber)." />
        <set-variable variableName="failureClassification" value="POLICY_REJECTED" />
        <set-variable variableName="agentResponse" value="#[vars.validationMessage]" />
        <logger level="WARN"
                message="telemetry stage=VALIDATION_FAIL ... reason=mutation-payload-incomplete" />
    </when>
</choice>
```

Close with the DECISION_MODEL telemetry logger:
```
telemetry stage=DECISION_MODEL ... intent ambiguous hasValidOrder hasReason hasCustomerId
policyRuleMatched credit mutationPayloadComplete allowMutation refundAmount amountSource
decisionSource decisionContractVersion decisionPolicyVersion
```

### D.11 — business-mutation.xml

Create `src/main/mule/business-mutation.xml`. Sub-flow `execute-mutation`.

Main `<choice>`:
```
allowMutation AND NOT agentError  --> issue credit
otherwise                         --> SKIPPED
```

**Issue credit branch:**

```xml
<try doc:name="Issue Credit in Service Cloud">
    <set-variable variableName="stageServiceCloud" value="START" />
    <ee:transform doc:name="Build MCP Request">
        <ee:message>
            <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
    "customerId": vars.customerId,
    "orderNumber": vars.normalizedOrderNumber default "UNKNOWN",
    "reason": vars.normalizedReason default vars.inputText,
    "amount": vars.refundAmount,
    "fraudScore": vars.riskScore default -1,
    "orchestratorContext": {
        "fraudScore": vars.riskScore default -1,
        "riskLevel": vars.riskLevel default "UNKNOWN"
    },
    "flowId": vars.flowId default "",
    "requestId": vars.requestId default "",
    "sessionId": vars.sessionId default "",
    "product": vars.refundProduct default "GENERAL_REFUND_CREDIT",
    "amountSource": vars.refundAmountSource default "fallback_random_product"
}]]></ee:set-payload>
        </ee:message>
    </ee:transform>

    <http:request method="POST"
                  config-ref="serviceCloudMcpRequestConfig"
                  path="/tool/issue_credit">
        <http:headers>#[{"Content-Type": "application/json",
                         "x-user-id": vars.userId,
                         "x-flow-id": vars.flowId,
                         "x-request-id": vars.requestId,
                         "x-session-id": vars.sessionId}]</http:headers>
    </http:request>

    <set-variable variableName="creditResult" value="#[payload]" />
    <set-variable variableName="caseId"
                  value='#[output application/java ---
if (isBlank((vars.creditResult.caseId default "") as String)) null
else (vars.creditResult.caseId as String)
]' />
    <set-variable variableName="stageServiceCloud" value="OK" />

    <!-- Invalidate profile cache after mutation -->
    <os:contains key="#[vars.profileCacheKey]"
                 objectStore="profileCacheObjectStore"
                 target="profileCacheEntryExists" />
    <choice>
        <when expression="#[(vars.profileCacheEntryExists default false) as Boolean]">
            <os:remove key="#[vars.profileCacheKey]" objectStore="profileCacheObjectStore" />
        </when>
    </choice>

    <logger level="INFO"
            message="telemetry stage=SERVICE_CLOUD_OK ... status=#[vars.creditResult.status default 'UNKNOWN']" />

    <!-- Classify a rejection from Service Cloud -->
    <choice>
        <when expression='#[upper((vars.creditResult.status default "UNKNOWN") as String) != "SUCCESS"
                            or ((vars.caseId default null) == null)]'>
            <set-variable variableName="shouldIssueCredit" value="#[false]" />
            <set-variable variableName="allowMutation" value="#[false]" />
            <set-variable variableName="failureClassification" value="SERVICE_CLOUD_REJECTED" />
            <set-variable variableName="agentResponse"
                          value='#[output application/java ---
(vars.creditResult.message default vars.agentResponse
 default "Service Cloud rejected the credit mutation.") as String]' />
            <logger level="WARN" message="telemetry stage=SERVICE_CLOUD_REJECTED ..." />
        </when>
    </choice>

    <error-handler>
        <on-error-continue type="ANY" logException="true">
            <set-variable variableName="stageServiceCloud" value="FAIL" />
            <set-variable variableName="httpStatus" value="#[200]" />
            <set-variable variableName="agentError" value="#[true]" />
            <set-variable variableName="caseId" value="#[null]" />
            <set-variable variableName="decision" value="CLARIFY" />
            <set-variable variableName="shouldIssueCredit" value="#[false]" />
            <set-variable variableName="allowMutation" value="#[false]" />
            <set-variable variableName="failureClassification" value="SERVICE_CLOUD_UNAVAILABLE" />
            <set-variable variableName="agentResponse"
                          value='#[output application/java ---
(vars.agentResponse default "I could not complete the credit mutation right now.
 Please retry or confirm details.") as String]' />

            <!-- Write to DLQ -->
            <os:store key='#[output application/java --- "dlq::" ++ ((vars.requestId default correlationId) as String)]'
                      objectStore="workflowDlqObjectStore">
                <os:value><![CDATA[#[output application/java ---
{
    timestamp: now() as String,
    flowId: vars.flowId default "",
    requestId: vars.requestId default "",
    sessionId: vars.sessionId default "",
    userId: vars.userId default "",
    orderNumber: vars.normalizedOrderNumber default "UNKNOWN",
    stageServiceCloud: vars.stageServiceCloud default "FAIL",
    compensationNeeded: true,
    errorType: error.errorType.identifier default "UNKNOWN",
    errorMessage: error.description default "Service Cloud mutation failed",
    payload: payload
}]]]></os:value>
            </os:store>

            <!-- Increment DLQ failure counter -->
            <os:contains key="dlq.failure.count"
                         objectStore="dlqMetricsObjectStore"
                         target="dlqCountExistsOnWrite" />
            <choice>
                <when expression="#[(vars.dlqCountExistsOnWrite default false) as Boolean]">
                    <os:retrieve key="dlq.failure.count"
                                 objectStore="dlqMetricsObjectStore"
                                 target="dlqFailureCountOnWrite" />
                </when>
                <otherwise>
                    <set-variable variableName="dlqFailureCountOnWrite" value="#[0]" />
                </otherwise>
            </choice>
            <os:store key="dlq.failure.count" objectStore="dlqMetricsObjectStore">
                <os:value>#[((vars.dlqFailureCountOnWrite default 0) as Number) + 1]</os:value>
            </os:store>

            <logger level="ERROR"
                    message="telemetry stage=SERVICE_CLOUD_FAIL ... action=return-without-caseid" />
        </on-error-continue>
    </error-handler>
</try>
```

**Checkpoint D.11:** With `data-cloud-sapi` and `service-cloud-mcp` running locally (from
Exercises 2 and 3), send:

```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: U123456" \
  -d '{
    "inputText": "I want a refund for order ORD-1001",
    "userId": "U123456",
    "requestId": "req-exercise-d11",
    "sessionId": "sess-001",
    "structured": {"orderNumber": "ORD-1001", "reason": "item arrived damaged"}
  }' | python3 -m json.tool
```

Expected (with Bedrock unavailable, mimic fallback active):
- `"decision"` is `APPROVE` or `CLARIFY` depending on Salesforce lookup
- `"stageStatus.dataCloud"` is `OK` or `FAIL`
- `"stageStatus.gateway"` is `DEGRADED`
- `"decisionSource"` is `"mimic"` or `"bedrock"`

---

## Part E — DataWeave Library Files

### E.1 — sanitize.dwl

Create `src/main/resources/dw/sanitize.dwl`:

```
%dw 2.0

fun sanitizeOrderNumberForSoqlLike(value: Any): String =
    upper(
        trim(
            ((value default "") as String)
                replace /[^A-Za-z0-9 -]/ with ""
        )
    )
```

This is imported in `business-resolution.xml` via `import dw::sanitize` (the Mule runtime resolves
`dw/sanitize.dwl` from `src/main/resources`).

### E.2 — policy-rules.dwl

Create `src/main/resources/dw/policy-rules.dwl`:

```
%dw 2.0

fun computePolicyRuleMatched(decision: Any, intent: Any, orderIdAmbiguous: Any,
                              hasValidOrderId: Any, hasReason: Any, hasCustomerId: Any): Boolean =
    (((decision default "ESCALATE") as String) == "APPROVE")
    and (((intent default "UNKNOWN") as String) == "REFUND_REQUEST")
    and not ((orderIdAmbiguous default false) as Boolean)
    and ((hasValidOrderId default false) as Boolean)
    and ((hasReason default false) as Boolean)
    and ((hasCustomerId default false) as Boolean)

fun computeAllowMutation(decision: Any, shouldIssueCredit: Any,
                          identityMissing: Any, mutationPayloadComplete: Any): Boolean =
    (((decision default "ESCALATE") as String) == "APPROVE")
    and ((shouldIssueCredit default false) as Boolean)
    and not ((identityMissing default false) as Boolean)
    and ((mutationPayloadComplete default false) as Boolean)
```

### E.3 — risk-assessment.dwl

Create `src/main/resources/dw/risk-assessment.dwl`:

```
%dw 2.0

fun normalizeDecisionCandidate(payload: Any): Null | String =
    do {
        var rawDecision = upper(((payload.decision default payload.risk.decision
                                  default payload.model.decision default "") as String))
        ---
        if (rawDecision == "APPROVE" or rawDecision == "DENY"
            or rawDecision == "CLARIFY" or rawDecision == "ESCALATE")
            rawDecision
        else
            null
    }

fun normalizeRiskLevel(payload: Any): String =
    do {
        var rawRiskLevel = upper(((payload.riskLevel default payload.risk.riskLevel
                                   default payload.model.riskLevel default "") as String))
        ---
        if (rawRiskLevel == "SAFE" or rawRiskLevel == "LOW"
            or rawRiskLevel == "CRITICAL" or rawRiskLevel == "UNKNOWN")
            rawRiskLevel
        else
            "UNKNOWN"
    }

fun normalizeRiskScore(payload: Any): Number =
    do {
        var rawRiskScore = payload.riskScore default payload.risk.riskScore
                           default payload.model.riskScore default null
        ---
        if (rawRiskScore is Number)
            rawRiskScore as Number
        else if (!isBlank((rawRiskScore default "") as String)
                 and (((rawRiskScore as String) matches /^-?\d+(\.\d+)?$/) default false))
            (rawRiskScore as Number)
        else
            -1
    }
```

### E.4 — response-envelope.dwl

Create `src/main/resources/dw/response-envelope.dwl`:

```
%dw 2.0

fun buildFinalResponseEnvelope(vars: Any): Object =
    do {
        var baseResponse = vars.agentResponse default "I was unable to process your request."
        ---
        {
            response: if (((vars.caseId default null) != null)
                          and (not isBlank((vars.caseId default "") as String)))
                baseResponse ++ "\n\nCase Reference: " ++ (vars.caseId as String)
            else
                baseResponse,
            metadata: {
                decision: vars.decision default "ESCALATE",
                shouldIssueCredit: vars.shouldIssueCredit default false,
                riskLevel: vars.riskLevel default "UNKNOWN",
                riskScore: vars.riskScore default -1,
                intent: vars.intent default "UNKNOWN",
                orderNumber: vars.orderNumber default "UNKNOWN",
                orderIdAmbiguous: vars.orderIdAmbiguous default false,
                hasValidOrderId: vars.hasValidOrderId default false,
                flowId: vars.flowId default "",
                requestId: vars.requestId default "",
                caseId: vars.caseId default null,
                sessionId: vars.sessionId default "",
                usedFallback: vars.scannerUsedFallback default false,
                agentError: vars.agentError default false,
                contractVersion: vars.contractVersion default "1.2",
                decisionSource: vars.decisionSource default "policy",
                decisionContractVersion: vars.decisionContractVersion default "bedrock-v1",
                decisionPolicyVersion: vars.decisionPolicyVersion default "orchestrator-policy-v2",
                failureClassification: vars.failureClassification default null,
                refundAmount: vars.refundAmount default 0,
                refundAmountSource: vars.refundAmountSource default "unresolved_salesforce",
                gates: {
                    allowMutation: vars.allowMutation default false,
                    hasValidOrder: vars.hasValidOrderId default false,
                    hasReason: vars.hasReason default false,
                    hasCustomerId: vars.hasCustomerId default false,
                    policyRuleMatched: vars.policyRuleMatched default false
                },
                stageStatus: {
                    dataCloud: vars.stageDataCloud default "NOT_RUN",
                    scanner: vars.stageScanner default "NOT_RUN",
                    gateway: vars.stageGateway default "NOT_RUN",
                    serviceCloud: vars.stageServiceCloud default "NOT_RUN"
                },
                validation: if ((vars.validationCode default null) != null)
                    {
                        statusCode: vars.validationCode,
                        message: vars.validationMessage default ""
                    }
                else
                    null
            }
        }
    }
```

---

## Part F — Shared and Environment Config YAML

### F.1 — shared-config.yaml

Create `src/main/resources/shared-config.yaml` (local dev defaults — all hosts point to localhost):

```yaml
sfdc:
  username: "local-dev"
  password: "local-dev"
  token: "local-dev"
  url: "https://login.salesforce.com"

data-cloud:
  host: "localhost"

scanner:
  enabled: "false"
  host: "localhost"
  path: "/api/v1/agent/chat"
  authHeader: "none"
  connectTimeoutMs: "10000"
  readTimeoutMs: "30000"

ai-gateway:
  host: "localhost"
  openaiPath: "/llmproxy2/chat/completions"
  anthropicPath: "/llmproxy/v1/messages"
  apiStyle: "openai"
  clientId: "local-dev"
  clientSecret: "local-dev"
  connectTimeoutMs: "10000"
  readTimeoutMs: "30000"

service-cloud-mcp:
  host: "localhost"

bedrock-proxy:
  host: "localhost"
  path: "/api/v1/agent/chat"
  connectTimeoutMs: "10000"
  readTimeoutMs: "30000"

http:
  pool:
    maxConnections: "10"
    connectionIdleTimeoutMs: "30000"

https:
  listener:
    port: "8082"

tls:
  keystore:
    path: "certs/localhost-keystore.jks"
    type: "JKS"
    alias: "localhost"
    password: "changeit"
    keyPassword: "changeit"
  truststore:
    path: "certs/localhost-truststore.jks"
    type: "JKS"
    password: "changeit"

aws:
  region: "us-east-2"
  accessKeyId: ""
  secretAccessKey: ""

bedrock:
  agentId: ""
  agentAliasId: ""
```

### F.2 — dev-config.yaml

Create `src/main/resources/dev-config.yaml` (CloudHub 2.0 host overrides from Module 4):

```yaml
data-cloud:
  host: "data-cloud-sapi-835dgu.wdob74.usa-e2.cloudhub.io"

ai-gateway:
  host: "agenticenterprisetraining-small-835dgu.wdob74.usa-e2.cloudhub.io"
  openaiPath: "/llmproxy2/chat/completions"
  anthropicPath: "/llmproxy/v1/messages"
  apiStyle: "openai"
  clientId: "local-dev"
  clientSecret: "local-dev"
  connectTimeoutMs: "10000"
  readTimeoutMs: "30000"

service-cloud-mcp:
  host: "service-cloud-mcp-835dgu.wdob74.usa-e2.cloudhub.io"

bedrock-proxy:
  host: "agenticenterprisetraining-small-835dgu.wdob74.usa-e2.cloudhub.io"
  path: "/api/v1/agent/chat"
  connectTimeoutMs: "10000"
  readTimeoutMs: "30000"

http:
  pool:
    maxConnections: "10"
    connectionIdleTimeoutMs: "30000"

https:
  listener:
    port: "8082"

tls:
  keystore:
    path: "certs/localhost-keystore.jks"
    type: "JKS"
    alias: "localhost"
    password: "changeit"
    keyPassword: "changeit"
  truststore:
    path: "certs/localhost-truststore.jks"
    type: "JKS"
    password: "changeit"
```

### F.3 — config.yaml (secure references only)

Create `src/main/resources/config.yaml`:

```yaml
# Secrets reference the Mule Secure Configuration Properties module.
# Plain-text values here are a teaching example only.
sfdc:
  username: "${sfdc.username}"
  password: "${secure::sfdc.password}"
  token: "${secure::sfdc.token}"
  url: "${sfdc.url}"

scanner:
  authHeader: "${secure::scanner.authHeader}"

ai-gateway:
  clientSecret: "${secure::ai-gateway.clientSecret}"

otel:
  logs:
    authHeader: "${secure::otel.logs.authHeader}"
```

---

## Part G — BedrockDirectInvoker Java Class

The `BedrockDirectInvoker` Java class was covered in detail in Module 4. Here you wire it into
the Mule flow using the DataWeave `java!` module.

### G.1 — Copy the class

Create `src/main/java/com/feroz/orchestrator/BedrockDirectInvoker.java` with the following content:

```java
package com.feroz.orchestrator;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockagentruntime.BedrockAgentRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockagentruntime.model.InvokeAgentRequest;
import software.amazon.awssdk.services.bedrockagentruntime.model.InvokeAgentResponseHandler;
import software.amazon.awssdk.services.bedrockagentruntime.model.FunctionParameter;
import software.amazon.awssdk.services.bedrockagentruntime.model.InvocationInputMember;
import software.amazon.awssdk.services.bedrockagentruntime.model.ReturnControlPayload;

public final class BedrockDirectInvoker {
    private BedrockDirectInvoker() {}

    public static Map<String, Object> invoke(
            String region, String accessKeyId, String secretAccessKey,
            String agentId, String agentAliasId, String sessionId, String inputText) {
        Map<String, Object> out = new HashMap<>();
        out.put("success", false);
        out.put("decision", null);
        out.put("response", "");
        out.put("riskLevel", "UNKNOWN");
        out.put("riskScore", -1);
        try {
            if (agentId == null || agentId.trim().isEmpty() || agentAliasId == null || agentAliasId.trim().isEmpty()) {
                out.put("error", "Missing Bedrock agentId/agentAliasId");
                return out;
            }
            BedrockAgentRuntimeAsyncClient client = BedrockAgentRuntimeAsyncClient.builder()
                    .region(Region.of(region))
                    .credentialsProvider(StaticCredentialsProvider.create(
                            AwsBasicCredentials.create(accessKeyId, secretAccessKey)))
                    .build();
            String finalText = "";
            Exception finalError = null;
            for (int attempt = 1; attempt <= 2; attempt++) {
                try {
                    finalText = invokeAgent(client, agentId, agentAliasId, sessionId, inputText, out);
                    finalError = null;
                    break;
                } catch (Exception e) {
                    finalError = e;
                    out.put("lastAttemptError", e.getMessage());
                    if (attempt == 1) { try { Thread.sleep(250L); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); break; } }
                }
            }
            if (finalError != null) throw finalError;
            out.put("rawPreview", finalText.length() > 500 ? finalText.substring(0, 500) : finalText);
            // Extract structured fields from agent response text
            Matcher m = Pattern.compile("\"decision\"\\s*:\\s*\"(APPROVE|DENY|ESCALATE|CLARIFY)\"", Pattern.CASE_INSENSITIVE).matcher(finalText);
            if (m.find()) out.put("decision", m.group(1).toUpperCase());
            Matcher rm = Pattern.compile("\"response\"\\s*:\\s*\"([^\"]+)\"", Pattern.CASE_INSENSITIVE).matcher(finalText);
            if (rm.find()) out.put("response", rm.group(1)); else out.put("response", finalText);
            String upper = finalText.toUpperCase();
            if (out.get("decision") == null) {
                if (upper.contains("RISK LEVEL: CRITICAL") || upper.contains("CRITICAL FRAUD RISK") || upper.contains("FRAUD RISK DETECTED") || (upper.contains("CRITICAL") && upper.contains("ESCALAT"))) {
                    out.put("decision", "ESCALATE");
                } else if (upper.contains("RISK LEVEL: SAFE") || upper.contains("RISK LEVEL: LOW") || upper.contains("APPROVE") || upper.contains("REFUND WILL BE ISSUED")) {
                    out.put("decision", "APPROVE");
                } else if (upper.contains("CLARIFY") || upper.contains("ONLY ASSIST WITH REFUND REQUESTS")) {
                    out.put("decision", "CLARIFY");
                } else if (upper.contains("UNABLE TO PROCESS") || upper.contains("STOP AND ESCALATE")) {
                    out.put("decision", "ESCALATE");
                } else if (Boolean.TRUE.equals(out.get("returnControlRequired"))) {
                    out.put("decision", "CLARIFY");
                }
            }
            Matcher rl = Pattern.compile("\\b(SAFE|LOW|CRITICAL|UNKNOWN)\\b").matcher(upper);
            if (rl.find()) out.put("riskLevel", rl.group(1));
            Matcher rs = Pattern.compile("\"riskScore\"\\s*:\\s*(-?\\d+)", Pattern.CASE_INSENSITIVE).matcher(finalText);
            if (rs.find()) { try { out.put("riskScore", Integer.parseInt(rs.group(1))); } catch (NumberFormatException ignored) {} }
            out.put("success", out.get("decision") != null);
            return out;
        } catch (Exception e) {
            out.put("error", e.getClass().getSimpleName() + ": " + e.getMessage());
            return out;
        }
    }

    private static String invokeAgent(BedrockAgentRuntimeAsyncClient client,
            String agentId, String agentAliasId, String sessionId, String inputText,
            Map<String, Object> out) throws Exception {
        StringBuilder text = new StringBuilder();
        AtomicReference<Throwable> streamError = new AtomicReference<>();
        AtomicReference<ReturnControlPayload> returnControl = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        InvokeAgentResponseHandler handler = InvokeAgentResponseHandler.builder()
                .onError(e -> { streamError.set(e); latch.countDown(); })
                .onComplete(latch::countDown)
                .subscriber(InvokeAgentResponseHandler.Visitor.builder()
                        .onChunk(c -> { if (c.bytes() != null) text.append(c.bytes().asUtf8String()); })
                        .onReturnControl(returnControl::set)
                        .build())
                .build();
        client.invokeAgent(InvokeAgentRequest.builder()
                .agentId(agentId).agentAliasId(agentAliasId)
                .sessionId(sessionId).inputText(inputText).enableTrace(true).build(), handler);
        if (!latch.await(75, TimeUnit.SECONDS)) throw new RuntimeException("invokeAgent timed out");
        client.close();
        if (streamError.get() != null) throw new RuntimeException("stream error: " + streamError.get().getMessage(), streamError.get());
        if (text.length() == 0 && returnControl.get() != null) {
            out.put("returnControlRequired", true);
            List<Map<String, String>> inputs = new ArrayList<>();
            for (InvocationInputMember input : returnControl.get().invocationInputs()) {
                if (input.functionInvocationInput() == null) continue;
                for (FunctionParameter p : input.functionInvocationInput().parameters()) {
                    Map<String, String> entry = new HashMap<>();
                    entry.put("actionGroup", input.functionInvocationInput().actionGroup());
                    entry.put("function", input.functionInvocationInput().function());
                    entry.put("name", p.name()); entry.put("value", p.value());
                    inputs.add(entry);
                }
            }
            out.put("returnControlInputs", inputs);
            out.put("response", inputs.isEmpty() ? "Agent requested additional context." : "Agent requested tool execution.");
            return "";
        }
        return text.toString().trim();
    }
}
```

The class declares `package com.feroz.orchestrator;` — confirm this matches your directory structure.

### G.2 — Verify the DataWeave invocation

In `circuit-breaker.xml`, the call is:

```
java!com::feroz::orchestrator::BedrockDirectInvoker::invoke(
    region, accessKeyId, secretAccessKey,
    agentId, agentAliasId,
    sessionId, inputText
)
```

The `java!` prefix tells the DataWeave runtime to treat this as a static Java method call.
The return type is `Map<String, Object>` — DataWeave reads it as an object with dot-notation access
(`vars.bedrockDirectResult.success`, `vars.bedrockDirectResult.decision`, etc.).

### G.3 — Confirm compilation

In Anypoint Studio, right-click the project > **Run As > Mule Application**. Watch the console for
any `ClassNotFoundException` or `NoSuchMethodException`. If the bedrockagentruntime dependency
resolved correctly in Part A, the class will compile and the invocation will work.

If `agentId` or `agentAliasId` is blank (as in `shared-config.yaml`), `BedrockDirectInvoker.invoke`
returns `{success: false, error: "Missing Bedrock agentId/agentAliasId"}` without making a network
call. This is the expected local-dev behavior — the mimic fallback takes over.

---

## Part H — ai-orchestrator-papi.xml (APIkit + health endpoints + DLQ monitor)

Create `src/main/mule/ai-orchestrator-papi.xml`. This file wires the RAML spec to the internal
endpoint, adds health probes, and starts the DLQ monitor scheduler.

Key flows:

**APIkit router flow:**
```xml
<flow name="ai-orchestrator-apikit-main">
    <http:listener config-ref="httpListenerConfig" path="/apikit/*" allowedMethods="POST" />
    <apikit:router config-ref="ai-orchestrator-apikit-config" />
</flow>

<flow name="post:\\orchestrate:ai-orchestrator-apikit-config">
    <http:request method="POST"
                  config-ref="localOrchestratorRequestConfig"
                  path="/api/orchestrate">
        <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
    </http:request>
</flow>
```

**MCP tool endpoint** (for Bedrock to call as a tool):
```xml
<flow name="mcp-assess-refund-request-flow">
    <http:listener config-ref="httpListenerConfig"
                   path="/mcp/tool/assess_refund_request"
                   allowedMethods="POST" />
    <set-variable variableName="httpStatus" value="#[200]" />
    <http:request method="POST"
                  config-ref="localOrchestratorRequestConfig"
                  path="/api/orchestrate">
        <http:headers>#[{
            "Content-Type": "application/json",
            "x-user-id": (attributes.headers."x-user-id" default payload.userId default ""),
            "x-flow-id": (attributes.headers."x-flow-id" default payload.flowId default ""),
            "x-request-id": (attributes.headers."x-request-id" default payload.requestId default ""),
            "x-session-id": (attributes.headers."x-session-id" default payload.sessionId default "")
        }]</http:headers>
    </http:request>
</flow>
```

**Health endpoint:**
```xml
<flow name="health-flow">
    <http:listener config-ref="httpListenerConfig" path="/health" allowedMethods="GET" />
    <set-payload value='#[output application/json --- {status: "ok", app: "ai-orchestrator"}]' />
</flow>
```

**Readiness endpoint** (parallel probes to data-cloud and service-cloud):
```xml
<flow name="ready-health-flow">
    <http:listener config-ref="httpListenerConfig" path="/health/ready" allowedMethods="GET" />
    <set-variable variableName="httpStatus" value="#[200]" />
    <scatter-gather>
        <route>
            <try>
                <http:request method="GET" config-ref="readinessDataCloudRequestConfig"
                              path="/health" responseTimeout="2000" />
                <set-payload value='#[{dataCloud: if ((attributes.statusCode default 500) as Number < 500) "UP" else "DEGRADED"}]' />
                <error-handler>
                    <on-error-continue type="ANY" logException="false">
                        <set-payload value='#[{dataCloud: "UNKNOWN"}]' />
                    </on-error-continue>
                </error-handler>
            </try>
        </route>
        <route>
            <try>
                <http:request method="GET" config-ref="readinessServiceCloudRequestConfig"
                              path="/health" responseTimeout="2000" />
                <set-payload value='#[{serviceCloud: if ((attributes.statusCode default 500) as Number < 500) "UP" else "DEGRADED"}]' />
                <error-handler>
                    <on-error-continue type="ANY" logException="false">
                        <set-payload value='#[{serviceCloud: "UNKNOWN"}]' />
                    </on-error-continue>
                </error-handler>
            </try>
        </route>
    </scatter-gather>
    <set-variable variableName="readyDataCloud"
                  value='#[payload."0".payload.dataCloud default "UNKNOWN"]' />
    <set-variable variableName="readyServiceCloud"
                  value='#[payload."1".payload.serviceCloud default "UNKNOWN"]' />
    <set-payload value='#[output application/json ---
{
  status: "ready",
  dependencies: {
    dataCloud: vars.readyDataCloud default "UNKNOWN",
    serviceCloud: vars.readyServiceCloud default "UNKNOWN"
  }
}]' />
</flow>
```

**DLQ monitor:**
```xml
<flow name="dlq-monitor-flow">
    <scheduler>
        <scheduling-strategy>
            <fixed-frequency frequency="5" timeUnit="MINUTES" />
        </scheduling-strategy>
    </scheduler>
    <os:contains key="dlq.failure.count"
                 objectStore="dlqMetricsObjectStore"
                 target="dlqCountExists" />
    <choice>
        <when expression="#[(vars.dlqCountExists default false) as Boolean]">
            <os:retrieve key="dlq.failure.count"
                         objectStore="dlqMetricsObjectStore"
                         target="dlqFailureCount" />
        </when>
        <otherwise>
            <set-variable variableName="dlqFailureCount" value="#[0]" />
        </otherwise>
    </choice>
    <choice>
        <when expression="#[(vars.dlqFailureCount default 0) as Number > 0]">
            <logger level="ERROR"
                    message="telemetry stage=DLQ_ALERT failuresLastWindow=#[vars.dlqFailureCount] action=manual-review-required" />
            <os:store key="dlq.failure.count" objectStore="dlqMetricsObjectStore">
                <os:value>#[0]</os:value>
            </os:store>
        </when>
    </choice>
</flow>
```

---

## Part I — End-to-End Verification

Start all four apps. Run the following curl commands in order.

### I.1 — Health check
```bash
curl -s http://localhost:8081/health
```
Expected: `{"status":"ok","app":"ai-orchestrator"}`

### I.2 — Readiness check
```bash
curl -s http://localhost:8081/health/ready | python3 -m json.tool
```
Expected: `{"status":"ready","dependencies":{"dataCloud":"UP","serviceCloud":"UP"}}`

### I.3 — Missing identity (Stage 1 short-circuit)
```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"inputText":"refund order ORD-999","requestId":"test-001"}' | python3 -m json.tool
```
Expected:
```json
{
  "metadata": {
    "decision": "CLARIFY",
    "validation": {"statusCode": 400, "message": "Missing trusted identity..."},
    "stageStatus": {"dataCloud": "NOT_RUN", "gateway": "NOT_RUN"}
  }
}
```

### I.4 — Duplicate request detection
```bash
# First request
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: U001" \
  -d '{"inputText":"refund ORD-1001","userId":"U001","requestId":"req-dedup-test"}' \
  | python3 -m json.tool

# Second request — same requestId
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: U001" \
  -d '{"inputText":"refund ORD-1001","userId":"U001","requestId":"req-dedup-test"}' \
  | python3 -m json.tool
```
Expected on second call: `"failureClassification": "DUPLICATE_REQUEST"`, all stageStatus `SKIPPED`.

### I.5 — 999-prefix escalation (mimic fallback path)
```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: U002" \
  -d '{
    "inputText": "I need a refund for order 999-100",
    "userId": "U002",
    "requestId": "req-escalate-test",
    "structured": {"orderNumber": "999-100", "reason": "wrong item"}
  }' | python3 -m json.tool
```
Expected: `"decision": "ESCALATE"`, `"riskLevel": "CRITICAL"`, `"riskScore": 95`,
`"decisionSource": "mimic"` (unless Bedrock is live).

### I.6 — Happy path (requires Bedrock and Service Cloud live)
```bash
curl -s -X POST http://localhost:8081/api/orchestrate \
  -H "Content-Type: application/json" \
  -H "x-user-id: U003" \
  -d '{
    "userId": "U003",
    "requestId": "req-happy-001",
    "sessionId": "sess-happy-001",
    "inputText": "I want to return order ORD-2001 because it arrived damaged",
    "structured": {
      "orderNumber": "ORD-2001",
      "reason": "item arrived damaged",
      "intent": "REFUND_REQUEST"
    }
  }' | python3 -m json.tool
```
Expected (with all services live):
```json
{
  "response": "Your refund has been approved.\n\nCase Reference: CS-XXXXXXXX",
  "metadata": {
    "decision": "APPROVE",
    "shouldIssueCredit": true,
    "gates": {"allowMutation": true},
    "stageStatus": {"dataCloud": "OK", "gateway": "OK", "serviceCloud": "OK"},
    "decisionSource": "bedrock",
    "refundAmountSource": "salesforce_query"
  }
}
```

### I.7 — Profile cache hit (verify 5-minute TTL)
```bash
# Send the same userId twice in rapid succession
for i in 1 2; do
  curl -s -X POST http://localhost:8081/api/orchestrate \
    -H "Content-Type: application/json" \
    -H "x-user-id: U004" \
    -d '{"userId":"U004","requestId":"req-cache-'$i'","inputText":"status of ORD-3001"}' \
    | python3 -m json.tool | grep stageDataCloud
done
```
Expected: first call shows `"dataCloud": "OK"`, second shows `"dataCloud": "CACHE_HIT"`.

---

## Key Config Reference

| Property | Where set | Default |
|---|---|---|
| HTTP listener port | `global-config.xml` | `8081` |
| HTTPS listener port | `shared-config.yaml` | `8082` |
| `requestDedupeObjectStore` TTL | `global-config.xml` | 30 min |
| `profileCacheObjectStore` TTL | `global-config.xml` | 5 min |
| `workflowDlqObjectStore` TTL | `global-config.xml` | 7 days |
| `circuitBreakerObjectStore` TTL | none (persists until eviction) | — |
| Circuit failure threshold | `initialize-orchestration-context` | `3` |
| Circuit cooldown | `initialize-orchestration-context` | `60 000 ms` |
| AI Gateway path (OpenAI style) | `shared-config.yaml` | `/llmproxy2/chat/completions` |
| AI Gateway path (Anthropic style) | `shared-config.yaml` | `/llmproxy/v1/messages` |
| `ai-gateway.apiStyle` | `shared-config.yaml` | `openai` |
| `scanner.enabled` | `shared-config.yaml` | `false` |
| DLQ monitor frequency | `ai-orchestrator-papi.xml` | every 5 min |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App fails to start: `Cannot load class com.feroz.orchestrator.BedrockDirectInvoker` | Java source not compiled | Confirm directory is `src/main/java/com/feroz/orchestrator/` and the package declaration matches |
| `ClassNotFoundException: software.amazon.awssdk...` | `bedrockagentruntime` dependency missing or unresolved | Re-check pom.xml dependency and run `mvn dependency:resolve` |
| `stageDataCloud: FAIL` on every request | `data-cloud-sapi` not running or wrong host | Confirm `data-cloud.host` in `dev-config.yaml` and that `data-cloud-sapi` is up on port 8083 |
| `decision: CLARIFY` with `failureClassification: SALESFORCE_UNAVAILABLE` | Salesforce credentials not set or org unreachable | Set `sfdc.username/password/token` in `shared-config.yaml` or use secure properties |
| `decision: CLARIFY` with `failureClassification: POLICY_REJECTED` and message about orderNumber | No Opportunity record matched the SOQL query | Create an Opportunity in Salesforce with a `Name` containing the test order number |
| `stageGateway: DEGRADED` on every call | AI Gateway host unreachable or client_id/client_secret wrong | Update `ai-gateway.host`, `clientId`, `clientSecret` in `dev-config.yaml`; check Module 4 AI Gateway setup |
| `decisionSource: mimic` instead of `bedrock` | `aws.accessKeyId` or `agentId` blank | Set `BEDROCK_AGENT_ID`, `BEDROCK_AGENT_ALIAS_ID`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` env vars |
| `stageServiceCloud: FAIL` and entry in DLQ | `service-cloud-mcp` not running or returning non-SUCCESS | Confirm `service-cloud-mcp` is up on port 8084 and `/tool/issue_credit` returns `{"status":"SUCCESS","caseId":"..."}` |
| Second request with same `requestId` does NOT return DUPLICATE | `requestDedupeObjectStore` in-memory store reset on restart | Use persistent store (default) — confirm `persistent="true"` in `global-config.xml` |
| Port 8081 already in use on startup | Another Mule app or process on 8081 | Stop competing app or change listener port |
| `Cannot find module 'dw::sanitize'` | `sanitize.dwl` not in `src/main/resources/dw/` | Create the file at the exact path |
