> **Missed earlier exercises? Catch up first:**
> ```bash
> python setup/catchup.py --student student.json --checkpoint 5
> ```
> Runs CP1–CP4 and CP5 (downloads data-cloud-sapi + service-cloud-mcp JARs, starts on :8083 and :8084).
> Then continue at [Part A](#part-a) below — both apps will already be running.

# Exercise 5 — System APIs: data-cloud-sapi and service-cloud-mcp

## Objective

Build two System API applications from scratch:

1. **`data-cloud-sapi`** — reads unified customer profile from Salesforce Data Cloud and returns grounding context
2. **`service-cloud-mcp`** — executes refund actions in Salesforce Service Cloud via a tool contract

By the end of this exercise both apps will be running and responding correctly to the verification requests listed at the end of each part.

## Background

System APIs sit at the bottom of the API-led connectivity stack. They own the connection to a single system of record and expose a stable interface that hides all vendor-specific details from the layers above.

`data-cloud-sapi` serves grounding data. When `ai-orchestrator` calls it before constructing a Bedrock prompt, the response fields (`customerTier`, `churnRisk`, `recommendedAction`) become part of the model's context.

`service-cloud-mcp` executes refund actions. It uses the Model Context Protocol (MCP) tool convention — a fixed endpoint with a defined input/output schema — so any orchestrator or AI model that knows the contract can call it without knowing that Salesforce is the backing system.

---

## Part A — data-cloud-sapi: Project Setup and pom.xml

### A.1 — Create the project

In Anypoint Studio, create a new Mule Project:

- Name: `data-cloud-sapi`
- Mule Runtime: `4.11.3`
- Do not generate a default flow

### A.2 — Parent pom.xml

Create `parent/pom.xml` in the project root. This defines connector versions for the entire agent network:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
             https://maven.apache.org/maven-v4_0_0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{YOUR_ORG_ID}</groupId>
    <artifactId>agent-network-parent</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>

    <properties>
        <app.runtime>4.11.3</app.runtime>
        <mule.maven.plugin.version>4.7.0</mule.maven.plugin.version>
        <munit.version>3.7.1</munit.version>
        <mule.http.connector.version>1.9.3</mule.http.connector.version>
        <mule.objectstore.connector.version>1.2.3</mule.objectstore.connector.version>
        <mule.sdc.connector.version>1.4.0</mule.sdc.connector.version>
        <mule.secure.properties.version>1.2.7</mule.secure.properties.version>
        <mule.apikit.module.version>1.10.0</mule.apikit.module.version>
        <mule.tracing.module.version>1.2.0</mule.tracing.module.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.mule.connectors</groupId>
                <artifactId>mule-http-connector</artifactId>
                <version>${mule.http.connector.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
            <dependency>
                <groupId>org.mule.connectors</groupId>
                <artifactId>mule-objectstore-connector</artifactId>
                <version>${mule.objectstore.connector.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
            <dependency>
                <groupId>com.mulesoft.connectors</groupId>
                <artifactId>mule4-sdc-connector</artifactId>
                <version>${mule.sdc.connector.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
            <dependency>
                <groupId>com.mulesoft.modules</groupId>
                <artifactId>mule-secure-configuration-property-module</artifactId>
                <version>${mule.secure.properties.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
            <dependency>
                <groupId>org.mule.modules</groupId>
                <artifactId>mule-apikit-module</artifactId>
                <version>${mule.apikit.module.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
            <dependency>
                <groupId>org.mule.modules</groupId>
                <artifactId>mule-tracing-module</artifactId>
                <version>${mule.tracing.module.version}</version>
                <classifier>mule-plugin</classifier>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <repositories>
        <repository>
            <id>anypoint-exchange-v3</id>
            <name>Anypoint Exchange</name>
            <url>https://maven.anypoint.mulesoft.com/api/v3/maven</url>
        </repository>
        <repository>
            <id>mulesoft-releases</id>
            <url>https://repository.mulesoft.org/releases/</url>
        </repository>
    </repositories>
</project>
```

Replace `{YOUR_ORG_ID}` with your Anypoint Platform organization ID (found in Access Management > Organization).

### A.3 — Application pom.xml

The application `pom.xml` inherits from the parent and declares only connector references (versions come from parent):

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
             https://maven.apache.org/maven-v4_0_0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>{YOUR_ORG_ID}</groupId>
        <artifactId>agent-network-parent</artifactId>
        <version>1.0.0</version>
        <relativePath>parent/pom.xml</relativePath>
    </parent>
    <groupId>{YOUR_ORG_ID}</groupId>
    <artifactId>data-cloud-sapi</artifactId>
    <version>1.0.0</version>
    <packaging>mule-application</packaging>

    <properties>
        <skipMunitTests>false</skipMunitTests>
    </properties>

    <build>
        <plugins>
            <plugin>
                <groupId>org.mule.tools.maven</groupId>
                <artifactId>mule-maven-plugin</artifactId>
                <version>${mule.maven.plugin.version}</version>
                <extensions>true</extensions>
                <configuration>
                    <cloudhub2Deployment>
                        <uri>https://anypoint.mulesoft.com</uri>
                        <provider>MC</provider>
                        <environment>Sandbox</environment>
                        <target>{YOUR_PRIVATE_SPACE_ID}</target>
                        <muleVersion>${app.runtime}</muleVersion>
                        <server>anypoint-exchange-v3</server>
                        <applicationName>data-cloud-sapi-v1</applicationName>
                        <replicas>1</replicas>
                        <vCores>0.1</vCores>
                        <deploymentTimeout>600000</deploymentTimeout>
                        <properties>
                            <sfdc.clientId>${sfdc.clientId}</sfdc.clientId>
                            <sfdc.clientSecret>${sfdc.clientSecret}</sfdc.clientSecret>
                            <sfdc.tokenEndpoint>${sfdc.tokenEndpoint}</sfdc.tokenEndpoint>
                            <slack.botToken>${slack.botToken}</slack.botToken>
                        </properties>
                    </cloudhub2Deployment>
                </configuration>
            </plugin>
            <plugin>
                <groupId>com.mulesoft.munit.tools</groupId>
                <artifactId>munit-maven-plugin</artifactId>
                <version>${munit.version}</version>
                <executions>
                    <execution>
                        <id>run-munit</id>
                        <phase>test</phase>
                        <goals>
                            <goal>test</goal>
                            <goal>coverage-report</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>

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
            <groupId>com.mulesoft.connectors</groupId>
            <artifactId>mule4-sdc-connector</artifactId>
            <classifier>mule-plugin</classifier>
        </dependency>
        <dependency>
            <groupId>com.mulesoft.modules</groupId>
            <artifactId>mule-secure-configuration-property-module</artifactId>
            <classifier>mule-plugin</classifier>
        </dependency>
        <dependency>
            <groupId>org.mule.modules</groupId>
            <artifactId>mule-apikit-module</artifactId>
            <classifier>mule-plugin</classifier>
        </dependency>
        <dependency>
            <groupId>org.mule.modules</groupId>
            <artifactId>mule-tracing-module</artifactId>
            <classifier>mule-plugin</classifier>
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

    <distributionManagement>
        <repository>
            <id>anypoint-exchange-v3</id>
            <url>https://maven.anypoint.mulesoft.com/api/v3/organizations/{YOUR_ORG_ID}/maven</url>
        </repository>
    </distributionManagement>
</project>
```

Replace `{YOUR_PRIVATE_SPACE_ID}` with your CloudHub 2.0 Private Space target ID.

**Checkpoint:** Run `mvn validate` from the project root. It should succeed with no errors before proceeding.

---

## Part B — data-cloud-sapi: Global Configuration

Create `src/main/mule/global.xml`.

### B.1 — Namespace declarations

The root `<mule>` element must declare all connector namespaces used in this file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:sdc="http://www.mulesoft.org/schema/mule/sdc"
      xmlns:apikit="http://www.mulesoft.org/schema/mule/mule-apikit"
      xmlns:tls="http://www.mulesoft.org/schema/mule/tls"
      xmlns:os="http://www.mulesoft.org/schema/mule/os"
      xmlns:secure-properties="http://www.mulesoft.org/schema/mule/secure-properties"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/tls http://www.mulesoft.org/schema/mule/tls/current/mule-tls.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/mule-apikit http://www.mulesoft.org/schema/mule/mule-apikit/current/mule-apikit.xsd
http://www.mulesoft.org/schema/mule/os http://www.mulesoft.org/schema/mule/os/current/mule-os.xsd
http://www.mulesoft.org/schema/mule/secure-properties http://www.mulesoft.org/schema/mule/secure-properties/current/mule-secure-properties.xsd
http://www.mulesoft.org/schema/mule/sdc http://www.mulesoft.org/schema/mule/sdc/current/mule-sdc.xsd">
```

### B.2 — Object Store Caching Strategy

Add this immediately after the opening `<mule>` tag:

```xml
    <ee:object-store-caching-strategy name="profileLookupCachingStrategy"
        keyGenerationExpression="#[vars.profileLookupCacheKey]"
        doc:name="Profile Lookup Cache Strategy">
        <os:private-object-store alias="profileLookupCacheStore"
            persistent="true"
            maxEntries="10000"
            entryTtl="5"
            entryTtlUnit="MINUTES"
            expirationInterval="1"
            expirationIntervalUnit="MINUTES" />
    </ee:object-store-caching-strategy>
```

The `keyGenerationExpression` references `vars.profileLookupCacheKey`. You must set this variable to `"profileLookup::" ++ safeTargetEmail` before the `<ee:cache>` block in the flow (covered in Part D).

### B.3 — HTTP Listener

```xml
    <!-- CloudHub terminates TLS at the ingress; app listener remains HTTP on worker port. -->
    <http:listener-config name="httpListenerConfig" doc:name="HTTP Listener config">
        <http:listener-connection host="0.0.0.0" port="${http.port}" />
    </http:listener-config>
```

### B.4 — TLS Contexts

Two TLS contexts are needed: one for the inbound listener (key-store) and one for outbound requests (trust-store):

```xml
    <tls:context name="listenerTlsContext" doc:name="Listener TLS Context">
        <tls:key-store type="${tls.keystore.type}"
                       path="${tls.keystore.path}"
                       alias="${tls.keystore.alias}"
                       password="${secure::tls.keystorePassword}"
                       keyPassword="${secure::tls.keyPassword}" />
    </tls:context>

    <tls:context name="requesterTlsContext" enabledProtocols="TLSv1.2,TLSv1.3"
                 doc:name="Requester TLS Context">
        <tls:trust-store insecure="false" />
    </tls:context>
```

The `requesterTlsContext` is attached to outbound HTTP request configs (Slack API, local profile calls). `insecure="false"` means the JVM's default trust store validates all upstream certificates.

### B.5 — HTTP Request Configs

```xml
    <http:request-config name="slackApiRequestConfig" doc:name="Slack API Request config"
                         basePath="/api">
        <http:request-connection protocol="HTTPS"
                                 host="${slack.host}"
                                 port="${slack.port}"
                                 tlsContext="requesterTlsContext"
                                 maxConnections="20"
                                 connectionIdleTimeout="30000" />
        <http:default-headers>
            <http:default-header key="Authorization" value="Bearer ${secure::slack.botToken}" />
        </http:default-headers>
    </http:request-config>

    <http:request-config name="localProfileRequestConfig"
                         doc:name="Local Profile Request config">
        <http:request-connection protocol="HTTPS"
                                 host="${local.profile.host}"
                                 port="${local.profile.port}"
                                 tlsContext="requesterTlsContext"
                                 maxConnections="10"
                                 connectionIdleTimeout="30000" />
    </http:request-config>
```

### B.6 — Configuration Properties and Secure Properties

```xml
    <global-property name="env" value="dev" />
    <configuration-properties file="config.yaml" doc:name="Common Configuration properties" />
    <configuration-properties file="${env}-config.yaml"
                               doc:name="Environment Configuration properties" />
    <secure-properties:config name="securePropertiesConfig"
        file="secure-properties.yaml"
        key="#[p('secure.key') default 'local-dev-secure-key']"
        doc:name="Secure Properties Config" />
    <configuration defaultErrorHandler-ref="global-default-error-handler"
                   doc:name="Global Defaults" />
```

The `secure.key` system property is passed at runtime. Locally, the fallback value `local-dev-secure-key` is used. In CloudHub, pass `-M-Dsecure.key=<actual-key>` as a JVM argument.

### B.7 — Data Cloud Connector Config

```xml
    <sdc:sdc-config name="salesforceDataCloudConfig"
                    doc:name="Salesforce Data Cloud Config">
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

Note: the SDC connector uses `consumerKey`/`consumerSecret`/`tokenEndpoint` — not `clientId`/`clientSecret`/`tokenUrl`. These reflect the Salesforce connected app attribute names.

### B.8 — APIkit Config

```xml
    <apikit:config name="dataCloudSapiApikitConfig"
        api="api/data-cloud-sapi.raml"
        outboundHeadersMapName="outboundHeaders"
        httpStatusVarName="httpStatus" />

</mule>
```

### B.9 — Create config.yaml

Create `src/main/resources/config.yaml`:

```yaml
http:
  responseTimeoutMs: "10000"
tls:
  keystore:
    type: "pkcs12"
    path: "certs/data-cloud-sapi-local.p12"
    alias: "data-cloud-sapi-local"
```

Create `src/main/resources/dev-config.yaml`:

```yaml
http:
  port: "8083"
slack:
  host: "slack.com"
  port: "443"
local:
  profile:
    host: "localhost"
    port: "8083"
```

Create `src/main/resources/secure-properties.yaml`. The values are encrypted placeholders — you will populate them using the Secure Properties Tool before local testing:

```yaml
sfdc:
  clientId: "![<encrypted-client-id>]"
  clientSecret: "![<encrypted-client-secret>]"
  tokenEndpoint: "![<encrypted-token-endpoint>]"
slack:
  botToken: "![<encrypted-bot-token>]"
tls:
  keystorePassword: "![<encrypted-keystore-password>]"
  keyPassword: "![<encrypted-key-password>]"
```

**Checkpoint:** Start the app in Anypoint Studio. It should start without connector errors. If you see `SDC:UNAUTHORIZED`, the credentials in `secure-properties.yaml` are incorrect or the decryption key does not match.

---

## Part C — data-cloud-sapi: RAML Specification

Create `src/main/resources/api/data-cloud-sapi.raml`:

```raml
#%RAML 1.0
title: Data Cloud SAPI
version: v1
baseUri: /apikit
mediaType: application/json

/profile/{slackId}:
  uriParameters:
    slackId:
      type: string
      required: true
      description: Slack user identifier used to resolve customer profile context.
  get:
    description: Return decision-grade grounding context for the provided Slack identity.
    responses:
      200:
        body:
          application/json:
            type: object
            properties:
              groundingVersion: string
              customerTier: string
              churnRisk: string
              customerName: string
              returnWindowStatus: string
              identityConfidence: string
              recommendedAction: string
              knownUnknowns:
                type: array
                items: string
            example:
              {
                "groundingVersion": "1.0",
                "customerTier": "Platinum",
                "churnRisk": "Low",
                "customerName": "Jane Smith",
                "returnWindowStatus": "UNKNOWN",
                "identityConfidence": "HIGH",
                "recommendedAction": "CONTINUE",
                "knownUnknowns": ["return_window_not_computed_in_data_cloud_sapi"]
              }
```

After saving the RAML, right-click it in Studio's Package Explorer and select **Mule > Generate Flows from REST API**. Studio generates scaffolded flows for each RAML operation.

**Checkpoint:** The APIkit router in `api.xml` should now have a generated flow named `get:/profile/{slackId}:dataCloudSapiApikitConfig`. You will replace its content in Part D.

---

## Part D — data-cloud-sapi: Main Flows

### D.1 — Create the error handler

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

    <error-handler name="global-default-error-handler">
        <on-error-propagate type="APIKIT:BAD_REQUEST,VALIDATION:*" logException="true">
            <set-variable variableName="httpStatus" value="#[400]" />
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: { code: "BAD_REQUEST", message: "The request is invalid.",
           correlationId: (vars.requestId default correlationId) } }]]>
                    </ee:set-payload>
                </ee:message>
            </ee:transform>
        </on-error-propagate>

        <on-error-propagate type="MULE:CONNECTIVITY,HTTP:CONNECTIVITY,SDC:UNAUTHORIZED,SDC:CONNECTIVITY"
                            logException="true">
            <set-variable variableName="httpStatus" value="#[503]" />
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: { code: "SERVICE_UNAVAILABLE",
           message: "A downstream service is unavailable. Try again later.",
           correlationId: (vars.requestId default correlationId) } }]]>
                    </ee:set-payload>
                </ee:message>
            </ee:transform>
        </on-error-propagate>

        <on-error-propagate type="ANY" logException="true">
            <set-variable variableName="httpStatus" value="#[500]" />
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: { code: "INTERNAL_SERVER_ERROR",
           message: "An unexpected error occurred.",
           correlationId: (vars.requestId default correlationId) } }]]>
                    </ee:set-payload>
                </ee:message>
            </ee:transform>
        </on-error-propagate>
    </error-handler>
</mule>
```

### D.2 — Create main.xml (primary flow)

Create `src/main/mule/main.xml`. This file contains the `get-unified-profile-flow` which handles `GET /api/profile/{slackId}`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd">

    <flow name="get-unified-profile-flow">
        <http:listener doc:name="Listener" config-ref="httpListenerConfig"
                       path="/api/profile/{slackId}" allowedMethods="GET">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="500">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>

        <!-- Step 1: Set defaults and extract path param -->
        <set-variable variableName="httpStatus" value="#[200]" doc:name="Default 200" />
        <set-variable variableName="incomingSlackId"
            value="#[attributes.uriParams.slackId]" doc:name="Save Slack ID" />

        <!-- Step 2: Extract OBO correlation headers -->
        <set-variable variableName="requestId"
            value='#[output application/java ---
                attributes.headers."x-request-id"
                default attributes.headers.requestId
                default attributes.queryParams.requestId
                default ""
            ]' doc:name="Resolve Request ID" />
        <set-variable variableName="flowId"
            value='#[output application/java ---
                attributes.headers."x-flow-id"
                default attributes.headers.flowId
                default attributes.queryParams.flowId
                default ""
            ]' doc:name="Resolve Flow ID" />
        <set-variable variableName="sessionId"
            value='#[output application/java ---
                attributes.headers."x-session-id"
                default attributes.headers.sessionId
                default attributes.queryParams.sessionId
                default ""
            ]' doc:name="Resolve Session ID" />
        <set-variable variableName="xUserId"
            value='#[output application/java ---
                attributes.headers."x-user-id"
                default attributes.queryParams.userId
                default ""
            ]' doc:name="Resolve X User ID" />

        <!-- Step 3: MDC tracing — these variables appear in every log line -->
        <tracing:set-logging-variable variableName="requestId"
            value="#[vars.requestId]" doc:name="MDC requestId" />
        <tracing:set-logging-variable variableName="flowId"
            value="#[vars.flowId]" doc:name="MDC flowId" />
        <tracing:set-logging-variable variableName="sessionId"
            value="#[vars.sessionId]" doc:name="MDC sessionId" />
        <tracing:set-logging-variable variableName="userId"
            value="#[vars.xUserId]" doc:name="MDC userId" />

        <logger level="INFO" doc:name="Log Request"
            message='#[output application/java ---
                "Incoming request slackId=" ++ vars.incomingSlackId ++
                " requestId=" ++ vars.requestId ++
                " flowId=" ++ vars.flowId ++
                " sessionId=" ++ vars.sessionId ++
                " xUserId=" ++ vars.xUserId
            ]' />

        <!-- Step 4: Resolve customer context with graceful fallback -->
        <try doc:name="Resolve Customer Context Safely">
            <flow-ref name="resolve-customer-context-subflow"
                      doc:name="Resolve Customer Context" />
            <error-handler>
                <on-error-continue type="ANY" logException="true"
                                   doc:name="Fallback On Context Failure">
                    <set-variable variableName="partyId" value="#['']"
                        doc:name="Fallback Party ID" />
                    <set-variable variableName="resolutionSource" value="FALLBACK"
                        doc:name="Fallback Resolution Source" />
                    <set-variable variableName="targetEmail"
                        value="unknown@training.demo"
                        doc:name="Fallback Target Email" />
                    <set-payload value='#[output application/java --- { data: [] }]'
                        doc:name="Fallback Empty Profile Data" />
                    <logger level="WARN" doc:name="Log Context Failure Fallback"
                        message='#[output application/java ---
                            "Profile context lookup failed; returning graceful fallback" ++
                            " requestId=" ++ (vars.requestId default "")
                        ]' />
                </on-error-continue>
            </error-handler>
        </try>

        <!-- Step 5: Build grounding response -->
        <flow-ref name="build-grounding-response-subflow"
                  doc:name="Build Grounding Response" />

        <logger level="INFO" doc:name="Log Result"
            message='#[output application/java ---
                "Grounding result requestId=" ++ (vars.requestId default "") ++
                " recommendedAction=" ++ (payload.recommendedAction default "UNKNOWN")
            ]' />
    </flow>

</mule>
```

### D.3 — Create main-support.xml (sub-flows)

Create `src/main/mule/main-support.xml`. This file contains the two sub-flows called by the main flow:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:sdc="http://www.mulesoft.org/schema/mule/sdc"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/sdc http://www.mulesoft.org/schema/mule/sdc/current/mule-sdc.xsd">

    <!-- ================================================================
         Sub-flow 1: Resolve email, then query Data Cloud for party and
         individual profile. Result is left in payload as {data: [...]}.
         ================================================================ -->
    <sub-flow name="resolve-customer-context-subflow">

        <!-- Map-first resolution: static map avoids Slack API calls in training. -->
        <ee:transform doc:name="Resolve Email from Map">
            <ee:variables>
                <ee:set-variable variableName="mappedEmail"><![CDATA[%dw 2.0
output application/java
var slackToEmailMap = {
    "U0AA9JSR2AD": "student-slack-test@globaltech.com"
}
---
slackToEmailMap[vars.incomingSlackId] default ""
]]></ee:set-variable>
            </ee:variables>
        </ee:transform>

        <choice doc:name="Use Map or Slack API">
            <when expression='#[vars.mappedEmail != ""]'>
                <set-variable variableName="targetEmail"
                    value="#[vars.mappedEmail]" doc:name="Use Mapped Email" />
                <set-variable variableName="resolutionSource"
                    value="MAP" doc:name="Set MAP Source" />
            </when>
            <otherwise>
                <!-- Slack API fallback: GET /api/users.info?user={slackId} -->
                <try doc:name="Resolve Email from Slack">
                    <http:request method="GET" doc:name="Get Slack User Email"
                        config-ref="slackApiRequestConfig"
                        path="#['/users.info?user=' ++ vars.incomingSlackId]" />
                    <set-variable variableName="targetEmail"
                        value='#[output application/java ---
                            payload.user.profile.email default "unknown@training.demo"]'
                        doc:name="Extract Email" />
                    <set-variable variableName="resolutionSource"
                        value="SLACK_API" doc:name="Set Slack Source" />
                    <error-handler>
                        <on-error-continue type="ANY" logException="true">
                            <set-variable variableName="targetEmail"
                                value="unknown@training.demo" doc:name="Use Fallback Email" />
                            <set-variable variableName="resolutionSource"
                                value="FALLBACK" doc:name="Set Fallback Source" />
                        </on-error-continue>
                    </error-handler>
                </try>
            </otherwise>
        </choice>

        <!-- SQL injection prevention before building query strings -->
        <ee:transform doc:name="Sanitize Query Inputs">
            <ee:variables>
                <ee:set-variable variableName="safeTargetEmail"><![CDATA[%dw 2.0
import sanitizeSqlLiteral from dw::common::sanitize
output application/java
---
sanitizeSqlLiteral(vars.targetEmail)
]]></ee:set-variable>
            </ee:variables>
        </ee:transform>

        <!-- Cache key must be set before entering ee:cache -->
        <set-variable variableName="profileLookupCacheKey"
            value='#[output application/java --- "profileLookup::" ++ vars.safeTargetEmail]'
            doc:name="Build Profile Cache Key" />

        <!-- Cache scope: both SDC queries are inside. Cache hit skips both. -->
        <ee:cache cachingStrategy-ref="profileLookupCachingStrategy"
                  doc:name="Cache Profile Lookup">
            <logger level="INFO" doc:name="Log Cache Miss"
                message='#[output application/java ---
                    "Profile cache MISS for key=" ++ vars.profileLookupCacheKey]' />

            <!-- Query 1: email -> partyId -->
            <sdc:query doc:name="Query Party ID from Email"
                       config-ref="salesforceDataCloudConfig">
                <sdc:query-body><![CDATA[#[output application/json --- {
    sql: "SELECT ssot__PartyId__c FROM ssot__ContactPointEmail__dlm WHERE ssot__EmailAddress__c = '"
          ++ vars.safeTargetEmail ++ "'"
}]]]></sdc:query-body>
            </sdc:query>

            <set-variable variableName="partyId"
                value="#[payload.data[0].ssot__PartyId__c default '']"
                doc:name="Save Party ID" />

            <!-- Query 2: partyId -> individual profile -->
            <choice doc:name="Has Party ID?">
                <when expression='#[vars.partyId != ""]'>
                    <sdc:query doc:name="Query Individual by Party ID"
                               config-ref="salesforceDataCloudConfig">
                        <sdc:query-body><![CDATA[#[output application/json
    import sanitizeSqlLiteral from dw::common::sanitize
    var safePartyId = sanitizeSqlLiteral(vars.partyId)
    ---
    {
        sql: "SELECT ssot__Id__c, ssot__FirstName__c, ssot__LastName__c, LoyaltyTier__c, ChurnRisk__c FROM ssot__Individual__dlm WHERE ssot__Id__c = '" ++ safePartyId ++ "'"
    }]]]></sdc:query-body>
                    </sdc:query>
                </when>
                <otherwise>
                    <set-payload value='#[output application/java --- { data: [] }]'
                        doc:name="No Profile Payload" />
                </otherwise>
            </choice>
        </ee:cache>
    </sub-flow>

    <!-- ================================================================
         Sub-flow 2: Build grounding response from raw Data Cloud fields.
         Result is set as payload (JSON).
         ================================================================ -->
    <sub-flow name="build-grounding-response-subflow">
        <ee:transform doc:name="Build Grounding Response">
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
var profile = payload.data[0] default {}
var profileId = profile.ssot__Id__c default ""
var firstName = profile.ssot__FirstName__c default ""
var lastName = profile.ssot__LastName__c default ""
var tier = profile.LoyaltyTier__c default "UNKNOWN"
var churnRisk = profile.ChurnRisk__c default "UNKNOWN"
var returnWindowStatus = "UNKNOWN"
var identityConfidence =
    if (vars.resolutionSource == "MAP" and vars.partyId != "") "HIGH"
    else if (vars.resolutionSource == "SLACK_API" and vars.partyId != "") "MEDIUM"
    else "LOW"
var knownUnknowns = [
    if (vars.targetEmail == "unknown@training.demo") "customer_email_unverified" else null,
    if (vars.partyId == "") "party_id_not_found" else null,
    if (profileId == "") "individual_profile_not_found" else null,
    if (tier == "UNKNOWN") "loyalty_tier_unavailable" else null,
    if (churnRisk == "UNKNOWN") "churn_risk_unavailable" else null,
    "return_window_not_computed_in_data_cloud_sapi"
] filter ($ != null)
var policyState =
    if (profileId == "") "UNKNOWN"
    else if (tier == "Platinum" or tier == "Gold") "VIP_ACTIVE"
    else if (churnRisk == "High" or churnRisk == "HIGH") "RISK_HIGH"
    else "STANDARD_ACTIVE"
var recommendedAction =
    if (profileId == "") "CLARIFY"
    else if (identityConfidence == "LOW") "CLARIFY"
    else if (policyState == "RISK_HIGH") "ESCALATE"
    else "CONTINUE"
---
{
    groundingVersion: "1.0",
    metadata: {
        requestId: if (vars.requestId != "") vars.requestId else null,
        flowId: if (vars.flowId != "") vars.flowId else null,
        sessionId: if (vars.sessionId != "") vars.sessionId else null
    },
    customerTier: tier,
    churnRisk: churnRisk,
    customerName: if ((firstName ++ lastName) != "") trim(firstName ++ " " ++ lastName)
                  else "Guest",
    returnWindowStatus: returnWindowStatus,
    identityConfidence: identityConfidence,
    recommendedAction: recommendedAction,
    knownUnknowns: knownUnknowns
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>
    </sub-flow>

</mule>
```

**Checkpoint — Verify data-cloud-sapi locally:**

```bash
# Health check
curl -s http://localhost:8083/health | jq .
# Expected: {"status":"ok","app":"data-cloud-sapi"}

# Profile lookup with the mapped Slack ID
curl -s "http://localhost:8083/api/profile/U0AA9JSR2AD" \
  -H "x-user-id: U0AA9JSR2AD" \
  -H "x-request-id: test-001" | jq .
```

Expected response shape:
```json
{
  "groundingVersion": "1.0",
  "customerTier": "Platinum",
  "churnRisk": "Low",
  "customerName": "Jane Smith",
  "returnWindowStatus": "UNKNOWN",
  "identityConfidence": "HIGH",
  "recommendedAction": "CONTINUE",
  "knownUnknowns": ["return_window_not_computed_in_data_cloud_sapi"]
}
```

If `partyId` resolution fails (Data Cloud not yet seeded), you will see `identityConfidence: "LOW"` and `recommendedAction: "CLARIFY"`. That is the correct graceful fallback.

---

## Part E — service-cloud-mcp: Project Setup

### E.1 — Create the project

In Anypoint Studio, create a new Mule Project:

- Name: `service-cloud-mcp`
- Mule Runtime: `4.11.3`

### E.2 — Create pom.xml

`service-cloud-mcp` does not use a parent pom. All dependency versions are declared inline:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
             https://maven.apache.org/maven-v4_0_0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{YOUR_ORG_ID}</groupId>
    <artifactId>service-cloud-mcp</artifactId>
    <version>1.0.0</version>
    <packaging>mule-application</packaging>

    <properties>
        <app.runtime>4.11.3</app.runtime>
        <mule.maven.plugin.version>4.7.0</mule.maven.plugin.version>
        <munit.version>3.7.1</munit.version>
    </properties>

    <build>
        <plugins>
            <plugin>
                <groupId>org.mule.tools.maven</groupId>
                <artifactId>mule-maven-plugin</artifactId>
                <version>${mule.maven.plugin.version}</version>
                <extensions>true</extensions>
                <configuration>
                    <cloudhub2Deployment>
                        <uri>https://anypoint.mulesoft.com</uri>
                        <provider>MC</provider>
                        <environment>Sandbox</environment>
                        <target>{YOUR_PRIVATE_SPACE_ID}</target>
                        <muleVersion>${app.runtime}</muleVersion>
                        <server>anypoint-exchange-v3</server>
                        <applicationName>service-cloud-mcp</applicationName>
                        <replicas>1</replicas>
                        <vCores>0.1</vCores>
                        <deploymentTimeout>600000</deploymentTimeout>
                        <properties>
                            <sfdc.clientId>${sfdc.clientId}</sfdc.clientId>
                            <sfdc.clientSecret>${sfdc.clientSecret}</sfdc.clientSecret>
                            <sfdc.tokenEndpoint>${sfdc.tokenEndpoint}</sfdc.tokenEndpoint>
                        </properties>
                    </cloudhub2Deployment>
                </configuration>
            </plugin>
        </plugins>
    </build>

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
            <version>1.11.5</version>
            <classifier>mule-plugin</classifier>
        </dependency>
        <dependency>
            <groupId>org.mule.modules</groupId>
            <artifactId>mule-tracing-module</artifactId>
            <version>1.1.0</version>
            <classifier>mule-plugin</classifier>
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

    <repositories>
        <repository>
            <id>anypoint-exchange-v3</id>
            <url>https://maven.anypoint.mulesoft.com/api/v3/maven</url>
        </repository>
        <repository>
            <id>mulesoft-releases</id>
            <url>https://repository.mulesoft.org/releases/</url>
        </repository>
    </repositories>

    <distributionManagement>
        <repository>
            <id>anypoint-exchange-v3</id>
            <url>https://maven.anypoint.mulesoft.com/api/v3/organizations/{YOUR_ORG_ID}/maven</url>
        </repository>
    </distributionManagement>
</project>
```

---

## Part F — service-cloud-mcp: Global Configuration and RAML

### F.1 — Create global.xml

Create `src/main/mule/global.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:apikit="http://www.mulesoft.org/schema/mule/mule-apikit"
      xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/mule-apikit http://www.mulesoft.org/schema/mule/mule-apikit/current/mule-apikit.xsd
http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd">

    <http:listener-config name="HTTP_Listener_config" doc:name="HTTP Listener config">
        <http:listener-connection host="0.0.0.0" port="${http.port}" />
    </http:listener-config>

    <configuration-properties file="config.yaml" doc:name="Shared Configuration" />

    <apikit:config name="service-cloud-mcp-api-config"
        api="api/service-cloud-mcp.raml"
        outboundHeadersMapName="outboundHeaders"
        httpStatusVarName="httpStatus" />

    <salesforce:sfdc-config name="Salesforce_Config" doc:name="Salesforce Config">
        <salesforce:oauth-client-credentials-connection>
            <salesforce:oauth-client-credentials
                clientId="${sfdc.clientId}"
                clientSecret="${sfdc.clientSecret}"
                tokenUrl="${sfdc.tokenEndpoint}" />
        </salesforce:oauth-client-credentials-connection>
    </salesforce:sfdc-config>

</mule>
```

Note: the Salesforce connector uses `clientId`/`clientSecret`/`tokenUrl` — different from the SDC connector's `consumerKey`/`consumerSecret`/`tokenEndpoint`.

### F.2 — Create config.yaml

Create `src/main/resources/config.yaml`:

```yaml
http:
  port: "8084"

env: "dev"

sfdc:
  clientId: "${sfdc.clientId}"
  clientSecret: "${sfdc.clientSecret}"
  tokenEndpoint: "${sfdc.tokenEndpoint}"
```

For local development, create a `dev-config.yaml` with the actual Salesforce credential values or pass them as JVM arguments: `-M-Dsfdc.clientId=... -M-Dsfdc.clientSecret=... -M-Dsfdc.tokenEndpoint=...`

### F.3 — Create the RAML

Create `src/main/resources/api/service-cloud-mcp.raml`:

```raml
#%RAML 1.0
title: service-cloud-mcp API
version: v1
baseUri: /api
mediaType: application/json

types:
  IssueCreditRequest:
    type: object
    additionalProperties: true
    properties:
      customerId:
        type: string
      amount:
        type: number
      orderNumber:
        type: string
      reason:
        type: string
      idempotencyKey?:
        type: string
      fraudScore?:
        type: number
      orchestratorContext?:
        type: object
      requestId?:
        type: string
      flowId?:
        type: string
      sessionId?:
        type: string
      userId?:
        type: string

  IssueCreditResponse:
    type: object
    additionalProperties: true
    properties:
      status:
        type: string
        enum: [SUCCESS, PARTIAL_SUCCESS, FAILED, REJECTED]
      creditId:
        type: string
      caseId:
        type: string
      opportunityId:
        type: string
      actionType:
        type: string
      failureClass:
        type: string
        enum: [NONE, BUSINESS_VALIDATION, BUSINESS_REJECTION, TECHNICAL_SALESFORCE, TECHNICAL_PARTIAL]
      retryable:
        type: boolean
      decisionHint:
        type: string
      missingFields:
        type: array
        items: string
      errorCode:
        type: string
      idempotencyKey:
        type: string
      requestId:
        type: string
      flowId:
        type: string
      message:
        type: string

/mcp:
  /tool:
    /issue_credit:
      post:
        description: Deterministic refund execution endpoint for irreversible business action handling.
        body:
          application/json:
            type: IssueCreditRequest
        responses:
          200:
            body:
              application/json:
                type: IssueCreditResponse
          500:
            body:
              application/json:
                type: IssueCreditResponse
```

### F.4 — Add custom fields to the Salesforce Opportunity object

Before building the flows, add four custom fields to the Opportunity object in your Salesforce org. These fields store the link between a refund action and the Case.

1. Log in to Salesforce Setup.
2. Go to **Object Manager > Opportunity > Fields & Relationships > New**.
3. Create the following fields (all type: Text, length 255, unless noted):

| Field Label | API Name | Type | Length |
|---|---|---|---|
| Refund Order Number | `Refund_Order_Number__c` | Text | 100 |
| Refund Reason | `Refund_Reason__c` | Text Area | 255 |
| Refund Case Id | `Refund_Case_Id__c` | Text | 18 |
| Refund Agent Status | `Refund_Agent_Status__c` | Text | 50 |

4. After creating each field, add it to the **Standard** page layout so it is visible in the agent console.

**Checkpoint:** Open any Opportunity record. Confirm the four refund fields appear in the layout.

---

## Part G — service-cloud-mcp: Tool Flow

### G.1 — Create the error handler

Create `src/main/mule/error.xml` (same pattern as data-cloud-sapi):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <error-handler name="global-default-error-handler">
        <on-error-propagate type="APIKIT:BAD_REQUEST,VALIDATION:*" logException="true">
            <set-variable variableName="httpStatus" value="#[400]" />
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: { code: "BAD_REQUEST", message: "The request is invalid." } }]]>
                    </ee:set-payload>
                </ee:message>
            </ee:transform>
        </on-error-propagate>
        <on-error-propagate type="ANY" logException="true">
            <set-variable variableName="httpStatus" value="#[500]" />
            <ee:transform>
                <ee:message>
                    <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ error: { code: "INTERNAL_SERVER_ERROR", message: "An unexpected error occurred." } }]]>
                    </ee:set-payload>
                </ee:message>
            </ee:transform>
        </on-error-propagate>
    </error-handler>

</mule>
```

### G.2 — Create processing-subflows.xml

This file contains `mcp-init-context` (context extraction) and `mcp-format-response` (response serialization):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:tracing="http://www.mulesoft.org/schema/mule/tracing"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/tracing http://www.mulesoft.org/schema/mule/tracing/current/mule-tracing.xsd">

    <sub-flow name="mcp-init-context">
        <!-- Extract correlation headers (accept both casing conventions) -->
        <set-variable variableName="requestId"
            value='#[output application/java ---
                (attributes.headers."x-request-id" default attributes.headers."X-Request-Id"
                 default payload.requestId default payload.request_id default "") as String]'
            doc:name="Save Request ID" />
        <set-variable variableName="flowId"
            value='#[output application/java ---
                (attributes.headers."x-flow-id" default attributes.headers."X-Flow-Id"
                 default payload.flowId default payload.flow_id default "") as String]'
            doc:name="Save Flow ID" />
        <set-variable variableName="sessionId"
            value='#[output application/java ---
                (attributes.headers."x-session-id" default attributes.headers."X-Session-Id"
                 default payload.sessionId default payload.session_id default "") as String]'
            doc:name="Save Session ID" />
        <set-variable variableName="userId"
            value='#[output application/java ---
                (attributes.headers."x-user-id" default attributes.headers."X-User-Id"
                 default payload.userId default "") as String]'
            doc:name="Save OBO User ID" />

        <!-- MDC tracing -->
        <tracing:set-logging-variable variableName="requestId"
            value="#[vars.requestId default 'unknown']" doc:name="MDC Request ID" />
        <tracing:set-logging-variable variableName="flowId"
            value="#[vars.flowId default 'unknown']" doc:name="MDC Flow ID" />
        <tracing:set-logging-variable variableName="sessionId"
            value="#[vars.sessionId default 'unknown']" doc:name="MDC Session ID" />
        <tracing:set-logging-variable variableName="userId"
            value="#[vars.userId default 'unknown']" doc:name="MDC User ID" />

        <!-- Extract business fields from payload (support both flat and structured shapes) -->
        <set-variable variableName="customerId"
            value='#[payload.structured.customerId default payload.customerId default ""]'
            doc:name="Save Customer ID" />
        <set-variable variableName="orderNumber"
            value='#[payload.structured.orderNumber default payload.orderNumber
                      default payload.order_number default ""]'
            doc:name="Save Order Number" />
        <set-variable variableName="reason"
            value='#[payload.structured.reason default payload.reason
                      default payload.refundReason default "Customer return request"]'
            doc:name="Save Reason" />
        <set-variable variableName="fraudScore"
            value='#[payload.orchestratorContext.fraudScore default payload.fraudScore default null]'
            doc:name="Save Fraud Score" />

        <!-- Initialise state variables -->
        <set-variable variableName="agentStatus" value="RECEIVED"
            doc:name="Set Initial Agent Status" />
        <set-variable variableName="errorMessage" value=""
            doc:name="Clear Error Message" />
        <set-variable variableName="opportunityId" value=""
            doc:name="Init Opportunity ID" />
        <set-variable variableName="caseId" value=""
            doc:name="Init Case ID" />
        <set-variable variableName="creditId" value=""
            doc:name="Init Credit ID" />
        <set-variable variableName="actionType" value="CREATE_CASE"
            doc:name="Init Action Type" />
        <set-variable variableName="failureClass" value="NONE"
            doc:name="Init Failure Class" />
        <set-variable variableName="retryable" value="#[false]"
            doc:name="Init Retryable" />
        <set-variable variableName="decisionHint" value="NONE"
            doc:name="Init Decision Hint" />
        <set-variable variableName="missingFields" value="#[[]]"
            doc:name="Init Missing Fields" />
        <set-variable variableName="errorCode" value="NONE"
            doc:name="Init Error Code" />
        <set-variable variableName="opportunityUpdateFailed" value="#[false]"
            doc:name="Init Opportunity Update Failed" />

        <!-- Idempotency key: use caller-supplied key or derive from business fields -->
        <set-variable variableName="idempotencyKey"
            value='#[if ((payload.idempotencyKey default "") != "")
                       payload.idempotencyKey
                   else
                       ((vars.customerId default "unknown-customer") ++ "|" ++
                        (vars.orderNumber default "unknown-order") ++ "|" ++
                        ((payload.amount default "unknown-amount") as String))]'
            doc:name="Set Idempotency Key" />

        <logger level="INFO" doc:name="Log Request"
            message='#[write({sourceApp: "service-cloud-mcp", stage: "INGRESS",
                status: "RECEIVED", requestId: vars.requestId, flowId: vars.flowId,
                sessionId: vars.sessionId, oboUserId: vars.userId},
                "application/json")]' />
    </sub-flow>

    <sub-flow name="mcp-format-response">
        <ee:transform doc:name="Format MCP Response">
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
    "status":
        if ((vars.failureClass default "NONE") == "BUSINESS_VALIDATION"
            or (vars.failureClass default "NONE") == "BUSINESS_REJECTION") "REJECTED"
        else if ((vars.httpStatus default 200) == 200
            and (vars.caseId default "") != ""
            and (vars.opportunityUpdateFailed default false)) "PARTIAL_SUCCESS"
        else if ((vars.httpStatus default 200) == 200
            and (vars.caseId default "") != "") "SUCCESS"
        else "FAILED",
    "creditId": if ((vars.failureClass default "NONE") == "BUSINESS_VALIDATION"
        or (vars.failureClass default "NONE") == "BUSINESS_REJECTION") ""
        else (vars.creditId default ""),
    "caseId": if ((vars.failureClass default "NONE") == "BUSINESS_VALIDATION"
        or (vars.failureClass default "NONE") == "BUSINESS_REJECTION") ""
        else (vars.caseId default ""),
    "opportunityId": vars.opportunityId default "",
    "actionType": vars.actionType default "NOOP",
    "failureClass": vars.failureClass default "NONE",
    "retryable": vars.retryable default false,
    "decisionHint": vars.decisionHint default "NONE",
    "missingFields": vars.missingFields default [],
    "errorCode": vars.errorCode default "NONE",
    "idempotencyKey": vars.idempotencyKey default "",
    "requestId": vars.requestId default "",
    "flowId": vars.flowId default "",
    "sessionId": vars.sessionId default "",
    "userId": vars.userId default "",
    "agentStatus": vars.agentStatus,
    "message": if ((vars.httpStatus default 200) == 200
                   and (vars.caseId default "") != ""
                   and (vars.opportunityUpdateFailed default false))
                   "Case action completed but opportunity update failed for order " ++ vars.orderNumber ++ "."
               else if ((vars.httpStatus default 200) == 200
                   and (vars.caseId default "") != "")
                   "Case action completed for order " ++ vars.orderNumber ++ "."
               else
                   "Technical failure while processing order " ++ vars.orderNumber ++ ". "
                   ++ (vars.errorMessage default "")
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>

        <logger level="INFO" doc:name="Log Result"
            message='#[write({sourceApp: "service-cloud-mcp", stage: "RESULT",
                status: payload.status default "UNKNOWN",
                caseId: payload.caseId default "",
                errorCode: payload.errorCode default "NONE",
                requestId: vars.requestId, flowId: vars.flowId},
                "application/json")]' />
    </sub-flow>

</mule>
```

### G.3 — Create main.xml (issue_credit handler)

Create `src/main/mule/main.xml`. This is the core tool flow — all five execution stages:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd">

    <flow name="mcp-issue-credit-handler">
        <set-variable variableName="httpStatus" value="#[200]" doc:name="Default 200" />

        <!-- Stage 1: Extract context and initialise state -->
        <flow-ref name="mcp-init-context" doc:name="Initialize Request Context" />

        <!-- Stage 2: Input validation
             If any required field is missing, set REJECTED_INPUT and skip all later stages.
             HTTP status stays 200 — this is a deterministic business rejection, not an error. -->
        <choice doc:name="Validate Required Inputs">
            <when expression='#[isBlank((vars.customerId default "") as String)
                               or isBlank((vars.orderNumber default "") as String)
                               or ((payload.amount default null) == null)]'>
                <set-variable variableName="agentStatus" value="REJECTED_INPUT" />
                <set-variable variableName="failureClass" value="BUSINESS_VALIDATION" />
                <set-variable variableName="actionType" value="NOOP" />
                <set-variable variableName="retryable" value="#[false]" />
                <set-variable variableName="decisionHint"
                    value="REJECT_AND_REQUEST_MISSING_FIELDS" />
                <set-variable variableName="errorCode"
                    value="VALIDATION_MISSING_FIELDS" />
                <set-variable variableName="missingFields"
                    value='#[output application/java --- [
                        if (isBlank((vars.customerId default "") as String)) "customerId" else null,
                        if (isBlank((vars.orderNumber default "") as String)) "orderNumber" else null,
                        if ((payload.amount default null) == null) "amount" else null
                    ] filter ($ != null)]' />
                <set-variable variableName="errorMessage"
                    value='#[if (isBlank((vars.customerId default "") as String)) "customerId is required"
                              else if (isBlank((vars.orderNumber default "") as String)) "orderNumber is required"
                              else "amount is required"]' />
                <logger level="WARN" doc:name="Log Invalid Input"
                    message='#[write({sourceApp: "service-cloud-mcp", stage: "VALIDATE_INPUT",
                        status: "REJECTED", message: vars.errorMessage,
                        errorCode: vars.errorCode}, "application/json")]' />
            </when>
        </choice>

        <!-- Stage 3: Risk gate
             Orders prefixed 999 with fraudScore >= 70 are blocked unconditionally. -->
        <choice doc:name="Critical Risk Gate">
            <when expression='#[vars.httpStatus == 200
                               and ((vars.orderNumber default "") startsWith "999")
                               and ((vars.fraudScore default null) != null)
                               and ((vars.fraudScore as Number) >= 70)]'>
                <set-variable variableName="agentStatus" value="REJECTED_RISK" />
                <set-variable variableName="failureClass" value="BUSINESS_REJECTION" />
                <set-variable variableName="actionType" value="NOOP" />
                <set-variable variableName="retryable" value="#[false]" />
                <set-variable variableName="decisionHint"
                    value="REJECT_AND_ESCALATE_FRAUD_REVIEW" />
                <set-variable variableName="errorCode" value="RISK_POLICY_BLOCK" />
                <set-variable variableName="missingFields" value="#[[]]" />
                <set-variable variableName="errorMessage"
                    value='#["Critical-risk order prefix 999 blocked with fraudScore "
                              ++ (vars.fraudScore as String)]' />
                <logger level="WARN" doc:name="Log Critical Risk Rejection"
                    message='#[write({sourceApp: "service-cloud-mcp", stage: "RISK_GATE",
                        status: "REJECTED", message: vars.errorMessage,
                        errorCode: vars.errorCode}, "application/json")]' />
            </when>
        </choice>

        <!-- Stage 4: Idempotency check
             Query for an existing Case with the same Subject key.
             If found, reuse it. Do not create a second Case. -->
        <try doc:name="Check Existing Case By Idempotency Key">
            <choice doc:name="Can Check Existing Case?">
                <when expression='#[vars.httpStatus == 200
                                   and (vars.failureClass default "NONE") == "NONE"]'>
                    <salesforce:query doc:name="Query Existing Case"
                                      config-ref="Salesforce_Config">
                        <salesforce:salesforce-query><![CDATA[#[
                            "SELECT Id FROM Case WHERE Subject = 'Return Request - Key "
                            ++ vars.idempotencyKey ++ "' ORDER BY CreatedDate DESC LIMIT 1"
                        ]]]></salesforce:salesforce-query>
                    </salesforce:query>
                    <choice doc:name="Existing Case Found?">
                        <when expression="#[sizeOf(payload) > 0]">
                            <set-variable variableName="caseId"
                                value="#[payload[0].Id]" doc:name="Set Existing Case ID" />
                            <set-variable variableName="actionType"
                                value="REUSE_CASE" doc:name="Set Reuse Action Type" />
                            <set-variable variableName="agentStatus"
                                value="CASE_REUSED" doc:name="Set Case Reused Status" />
                            <logger level="INFO" doc:name="Log Existing Case Reuse"
                                message='#[write({sourceApp: "service-cloud-mcp",
                                    stage: "CASE_IDEMPOTENCY", status: "SUCCESS",
                                    message: "Existing case reused",
                                    caseId: vars.caseId}, "application/json")]' />
                        </when>
                    </choice>
                </when>
            </choice>
            <error-handler>
                <on-error-continue type="ANY" logException="true"
                                   doc:name="Idempotency Check Error">
                    <set-variable variableName="retryable" value="#[true]" />
                    <logger level="WARN" doc:name="Log Idempotency Check Error"
                        message='#[write({sourceApp: "service-cloud-mcp",
                            stage: "CASE_IDEMPOTENCY", status: "WARN",
                            message: "Idempotency lookup failed; proceeding"},
                            "application/json")]' />
                </on-error-continue>
            </error-handler>
        </try>

        <!-- Stage 5a: Find open Opportunity for linkage (non-fatal if absent) -->
        <try doc:name="Find Opportunity">
            <choice doc:name="Can Query Opportunity?">
                <when expression='#[vars.httpStatus == 200
                                   and (vars.failureClass default "NONE") == "NONE"]'>
                    <salesforce:query doc:name="Query Open Opportunity"
                                      config-ref="Salesforce_Config">
                        <salesforce:salesforce-query>SELECT Id FROM Opportunity
                            WHERE StageName != 'Closed Won'
                            AND StageName != 'Closed Lost'
                            ORDER BY LastModifiedDate DESC LIMIT 1
                        </salesforce:salesforce-query>
                    </salesforce:query>
                    <choice doc:name="Opportunity Found?">
                        <when expression="#[sizeOf(payload) > 0]">
                            <set-variable variableName="opportunityId"
                                value="#[payload[0].Id]" doc:name="Save Opportunity ID" />
                        </when>
                        <otherwise>
                            <logger level="WARN" doc:name="No Opportunity Found"
                                message="No open Opportunity found for order #[vars.orderNumber]" />
                        </otherwise>
                    </choice>
                </when>
            </choice>
            <error-handler>
                <on-error-continue type="ANY" logException="true"
                                   doc:name="Opportunity Error">
                    <set-variable variableName="opportunityId" value="" />
                    <set-variable variableName="retryable" value="#[true]" />
                </on-error-continue>
            </error-handler>
        </try>

        <!-- Stage 5b: Create Case (only if no existing case from idempotency check)
             until-successful retries the create up to 2 times before throwing. -->
        <try doc:name="Create Case">
            <choice doc:name="Can Create New Case?">
                <when expression='#[vars.httpStatus == 200
                                   and (vars.failureClass default "NONE") == "NONE"
                                   and (vars.caseId default "") == ""]'>
                    <until-successful maxRetries="2" millisBetweenRetries="1000"
                                      doc:name="Retry Case Create">
                        <salesforce:create type="Case" doc:name="Create Case"
                                           config-ref="Salesforce_Config">
                            <salesforce:records>#[[{
                                "Subject":     "Return Request - Key " ++ vars.idempotencyKey,
                                "Description": vars.reason,
                                "Origin":      "Web",
                                "Status":      "New",
                                "Priority":    "High"
                            }]]</salesforce:records>
                        </salesforce:create>
                    </until-successful>
                    <choice doc:name="Case SaveResult Success?">
                        <when expression='#[((payload.items[0].payload.success default false)
                                            or (payload.items[0].successful default false))
                                           and ((payload.items[0].payload.id
                                               default payload.items[0].id default "") != "")]'>
                            <set-variable variableName="caseId"
                                value='#[payload.items[0].payload.id
                                         default payload.items[0].id default ""]'
                                doc:name="Save Case ID From SaveResult" />
                            <set-variable variableName="agentStatus"
                                value="CASE_CREATED" />
                            <set-variable variableName="actionType"
                                value="CREATE_CASE" />
                            <logger level="INFO" doc:name="Log Case Created"
                                message='#[write({sourceApp: "service-cloud-mcp",
                                    stage: "CASE_CREATE", status: "SUCCESS",
                                    caseId: vars.caseId}, "application/json")]' />
                        </when>
                        <otherwise>
                            <set-variable variableName="httpStatus" value="#[500]" />
                            <set-variable variableName="agentStatus" value="FAILED" />
                            <set-variable variableName="failureClass"
                                value="TECHNICAL_SALESFORCE" />
                            <set-variable variableName="retryable" value="#[true]" />
                            <set-variable variableName="errorCode"
                                value="SFDC_CREATE_TECHNICAL_FAILURE" />
                            <logger level="ERROR" doc:name="Log Case SaveResult Error"
                                message="Case create did not return success=true" />
                        </otherwise>
                    </choice>
                </when>
            </choice>
            <error-handler>
                <on-error-continue type="ANY" logException="true"
                                   doc:name="Case Creation Error">
                    <set-variable variableName="httpStatus" value="#[500]" />
                    <set-variable variableName="agentStatus" value="FAILED" />
                    <set-variable variableName="failureClass"
                        value="TECHNICAL_SALESFORCE" />
                    <set-variable variableName="retryable" value="#[true]" />
                    <set-variable variableName="decisionHint"
                        value="RETRY_TECHNICAL_FAILURE" />
                    <set-variable variableName="errorCode"
                        value="SFDC_CREATE_EXCEPTION" />
                    <set-variable variableName="errorMessage"
                        value='#[error.description default error.errorType.identifier
                                  default "Case creation failed"]' />
                    <logger level="ERROR" doc:name="Log Case Error"
                        message='#[write({sourceApp: "service-cloud-mcp",
                            stage: "CASE_CREATE", status: "FAIL",
                            message: vars.errorMessage}, "application/json")]' />
                </on-error-continue>
            </error-handler>
        </try>

        <!-- Stage 5c: Update Opportunity with refund fields
             Only runs if both caseId and opportunityId are present.
             Failure is non-fatal: sets opportunityUpdateFailed=true, case still returned. -->
        <try doc:name="Update Opportunity">
            <choice doc:name="Can Update Opportunity?">
                <when expression='#[vars.httpStatus == 200
                                   and (vars.failureClass default "NONE") == "NONE"
                                   and (vars.opportunityId default "") != ""
                                   and (vars.caseId default "") != ""]'>
                    <salesforce:update type="Opportunity" doc:name="Update Opportunity"
                                       config-ref="Salesforce_Config">
                        <salesforce:records>#[[{
                            "Id":                      vars.opportunityId,
                            "Refund_Order_Number__c":  vars.orderNumber,
                            "Refund_Reason__c":        vars.reason,
                            "Refund_Case_Id__c":       vars.caseId,
                            "Refund_Agent_Status__c":  vars.agentStatus
                        }]]</salesforce:records>
                    </salesforce:update>
                    <set-variable variableName="agentStatus"
                        value="OPPORTUNITY_UPDATED" />
                    <logger level="INFO" doc:name="Log Opportunity Updated"
                        message='#[write({sourceApp: "service-cloud-mcp",
                            stage: "OPPORTUNITY_UPDATE", status: "SUCCESS"},
                            "application/json")]' />
                </when>
                <otherwise>
                    <logger level="INFO" doc:name="Skip Opportunity Update"
                        message="Skipping opportunity update. status=#[vars.httpStatus], opportunity=#[vars.opportunityId default 'none']" />
                </otherwise>
            </choice>
            <error-handler>
                <on-error-continue type="ANY" logException="true"
                                   doc:name="Opportunity Update Error">
                    <set-variable variableName="opportunityUpdateFailed"
                        value="#[true]" />
                    <set-variable variableName="retryable" value="#[true]" />
                    <set-variable variableName="decisionHint"
                        value="ACCEPT_CASE_RETRY_OPPORTUNITY_UPDATE" />
                    <set-variable variableName="errorCode"
                        value="SFDC_OPPORTUNITY_UPDATE_ERROR" />
                    <logger level="WARN" doc:name="Log Opportunity Update Error"
                        message='#[write({sourceApp: "service-cloud-mcp",
                            stage: "OPPORTUNITY_UPDATE", status: "FAIL"},
                            "application/json")]' />
                </on-error-continue>
            </error-handler>
        </try>

        <!-- Format and return the response -->
        <flow-ref name="mcp-format-response" doc:name="Format Response" />
    </flow>

</mule>
```

### G.4 — Create api.xml (HTTP listeners)

Create `src/main/mule/api.xml`. This wires the HTTP listener to the handler flow and adds health check endpoints:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mule xmlns:apikit="http://www.mulesoft.org/schema/mule/mule-apikit"
      xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:http="http://www.mulesoft.org/schema/mule/http"
      xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
http://www.mulesoft.org/schema/mule/http http://www.mulesoft.org/schema/mule/http/current/mule-http.xsd
http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd
http://www.mulesoft.org/schema/mule/mule-apikit http://www.mulesoft.org/schema/mule/mule-apikit/current/mule-apikit.xsd
http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd">

    <!-- APIkit router for RAML-validated requests -->
    <flow name="service-cloud-mcp-api-main">
        <http:listener config-ref="HTTP_Listener_config" path="/api/*" />
        <apikit:router config-ref="service-cloud-mcp-api-config" />
        <error-handler ref="global-default-error-handler" />
    </flow>

    <!-- APIkit-generated route -->
    <flow name="post:\mcp\tool\issue_credit:service-cloud-mcp-api-config">
        <flow-ref name="mcp-issue-credit-handler" />
        <error-handler ref="global-default-error-handler" />
    </flow>

    <!-- Direct MCP listener (bypasses APIkit validation — useful for testing) -->
    <flow name="mcp-issue-credit-flow">
        <http:listener config-ref="HTTP_Listener_config"
                       path="/mcp/tool/issue_credit" allowedMethods="POST">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 500]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>
        <flow-ref name="mcp-issue-credit-handler" />
        <error-handler ref="global-default-error-handler" />
    </flow>

    <!-- Health check -->
    <flow name="health-flow">
        <http:listener config-ref="HTTP_Listener_config" path="/health"
                       allowedMethods="GET">
            <http:response statusCode="200">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
        </http:listener>
        <ee:transform>
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{ status: "ok", app: "service-cloud-mcp" }]]></ee:set-payload>
            </ee:message>
        </ee:transform>
        <error-handler ref="global-default-error-handler" />
    </flow>

    <!-- Readiness probe: verifies Salesforce connectivity -->
    <flow name="health-ready-flow">
        <http:listener config-ref="HTTP_Listener_config" path="/health/ready"
                       allowedMethods="GET">
            <http:response statusCode="#[vars.httpStatus default 200]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:response>
            <http:error-response statusCode="#[vars.httpStatus default 503]">
                <http:headers>#[{"Content-Type": "application/json"}]</http:headers>
            </http:error-response>
        </http:listener>
        <set-variable variableName="httpStatus" value="#[200]" />
        <set-variable variableName="salesforceReady" value="#[true]" />
        <set-variable variableName="salesforceReason"
            value="Connectivity check passed" />
        <try>
            <salesforce:query config-ref="Salesforce_Config">
                <salesforce:salesforce-query>SELECT Id FROM User LIMIT 1</salesforce:salesforce-query>
            </salesforce:query>
            <error-handler>
                <on-error-continue type="ANY" logException="true">
                    <set-variable variableName="httpStatus" value="#[503]" />
                    <set-variable variableName="salesforceReady" value="#[false]" />
                    <set-variable variableName="salesforceReason"
                        value='#[error.description default "Salesforce connectivity check failed"]' />
                </on-error-continue>
            </error-handler>
        </try>
        <ee:transform>
            <ee:message>
                <ee:set-payload><![CDATA[%dw 2.0
output application/json
---
{
  status: if (vars.httpStatus == 200) "ready" else "not_ready",
  app: "service-cloud-mcp",
  dependencies: {
    salesforce: {
      status: if (vars.salesforceReady) "UP" else "DOWN",
      reason: vars.salesforceReason
    }
  }
}]]></ee:set-payload>
            </ee:message>
        </ee:transform>
        <error-handler ref="global-default-error-handler" />
    </flow>

</mule>
```

---

## Verification

### Verify data-cloud-sapi

```bash
# Health
curl -s http://localhost:8083/health | jq .

# Readiness (checks Data Cloud connectivity)
curl -s http://localhost:8083/health/ready | jq .

# Profile lookup — mapped Slack ID
curl -s "http://localhost:8083/api/profile/U0AA9JSR2AD" \
  -H "x-user-id: U0AA9JSR2AD" \
  -H "x-request-id: ex5-001" | jq .

# Profile lookup — unknown Slack ID (should return graceful fallback)
curl -s "http://localhost:8083/api/profile/U_UNKNOWN" \
  -H "x-user-id: U_UNKNOWN" | jq .
# Expected: identityConfidence=LOW, recommendedAction=CLARIFY
```

For CloudHub deployments, replace `localhost:8083` with the deployed hostname:

```bash
curl -s "https://{data-cloud-sapi-host}/api/profile/{slackUserId}" \
  -H "x-user-id: {slackUserId}" | jq .
```

### Verify service-cloud-mcp

```bash
# Health
curl -s http://localhost:8084/health | jq .

# Readiness (checks Salesforce connectivity)
curl -s http://localhost:8084/health/ready | jq .

# Valid request — should return status=SUCCESS, agentStatus=CASE_CREATED
curl -s -X POST http://localhost:8084/mcp/tool/issue_credit \
  -H "Content-Type: application/json" \
  -H "x-user-id: U0AA9JSR2AD" \
  -H "x-request-id: ex5-002" \
  -d '{
    "customerId": "C001",
    "orderNumber": "ORD-123",
    "amount": 50.00,
    "reason": "wrong item received"
  }' | jq .

# Idempotency — run the exact same request a second time
# Expected: status=SUCCESS, agentStatus=CASE_REUSED, same caseId as first call
curl -s -X POST http://localhost:8084/mcp/tool/issue_credit \
  -H "Content-Type: application/json" \
  -H "x-user-id: U0AA9JSR2AD" \
  -H "x-request-id: ex5-003" \
  -d '{
    "customerId": "C001",
    "orderNumber": "ORD-123",
    "amount": 50.00,
    "reason": "wrong item received"
  }' | jq .

# Risk gate — 999-prefix order with fraudScore >= 70
# Expected: status=REJECTED, agentStatus=REJECTED_RISK,
#           decisionHint=REJECT_AND_ESCALATE_FRAUD_REVIEW, HTTP 200
curl -s -X POST http://localhost:8084/mcp/tool/issue_credit \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "C001",
    "orderNumber": "999-001",
    "amount": 50.00,
    "fraudScore": 95,
    "reason": "test"
  }' | jq .

# Input validation — missing required field
# Expected: status=REJECTED, agentStatus=REJECTED_INPUT,
#           missingFields=["amount"], HTTP 200
curl -s -X POST http://localhost:8084/mcp/tool/issue_credit \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "C001",
    "orderNumber": "ORD-456"
  }' | jq .
```

For CloudHub deployments:

```bash
curl -s -X POST "https://{service-cloud-mcp-host}/mcp/tool/issue_credit" \
  -H "Content-Type: application/json" \
  -H "x-user-id: {userId}" \
  -d '{"customerId":"C001","orderNumber":"ORD-123","amount":50.00,"reason":"wrong item"}' \
  | jq .
```

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| `SDC:UNAUTHORIZED` on startup | `consumerKey` or `consumerSecret` is wrong, or secure property decryption key does not match | Re-encrypt credentials with the correct key; verify `secure.key` JVM arg matches |
| `SDC:CONNECTIVITY` during profile query | Data Cloud endpoint unreachable or token endpoint wrong | Confirm `sfdc.tokenEndpoint` points to your org's Data Cloud token endpoint, not the standard Salesforce login URL |
| Profile returns `identityConfidence: LOW` for a known user | SlackId not in static map and Slack API call failed | Add the Slack ID to the `slackToEmailMap` in `resolve-customer-context-subflow`, or verify the Slack bot token |
| `SALESFORCE:INVALID_INPUT` on case create | Required Case field missing or custom validation rule triggered | Check the Salesforce org for active validation rules on the Case object; confirm `Status` picklist includes `New` |
| `agentStatus=REJECTED_RISK` when not expected | `orderNumber` starts with `999` and `fraudScore` in request body is >= 70 | Use a different order number prefix, or do not include `fraudScore` in the request body |
| `agentStatus=CASE_REUSED` on first call | A Case with matching Subject already exists from a previous test run | Delete the old Case in Salesforce, or use a different `customerId`/`orderNumber`/`amount` combination |
| `opportunityUpdateFailed=true` in response | No open Opportunity found, or the four custom fields do not exist on the Opportunity object | Verify custom fields were created (Part F.4) and are on the page layout |
| HTTP 500 from `service-cloud-mcp` | Technical Salesforce failure — `SALESFORCE:CONNECTIVITY` or `SALESFORCE:INVALID_SESSION_ID` | Check CloudHub logs; verify `sfdc.tokenEndpoint` is the correct Salesforce instance URL |
| `APIKIT:BAD_REQUEST` (400) | Request body does not match the RAML `IssueCreditRequest` type | Confirm the request includes `customerId`, `orderNumber`, `amount` (required RAML fields) and `Content-Type: application/json` |
| App starts but `/mcp/tool/issue_credit` returns 404 | `api.xml` flow name does not match APIkit-generated name | Check that the flow named `post:\mcp\tool\issue_credit:service-cloud-mcp-api-config` exists in `api.xml` |
