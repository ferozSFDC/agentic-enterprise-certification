# Job Task Analysis: Architecting and Developing an Agentic Enterprise

## Job Role Definition

**Title:** MuleSoft Agentic Enterprise Architect / Developer

**Summary:** Designs, builds, deploys, and governs multi-system agentic solutions that use AI reasoning (LLMs, Bedrock Agents) within enterprise-grade MuleSoft integration networks. Implements API-led connectivity patterns where the Process layer orchestrates AI decision-making constrained by deterministic policy guardrails, the Experience layer adapts human channels (Slack, chat) into structured requests, and System APIs expose backend capabilities as governed tools that agents can invoke.

**Distinguishing Characteristics:**
- This role goes BEYOND traditional MuleSoft development (which focuses on connectors, transformations, and deployment)
- This role goes BEYOND pure AI/ML engineering (which focuses on model training and prompt tuning)
- This role sits at the intersection: **enterprise integration architecture + applied AI governance**
- The practitioner must make judgment calls about where AI adds value vs. where deterministic logic is safer, cheaper, and more auditable

**Recommended Experience:**
- 2+ years building Mule 4 applications (connectors, DataWeave, CloudHub)
- Familiarity with Salesforce platform (Service Cloud, Data Cloud, Connected Apps, OAuth)
- Exposure to at least one LLM provider (Bedrock, OpenAI, Anthropic)
- Understanding of enterprise resilience patterns (retry, circuit breaker, DLQ)

---

## Rationale: Why 8 Duty Areas and How Weights Were Derived

### Methodology

This JTA was constructed by triangulating three evidence sources:

1. **Course content analysis** — 9 instructional modules (slide decks + hands-on exercises) were reviewed to identify every distinct skill cluster the course teaches. Modules that share a single skill cluster were merged; modules that span multiple clusters were split.

2. **Reference implementation analysis** — 4 production-grade MuleSoft applications (slack-agent-router, ai-orchestrator, data-cloud-sapi, service-cloud-mcp) were examined at the code level to identify what a practitioner actually builds, configures, and debugs on the job. Each app's responsibility boundary informed duty area boundaries.

3. **Target persona validation** — The role is defined as a Hybrid (Architect + Builder) who both designs and implements. This means the JTA must include both "decide/design" tasks (architecture, governance) AND "build/configure" tasks (Salesforce setup, Bedrock configuration, deployment). A pure-architect cert would omit areas 2, 4, 6, 8. A pure-developer cert would under-weight areas 1, 7.

### Why 8 Areas (Not Fewer, Not More)

The 8 duty areas map to **8 distinct job activities** — each with its own tools, decisions, and failure modes. Merging any two would obscure a critical skill boundary; splitting any further would create areas too narrow to generate meaningful exam items.

| Candidate merge | Why it was rejected |
|----------------|-------------------|
| Merge 1 (Architecture) + 7 (Governance) | Architecture decisions happen at design time (where does AI go?). Governance happens at platform/runtime time (what policies enforce the design?). Different tools, different stakeholders, different failure modes. An architect who can design but not govern — or vice versa — has a gap. |
| Merge 2 (Experience) + 3 (Process) | Experience layer skills are channel-specific (Slack constraints, async ack, modal state). Process layer skills are channel-agnostic (pipeline orchestration, policy enforcement, AI fallback). Practitioners who excel at one often struggle with the other. The ai-orchestrator has zero awareness of Slack; the slack-agent-router has zero awareness of refund policy. |
| Merge 4 (System APIs) + 6 (Salesforce Config) | System API design (contract patterns, idempotency, HTTP 200 philosophy) is platform-agnostic — it applies whether the backend is Salesforce, SAP, or a database. Salesforce configuration (DMO mapping, Identity Resolution, Connected Apps) is platform-specific procedural knowledge. A practitioner might design excellent System APIs against a mock but fail to configure Data Cloud correctly. |
| Merge 5 (AI Services) + 3 (Process Orchestration) | Configuring Bedrock Agents and the AI Gateway is setup/wiring work (Action Groups, Lambda contracts, SigV4). Process orchestration is runtime logic (multi-stage pipeline, circuit breakers, DLQ). You configure AI once; you orchestrate it on every request. |
| Split 3 (Process) into "AI Reasoning" + "Policy Enforcement" | These are intentionally coupled. The entire point of "guided determinism" is that AI and policy work together in one pipeline. Testing them separately would miss the critical judgment: knowing when AI proposes something that policy must override. |

### How Weights Were Assigned

Weights reflect three factors, scored independently and then averaged:

**Factor 1: Consequence of Incompetence (What breaks if this skill is missing?)**

| Rating | Meaning | Example |
|--------|---------|---------|
| Critical | Data loss, unauthorized actions, security breach | Process Orchestration — missing policy gates allow AI to approve fraudulent refunds |
| High | System failure, degraded service, compliance violation | Architecture — wrong layer boundaries create unmaintainable spaghetti |
| Medium | Suboptimal performance, manual workarounds needed | Deploy — wrong order causes startup failures but is recoverable |
| Low | Cosmetic, inconvenient, easily fixed | Message formatting issues in Slack |

**Factor 2: Frequency of Activity (How often does the practitioner do this?)**

| Rating | Meaning |
|--------|---------|
| Every request | Happens on every inbound event (dedup, orchestration, policy check) |
| Every project | Done once per project but foundational (architecture, governance setup) |
| Per deployment | Done each time code goes to production |
| Per system/channel | Done once when onboarding a new backend or channel |

**Factor 3: Breadth of Knowledge Required (How many concepts must the candidate juggle?)**

Measured by the number of distinct technical concepts, tools, and decision points within the duty area.

### Weight Derivation Table

| Duty Area | Consequence | Frequency | Breadth | Resulting Weight | Justification |
|-----------|-------------|-----------|---------|-----------------|---------------|
| **3. Process Orchestration** | Critical — unauthorized mutations if missing | Every request — runs on each event | Highest — 12 tasks spanning AI invocation, circuit breakers, DLQ, policy, dedup, risk, grounding, failure taxonomy | **20%** | This is the "brain" of the system. Every other layer feeds into or is called from here. It requires the deepest judgment about when AI should decide vs. when rules should override. Mistakes are irreversible (refunds issued, cases created). |
| **1. Architecture Design** | High — wrong boundaries create technical debt that affects every subsequent decision | Every project — done at inception, referenced throughout | High — 7 tasks across layer classification, protocol selection, identity chains, design principles | **15%** | Architecture is foundational but happens once. It sets the ceiling for everything else. Without this, practitioners build working code that's architecturally incoherent. Weight reflects the "force multiplier" effect — a good architecture makes every other area easier. |
| **4. System APIs as Tools** | High — broken contracts or missing idempotency cause duplicate actions and data corruption | Per system — built once per backend but called on every request | High — 10 tasks spanning Salesforce connectors, caching, idempotency, MCP contracts, risk gates, grounding responses | **15%** | System APIs are the hands of the system — they do the actual work. If they lack idempotency, the AI orchestrator creates duplicate Cases. If they return HTTP 500 instead of 200-with-rejection, upstream circuit breakers trip unnecessarily. Two apps in the reference architecture (data-cloud-sapi, service-cloud-mcp) are System APIs. |
| **2. Experience Layer** | High — user-facing failures (dropped messages, duplicate actions from retries) | Per channel — built once per channel but processes every inbound event | Medium — 7 tasks focused on async patterns, dedup, AI extraction, modals | **12%** | The Experience layer is the "face" of the system but its scope is narrower than Process or System layers. It requires specific Slack knowledge (3-second ack, modals, private_metadata) and dedup patterns, but doesn't involve the deep AI/policy judgment of Area 3. |
| **5. AI Services** | High — misconfigured agents produce wrong decisions at scale; security gaps in IAM expose model access | Per AI agent — configured once, invoked many times | Medium — 8 tasks spanning Bedrock Agents, Lambda, AI Gateway, Agent Scanner, IAM | **12%** | This is "AI infrastructure wiring" — critical to get right but done less frequently than orchestration or System API development. Weight matches Area 2 because both are "configure once, invoke often" domains with similar breadth. |
| **6. Salesforce Config** | High — wrong DMO mapping causes silent failures (no error, just empty results); broken Connected Apps block all auth | Per org — done once during setup | Medium — 7 tasks focused on Data Cloud, Identity Resolution, Connected Apps, Flows | **10%** | Salesforce configuration is procedural — there's a right way and many wrong ways, but the decision space is narrower than architecture or orchestration. The "silent failure" risk (wrong Party field mapping returns zero results with no error) makes it critical to test, but the scope is contained to one platform. |
| **7. Governance** | High — ungoverned agents consume unlimited tokens, bypass security policies, operate without audit trail | Per deployment — configured at platform level, evolves as agent portfolio grows | Medium — 7 tasks spanning Agent Fabric, policy library, agent-network.yaml, MCP Bridge, observability | **10%** | Governance is the "enterprise layer" that separates a demo from production. It's high-consequence but narrower in breadth than Process Orchestration. Weight matches Area 6 because both are "configure the platform" activities — one for Salesforce, one for Anypoint. |
| **8. Deploy and Operate** | Medium — wrong deploy order causes temporary failures but is recoverable; missing health probes delay detection | Per deployment — done each release cycle | Low — 6 tasks focused on deployment order, properties, health, monitoring | **6%** | Deployment is important but well-understood territory for anyone with MuleSoft experience. The agentic-specific aspects (multi-app ordering, DLQ monitoring) are a thin layer on top of standard CloudHub 2.0 skills. The MQC should already know basic deployment; we're testing the agentic-specific increments only. |

### Validation Criteria

A stakeholder reviewing these weights should verify:

1. **Does the highest-weighted area (Process Orchestration, 20%) represent the highest-consequence, highest-frequency, highest-breadth skill?** — Yes. This is where AI decisions become irreversible actions, where policy enforcement overrides AI, and where 12 distinct patterns must be mastered.

2. **Does the lowest-weighted area (Deploy/Operate, 6%) represent skills that are largely pre-existing for the target candidate?** — Yes. The MQC already knows CloudHub deployment; only the agentic-specific increments (multi-app ordering, DLQ monitoring) are new.

3. **Do equal-weight areas (2=5 at 12%, 6=7 at 10%) share similar consequence/frequency/breadth profiles?** — Yes. Areas 2 and 5 are both "configure once, invoke often" domains. Areas 6 and 7 are both "platform configuration" domains (Salesforce vs. Anypoint).

4. **Does the sum match the course investment?** — Roughly. Module 5 (Process Layer) is the longest instructional module. Module 7 (Deployment) is the shortest hands-on exercise. The weights track the relative depth of instruction.

5. **Would removing any area leave a blind spot in the certified candidate's skill set?** — Yes. Each area represents a distinct failure mode that cannot be covered by competence in the other seven areas.

---

## Duty Area 1: Design Agentic Architecture Using API-Led Connectivity

**Weight: ~15%**

*The practitioner must be able to determine WHERE intelligence belongs in the integration network and WHY each layer exists.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 1.1 | Classify components into Experience, Process, and System layers based on their responsibility in an agentic network | High | Every project |
| 1.2 | Determine which stages of a pipeline require AI reasoning vs. deterministic logic, applying the "guided determinism" principle | High | Every project |
| 1.3 | Design the contract between layers (request/response envelopes, header propagation, metadata fields) so that each layer can evolve independently | High | Every project |
| 1.4 | Define the On-Behalf-Of (OBO) identity propagation chain from the human channel through all downstream services | High | Every project |
| 1.5 | Select the appropriate protocol for each integration point (REST, MCP tool, streaming agent invocation, event push) based on the interaction pattern | Medium | Every project |
| 1.6 | Map enterprise design principles (fail safe, deterministic guardrails, idempotent by default, observable, secure by construction, same artifact different config) to implementation decisions | High | Every project |
| 1.7 | Identify which components in an agentic network should be registered as Agent/Tool Instances vs. governed as standard APIs | Medium | Per deployment |

### Knowledge Required
- API-led connectivity (Experience / Process / System) and how it evolves for agentic use
- Guided determinism: AI for reasoning, deterministic for validation/routing/enforcement
- MCP (Model Context Protocol) as a tool contract standard
- OBO identity patterns and header-based context propagation
- Agent Fabric concepts: Agent and Tool Instances, protocol types (MCP Server, Agent/A2A, LLM)

---

## Duty Area 2: Implement Experience Layer Integration (Channel Adapters)

**Weight: ~12%**

*The practitioner must be able to bridge human interaction channels (Slack, chat, etc.) to the agentic network while handling the real-time constraints of those channels.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 2.1 | Implement webhook endpoints that acknowledge events within platform time constraints (e.g., Slack's 3-second requirement) using async processing patterns | High | Per channel |
| 2.2 | Deduplicate incoming events using persistent Object Store to prevent duplicate downstream actions from at-least-once delivery guarantees | High | Per channel |
| 2.3 | Extract structured fields from natural language input using an AI model (via AI Gateway) with graceful fallback when AI is unavailable | Medium | Per use case |
| 2.4 | Build interactive confirmation flows (modals, buttons) that carry correlation context across stateless interactions using serialized metadata | Medium | Per use case |
| 2.5 | Resolve user identity from the channel platform (e.g., Slack user ID to email) and propagate it as OBO headers for downstream authorization | High | Per channel |
| 2.6 | Implement circuit breaker protection on downstream service calls to prevent cascading failures from slow AI or orchestration services | High | Per integration |
| 2.7 | Format agent responses for the target channel, translating structured metadata (stage status, case IDs, decisions) into human-readable messages | Low | Per channel |

### Knowledge Required
- Slack Events API, slash commands, interactivity (modals/buttons), Bot Token scopes
- Async processing: acknowledge immediately, process in background, update via API
- Event deduplication strategies (Object Store with TTL vs. retry headers)
- AI-powered field extraction (prompt engineering for structured output)
- Circuit breaker state machine (CLOSED/OPEN/HALF_OPEN)
- Stateless interaction patterns (private_metadata serialization)

---

## Duty Area 3: Build AI-Powered Process Orchestration

**Weight: ~20%**

*The practitioner must be able to build the "brain" — the Process layer that reasons about requests, assesses risk, enforces policy, and decides whether to act. This is the highest-weight area because it requires the deepest judgment about AI + enterprise safety.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 3.1 | Design a multi-stage orchestration pipeline where each stage has clear entry/exit criteria and observable status (OK, FAIL, DEGRADED, SKIPPED) | High | Every project |
| 3.2 | Implement request deduplication at the Process layer using a persistent Object Store with appropriate TTL to prevent duplicate AI calls and mutations | High | Every project |
| 3.3 | Enrich AI prompts with real customer context (loyalty tier, churn risk, purchase history) fetched from System APIs, and cache that context to reduce cost and latency | High | Per use case |
| 3.4 | Invoke an AI model (via AI Gateway or direct SDK) to perform risk assessment, passing structured context and receiving a typed decision (APPROVE/DENY/ESCALATE/CLARIFY) | High | Per use case |
| 3.5 | Implement a multi-tier fallback chain (primary gateway, direct SDK fallback, deterministic mimic) so the system never leaves the user without a response | High | Per AI integration |
| 3.6 | Implement a circuit breaker around AI service calls, tracking failure counts in Object Store with configurable threshold and cooldown | High | Per AI integration |
| 3.7 | Enforce deterministic policy rules AFTER AI reasoning — overriding AI suggestions when they violate business constraints (refund caps, velocity limits, missing identity) | Critical | Every project |
| 3.8 | Gate irreversible mutations behind multiple conditions (approved decision + valid identity + complete payload + policy match) to prevent unauthorized actions | Critical | Every project |
| 3.9 | Persist failed mutations to a Dead Letter Queue with compensation metadata (timestamp, correlation IDs, error classification, retryable flag) for manual replay | High | Every project |
| 3.10 | Classify failures using a taxonomy (POLICY_REJECTED, GATEWAY_DEGRADED, BEDROCK_UNAVAILABLE, SERVICE_CLOUD_REJECTED, etc.) to enable targeted retry and alerting strategies | Medium | Every project |
| 3.11 | Resolve business data (refund amounts, order details) from Salesforce or other systems of record, sanitizing inputs to prevent injection attacks | High | Per use case |
| 3.12 | Build the final response envelope with both a human-readable response and machine-readable metadata (gates, stage status, decision source, fallback indicators) | Medium | Every project |

### Knowledge Required
- Multi-stage pipeline design with variable initialization and safe defaults
- AI Gateway invocation patterns (OpenAI-compatible and Anthropic-compatible API styles)
- Amazon Bedrock Agent Runtime: streaming API, Action Groups, Return Control
- Circuit breaker pattern: state machine, Object Store persistence, cooldown logic
- Policy enforcement: deterministic rules that override probabilistic AI decisions
- Dead Letter Queue design: what to store, TTL, compensation flags, alerting
- SOQL injection prevention (input sanitization before query construction)
- DataWeave library functions for reusable business logic (policy rules, risk normalization, response envelopes)
- Failure taxonomy design for observability and automated retry routing

---

## Duty Area 4: Develop System APIs as Agent Tools

**Weight: ~15%**

*The practitioner must be able to wrap backend systems (Salesforce, databases, SaaS) as governed tools that any orchestrator or AI agent can invoke through a stable contract.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 4.1 | Design a System API that executes actions without making decisions — reporting outcomes via response fields (status, decisionHint, failureClass) rather than HTTP status codes | High | Per system |
| 4.2 | Implement the "HTTP 200 for all business outcomes" pattern so upstream orchestrators can read the full response body regardless of whether the action succeeded or was rejected | High | Per system |
| 4.3 | Implement idempotency at the System API layer using a deterministic key derived from request parameters, preventing duplicate actions on retry | High | Per mutation endpoint |
| 4.4 | Implement a risk gate that blocks execution based on fraud signals received from the orchestrator (e.g., order prefix patterns + fraud score thresholds) | High | Per mutation endpoint |
| 4.5 | Authenticate to Salesforce using OAuth 2.0 Client Credentials (both SDC connector and Salesforce connector variants) and handle token refresh transparently | High | Per Salesforce integration |
| 4.6 | Query Salesforce Data Cloud using the two-step pattern (email to Party ID via Contact Point Email, Party ID to Individual profile) for customer context resolution | High | Per Data Cloud integration |
| 4.7 | Implement Object Store caching for expensive queries (Data Cloud, external APIs) with appropriate TTL and cache invalidation on state-changing mutations | Medium | Per read endpoint |
| 4.8 | Define an MCP tool contract (agent-network.yaml) specifying tool name, description, input schema, and output schema so AI agents can discover and invoke the tool | Medium | Per tool |
| 4.9 | Create and update Salesforce objects (Cases, Opportunities) with retry logic (until-successful) and validate SaveResult responses for partial failures | High | Per Salesforce mutation |
| 4.10 | Build a grounding response that translates raw system data into agent-consumable context (customerTier, churnRisk, identityConfidence, recommendedAction, knownUnknowns) | Medium | Per context API |

### Knowledge Required
- System API design principles: execute never decide, 200 for business outcomes, 5xx for technical failures only
- Salesforce Data Cloud: Data Streams, DMO mapping, Identity Resolution, SQL API (ssot__ objects)
- Salesforce Service Cloud: Case/Opportunity CRUD, Autolaunched Flows, Connected Apps
- OAuth 2.0 Client Credentials grant (token endpoint, Run As user, scope configuration)
- MCP tool schema specification (agent-network.yaml)
- Idempotency key design and SOQL-based duplicate detection
- Object Store caching: TTL selection, eviction, invalidation patterns
- Grounding response design: confidence levels, recommended actions, known unknowns

---

## Duty Area 5: Configure Enterprise AI Services

**Weight: ~12%**

*The practitioner must be able to set up and configure the AI services that the agentic network consumes — not train models, but wire them into the enterprise fabric with proper governance.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 5.1 | Configure an Amazon Bedrock Agent with foundation model selection, natural-language instructions that enforce tool ordering, and Action Groups that invoke Lambda functions | High | Per AI agent |
| 5.2 | Implement a Lambda function that conforms to Bedrock's Action Group response contract (messageVersion, actionGroup, function, functionResponse with TEXT body) | High | Per action group |
| 5.3 | Configure an Agent and Tool Instance on the Omni Gateway (AI Gateway) with Client-ID-Enforcement, SigV4 credential signing, and upstream model routing | High | Per LLM endpoint |
| 5.4 | Set up an Agent Scanner to discover AI agents across cloud providers and publish their metadata to Anypoint Exchange for enterprise-wide visibility | Medium | Per cloud account |
| 5.5 | Create IAM credentials with least-privilege policies separating full development access from scanner-only read access | High | Per cloud account |
| 5.6 | Write Bedrock Agent instructions that enforce mandatory tool ordering through natural language (MUST call X before Y, NEVER proceed without Z) | High | Per AI agent |
| 5.7 | Test AI agent behavior for both happy-path and adversarial scenarios (safe orders, fraudulent orders, missing parameters) to verify instruction compliance | High | Per AI agent |
| 5.8 | Invoke a Bedrock Agent programmatically via the AWS SDK (streaming API, session management, timeout handling) as a fallback when the AI Gateway is unavailable | Medium | Per fallback implementation |

### Knowledge Required
- Amazon Bedrock: Agents, Action Groups, Foundation Models, Aliases, Versions
- Lambda function development for Bedrock Action Groups (response contract)
- MuleSoft AI Gateway: Agent and Tool Instance configuration (Runtime, Downstream, Upstream)
- Agent Scanner: discovery mechanism, Exchange publication, daily sync
- AWS IAM: users, policies, access keys, least-privilege principle
- Bedrock Agent instruction engineering: mandatory/prohibitive phrasing
- Bedrock Agent Runtime API: InvokeAgent, streaming protocol, ReturnControlPayload

---

## Duty Area 6: Manage Salesforce Platform for Agentic Context and Action

**Weight: ~10%**

*The practitioner must be able to configure the Salesforce org that provides customer context (Data Cloud) and action execution (Service Cloud) for the agentic network.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 6.1 | Configure Data Cloud data ingestion (Data Streams) from CRM objects, selecting only the fields needed for agent grounding to minimize noise and ingestion time | High | Per data source |
| 6.2 | Map Data Lake Objects to Data Model Objects (Individual, Contact Point Email) ensuring the Party field links correctly from Contact ID (not Email) to enable Identity Resolution | Critical | Per data source |
| 6.3 | Configure Identity Resolution rules (match rules, reconciliation rules) and run the resolution process to produce Unified Individuals queryable via the SQL API | High | Per org |
| 6.4 | Create custom fields on Data Model Objects with correct API names that match downstream query expectations (e.g., LoyaltyTier not Loyalty_Tier) | High | Per custom field |
| 6.5 | Create a Connected App with OAuth 2.0 Client Credentials flow, configure the Run As user, relax IP restrictions for CloudHub, and add required scopes (api, cdp_profile_api, cdp_query_api) | High | Per org |
| 6.6 | Build an Autolaunched Flow that executes agent actions (e.g., create a Case from input variables) and verify it is callable via the REST API | Medium | Per action |
| 6.7 | Verify Data Cloud queries return expected results using the two-step pattern and troubleshoot common silent failures (wrong Party mapping, missing refresh, custom field name mismatch) | High | Per deployment |

### Knowledge Required
- Data Cloud architecture: Data Streams, Data Lake Objects, Data Model Objects, Identity Resolution
- DMO mapping canvas: Individual, Contact Point Email, Party field relationship
- Identity Resolution: match rules (exact email), reconciliation rules (source priority, most frequent)
- Connected App configuration: OAuth scopes, Client Credentials flow, Run As user, IP relaxation
- Salesforce Flow: Autolaunched flows, input variables, Get Records, Create Records
- My Domain token endpoint (not login.salesforce.com)
- Common silent failures: Party mapped to Email (not Contact ID), missing data refresh, DMO field name mismatch

---

## Duty Area 7: Govern Agents at Enterprise Scale

**Weight: ~10%**

*The practitioner must be able to apply governance controls across an enterprise agent portfolio using Agent Fabric — ensuring security, compliance, cost control, and observability at the platform level.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 7.1 | Classify each component in an agentic network by its Agent Fabric protocol type (MCP Server, Agent/A2A, LLM) and determine which require gateway governance vs. standard API management | High | Per deployment |
| 7.2 | Apply governance policies from the Agent Fabric policy library (PII Handling, Input Validation, Rate Limiting, Cost Threshold Alert, OAuth 2.0 OBO Credential Injection) to Agent and Tool Instances | High | Per instance |
| 7.3 | Define an agent-network.yaml that declares tools, their schemas, security requirements, and gateway routing — enabling declarative governance via version control | Medium | Per network |
| 7.4 | Configure observability for token usage attribution (cost by provider, model, business unit) and latency SLA tracking across the agent portfolio | Medium | Per environment |
| 7.5 | Use MCP Bridge to expose existing REST APIs as MCP servers without code for simple tool endpoints, and identify when hand-built MCP in Mule is required for custom logic | Medium | Per tool |
| 7.6 | Implement the six non-negotiable design principles (fail safe, deterministic guardrails, idempotent, observable, secure by construction, same artifact different config) at both application and platform levels | High | Every project |
| 7.7 | Distinguish between governance controls that belong in application code (business-policy.xml) vs. platform policies (Omni Gateway) and explain when each is appropriate | High | Every project |

### Knowledge Required
- Agent Fabric: four capabilities (Discover, Govern, Orchestrate, Observe)
- Omni Gateway (formerly Flex Gateway): runtime governance layer
- Governance policy library: access/security policies, performance/cost policies
- agent-network.yaml contract structure
- MCP Bridge: wizard flow for no-code MCP server creation
- Token cost observability: provider attribution, model distribution, business unit breakdown
- Agent Visualizer: end-to-end trace visualization
- Application-level vs. platform-level governance boundaries

---

## Duty Area 8: Deploy and Operate Agentic Networks

**Weight: ~6%**

*The practitioner must be able to deploy a multi-app agentic network to CloudHub 2.0 in the correct order, manage secrets, verify health, and monitor operational status.*

### Task Statements

| ID | Task Statement | Criticality | Frequency |
|----|---------------|-------------|-----------|
| 8.1 | Determine the correct deployment order for a multi-app network based on dependency flow (System APIs first, Process layer second, Experience layer last) | High | Per deployment |
| 8.2 | Implement a property strategy that separates non-sensitive defaults (YAML in JAR), environment-specific hosts (env-config.yaml), and secrets (Runtime Manager encrypted properties) | High | Per app |
| 8.3 | Configure health endpoints (liveness and readiness probes) that verify downstream dependency connectivity before accepting traffic | High | Per app |
| 8.4 | Verify end-to-end flow after deployment by executing the full path (Slack message → orchestration → Data Cloud → AI → Service Cloud → Case created) and confirming all stage statuses | High | Per deployment |
| 8.5 | Monitor DLQ alert frequency and failure classifications to identify degraded downstream services requiring attention | Medium | Ongoing |
| 8.6 | Manage CloudHub 2.0 deployment properties (vCore sizing, replicas, Shared Space targeting) and understand the implications of 0.1 vCore startup time on health probes | Medium | Per deployment |

### Knowledge Required
- CloudHub 2.0: Shared Space, deployment via Maven plugin, vCore sizing, startup behavior
- Property hierarchy: config.yaml < env-config.yaml < Runtime Manager properties
- Secure properties: encryption at rest, runtime key injection
- Health probes: liveness (is the JVM running) vs. readiness (can I serve traffic)
- Deployment dependency ordering
- End-to-end verification methodology
- DLQ monitoring and alerting patterns

---

## Cross-Cutting Knowledge Areas

These knowledge areas underpin multiple duty areas and are not isolated to a single domain:

| Area | Relevant Duty Areas | Description |
|------|-------------------|-------------|
| **DataWeave 2.0** | 2, 3, 4 | Transformation language used in every flow for JSON construction, regex extraction, conditional logic, library functions |
| **Object Store patterns** | 2, 3, 4, 8 | Persistent key-value storage for deduplication, caching, circuit breaker state, DLQ |
| **Correlation ID propagation** | 1, 2, 3, 4, 8 | x-request-id, x-flow-id, x-session-id, x-user-id headers flowing through all layers |
| **Error handling philosophy** | 2, 3, 4 | on-error-continue for graceful degradation vs. on-error-propagate for fatal failures |
| **TLS and credential management** | 4, 5, 6, 8 | Secure properties, keystores, OAuth token management, CloudHub TLS termination |
| **Structured telemetry** | 3, 7, 8 | key=value log format, stage-based tracking, failure classification for observability |

---

## Minimally Qualified Candidate (MQC) Profile

The MQC for this certification can **independently**:
- Design a 3-layer agentic architecture and justify where AI reasoning belongs
- Build the Process layer orchestration pipeline with policy enforcement and AI fallback
- Connect to Salesforce (Data Cloud + Service Cloud) with proper authentication and query patterns
- Configure Bedrock Agents and the MuleSoft AI Gateway for governed LLM access
- Deploy and verify a multi-app network on CloudHub 2.0
- Apply enterprise governance principles at both application and platform levels

The MQC **occasionally requires assistance** with:
- Complex Bedrock Agent instruction engineering for novel use cases
- Advanced Agent Fabric governance configurations (multi-org, multi-region)
- Performance tuning (connection pools, vCore sizing, cache TTL optimization)
- Custom Java extensions (e.g., BedrockDirectInvoker SDK integration)

**Beyond the MQC (too complex to assess in this exam):**
- Training or fine-tuning foundation models
- Salesforce Data Cloud segmentation and activation rules
- Network infrastructure (VPCs, private connectivity, DNS)
- Advanced AWS IAM (STS, cross-account roles, service control policies)
- Mule 4 custom connector development

**Below the MQC (too basic to assess):**
- Creating a basic Mule project in Anypoint Studio
- Writing simple DataWeave transformations
- Deploying a single app to CloudHub
- Basic Salesforce admin (creating objects, fields)
- General REST API concepts (HTTP methods, status codes)

---

## Summary Weighting

| Duty Area | Weight | Question Count (60-item exam) |
|-----------|--------|-------------------------------|
| 1. Design Agentic Architecture | 15% | 9 |
| 2. Experience Layer Integration | 12% | 7 |
| 3. AI-Powered Process Orchestration | 20% | 12 |
| 4. System APIs as Agent Tools | 15% | 9 |
| 5. Enterprise AI Services | 12% | 7 |
| 6. Salesforce Platform Configuration | 10% | 6 |
| 7. Agent Governance at Scale | 10% | 6 |
| 8. Deploy and Operate | 6% | 4 |
| **Total** | **100%** | **60** |

---

## Mapping to Course Modules

| Duty Area | Primary Course Module(s) |
|-----------|--------------------------|
| 1 | Module 1 (Why Agentic), Module 8 (Agent Fabric Governance) |
| 2 | Module 3 (Slack Experience Layer) |
| 3 | Module 5 (Process Layer — ai-orchestrator) |
| 4 | Module 6 (System APIs) |
| 5 | Module 4 (AI Gateway + Bedrock) |
| 6 | Module 2 (Salesforce Backbone) |
| 7 | Module 8 (Agent Fabric Governance) |
| 8 | Module 7 (Deployment + E2E Validation) |

---

## Notes for Exam Development

1. **Scenario-based questions preferred** — most tasks involve judgment calls (where to put AI, which fallback strategy, what response contract to use) not rote memorization
2. **"What would go wrong if..."** format tests understanding of silent failures (wrong Party mapping, missing identity, duplicate actions without idempotency)
3. **Architecture decision questions** test the boundary between AI reasoning and deterministic logic
4. **No pure code syntax questions** — test understanding of patterns and consequences, not memorization of XML tag names
5. **Cross-domain scenarios** are ideal — a single question can test architecture + resilience + governance simultaneously
