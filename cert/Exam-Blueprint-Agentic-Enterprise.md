# Exam Blueprint: Architecting and Developing an Agentic Enterprise

## Exam Metadata

| Field | Value |
|-------|-------|
| **Exam Title** | Salesforce Certified MuleSoft Agentic Enterprise Architect |
| **Exam Code** | TBD (pending PDD approval) |
| **Target Candidate** | Hybrid Architect + Builder — designs AND implements agentic enterprise systems |
| **Prerequisite** | Salesforce Certified MuleSoft Developer (SCMD) recommended |
| **Format** | Proctored, closed-book, single-select multiple choice |
| **Delivery Model** | Computerized Adaptive Testing (CAT) with SPRT classification |
| **Items per Session** | 5–40 (adaptive; algorithm determines length per candidate) |
| **Item Pool Size** | 180+ calibrated items (minimum viable: 120) |
| **Duration** | 120 minutes |
| **Decision** | PASS or FAIL (binary classification, no numeric score reported) |
| **Classification Method** | Sequential Probability Ratio Test (SPRT) with Wald boundaries |
| **Error Rates** | α ≤ 5% (false pass), β ≤ 5% (false fail) |
| **Expected Avg Length** | ~14 items (clear pass/fail: ~8–9; borderline: ~25) |
| **Delivery** | Custom CAT engine (cert-engine) via proctored web session |
| **Source Document** | JTA-Agentic-Enterprise.md |

### Classification Rationale

This exam uses **Computerized Adaptive Testing (CAT)** with **Sequential Probability Ratio Test (SPRT)** classification rather than a traditional fixed-form with raw cut score. Rationale:

1. **Shorter exams for most candidates.** Clearly passing candidates see ~8 items; clearly failing candidates see ~9. Only borderline cases approach the 40-item ceiling. Monte Carlo validation shows an average of 14 items per session — a 65% reduction vs. a 40-item fixed form.

2. **Statistical rigor.** SPRT provides a mathematically grounded confidence level for every decision. The exam accumulates evidence until it can classify PASS or FAIL at the specified error rates (α=0.05, β=0.05), or forces a decision at the ceiling using the final ability estimate vs. the cut score.

3. **Security.** No two candidates see the same item set. Adaptive selection from a 180+ item pool, combined with Sympson-Hetter exposure control (max 25% exposure rate per item), makes item harvesting infeasible.

4. **Candidate experience.** High-ability candidates are not forced through 40+ items testing content well below their level. The exam respects their time and reduces fatigue effects.

**Cut score (θ_c = 0.0)** was set using the 2PL IRT scale where 0.0 represents the minimally qualified candidate (MQC). The indifference region (δ=0.2) prevents SPRT oscillation for candidates very near the boundary. Final θ_c will be validated post-beta using a Modified Angoff procedure with SME panel, then translated to the IRT ability scale.

**Validation results (1000-candidate Monte Carlo simulation):**
- Classification accuracy: 96.6% (target >95%)
- False pass rate: 1.6% (target ≤5%)
- False fail rate: 1.8% (target ≤5%)
- Average test length: 13.9 items (8.1 clear pass, 8.8 clear fail, 25.1 borderline)
- Domain coverage: all 8 domains within ±1.2% of blueprint targets

---

## Cognitive Complexity (CC) Levels

Every objective is assigned a CC level that determines the depth of thinking required. This maps to Bloom's Taxonomy and directly influences item-writing style.

| CC Level | Bloom's Tier | What It Tests | Question Characteristics | Distribution Target |
|----------|-------------|---------------|-------------------------|-------------------|
| **CC2 — Application & Analysis** | Apply / Analyze | Apply a pattern to a scenario, determine what's needed given requirements, diagnose a configuration problem | "Given this scenario, which approach..." / "An architect needs to..." / "Given this failure, what is misconfigured..." | 60-65% of items |
| **CC3 — Evaluation & Judgment** | Evaluate / Create | Choose between competing approaches, diagnose root causes from symptoms, predict consequences of design decisions | "What would happen if..." / "Which combination addresses..." / "Given these trade-offs, which design..." | 35-40% of items |

**Target distribution for this exam:** CC2 = 45 items (75%), CC3 = 15 items (25%)

**Zero CC1 (Recall) items.** This is a deliberate design decision. Rationale:

1. **The target candidate is a Hybrid Architect + Builder.** If they can't apply knowledge to a scenario, recalling a definition has no value. Anyone who can apply a concept necessarily recalls it — testing recall separately wastes exam real estate.
2. **Pure recall tests study skill, not job skill.** Memorizing "what are the four Agent Fabric capabilities" doesn't predict whether someone can govern an agent network. Applying those capabilities to a governance gap does.
3. **Scenario-based items have higher discrimination.** CC2/CC3 items better separate qualified from unqualified candidates because they test the judgment that matters on the job — not vocabulary.
4. **This matches the course philosophy.** The course teaches through building, not lecture. Every concept is introduced in the context of a real system. The exam should mirror that.

---

## Domain Structure

### Domain 1: Agentic Architecture Design
**Weight: 15% | Items: 9 | Source: JTA Duty Area 1**

The candidate must be able to design multi-layer agentic architectures that separate concerns correctly, propagate identity, and apply enterprise design principles.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 1.1 | Given a set of components in an agentic system, classify each into the correct API-led connectivity layer (Experience, Process, System) and justify the placement based on its responsibility | CC2 | 2 |
| 1.2 | Given a pipeline with mixed decision types, determine which stages require AI reasoning vs. deterministic logic by applying the guided determinism principle | CC3 | 2 |
| 1.3 | Given a multi-service architecture, design the identity propagation chain (OBO headers: x-obo-user-id, x-user-id, x-request-id) from the human channel through all downstream services | CC2 | 2 |
| 1.4 | Given integration requirements, select the appropriate protocol (REST, MCP tool invocation, streaming agent, event push) for each connection point and explain trade-offs | CC2 | 1 |
| 1.5 | Given the six enterprise design principles (fail safe, deterministic guardrails, idempotent by default, observable, secure by construction, same artifact different config), evaluate which principles are violated in a given architecture | CC3 | 1 |
| 1.6 | Distinguish between components that should be registered as Agent/Tool Instances in Agent Fabric vs. governed as standard APIs based on their interaction pattern and protocol type | CC2 | 1 |

**Enabling Knowledge:**
- API-led connectivity layers and their evolution for agentic use
- Guided determinism: the principle that AI is used for reasoning while deterministic logic handles validation, routing, and enforcement
- MCP (Model Context Protocol) as a tool contract standard
- OBO identity propagation pattern: where headers are injected, where they're read, what happens if they're missing
- Agent Fabric protocol types: MCP Server, Agent/A2A, LLM

---

### Domain 2: Experience Layer Integration
**Weight: 12% | Items: 7 | Source: JTA Duty Area 2**

The candidate must be able to build channel adapters that bridge human interaction platforms to the agentic network while respecting real-time constraints and ensuring exactly-once processing.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 2.1 | Given a channel platform's constraints (e.g., Slack's 3-second acknowledgment requirement), design an async processing pattern that accepts events immediately and processes them in the background | CC2 | 1 |
| 2.2 | Given a scenario where duplicate events arrive (at-least-once delivery), implement a deduplication strategy using persistent Object Store with appropriate TTL and key derivation | CC2 | 2 |
| 2.3 | Given natural language input from a user, determine the appropriate approach for AI-powered field extraction (prompt design, model selection via AI Gateway, fallback when AI is unavailable) | CC2 | 1 |
| 2.4 | Given a multi-step user interaction that spans stateless requests (e.g., modal open → modal submit), design a context propagation mechanism using serialized metadata | CC2 | 1 |
| 2.5 | Given a channel user identity (e.g., Slack user ID) and a downstream service that requires OBO authorization, determine the correct identity resolution chain and diagnose what fails if the OBO header is missing or incorrect | CC2 | 1 |
| 2.6 | Given a downstream service experiencing failures, determine the correct circuit breaker configuration (threshold, cooldown, half-open probe count) to protect the Experience layer from cascading failure | CC3 | 1 |

**Enabling Knowledge:**
- Slack Events API: retry behavior (x-slack-retry-num, x-slack-retry-reason), 3-second response requirement
- Async processing pattern: immediate 200 acknowledgment, background flow, thread reply with results
- Object Store: TTL configuration, key design for idempotency, failure-safe retrieval
- AI Gateway invocation from Experience layer: /chat/completions endpoint, model selection, timeout handling
- Modal/interaction patterns: private_metadata serialization, state across stateless requests
- Circuit breaker state machine: CLOSED → OPEN (on threshold) → HALF_OPEN (on cooldown expiry) → CLOSED (on success)

---

### Domain 3: AI-Powered Process Orchestration
**Weight: 20% | Items: 12 | Source: JTA Duty Area 3**

The candidate must be able to design and build the Process layer pipeline that orchestrates AI reasoning within deterministic guardrails, enforces business policy regardless of AI output, and degrades gracefully when AI services are unavailable.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 3.1 | Given a multi-stage orchestration requirement, design a pipeline where each stage has defined entry/exit criteria and reports observable status (OK, FAIL, DEGRADED, SKIPPED) | CC2 | 1 |
| 3.2 | Given a scenario where the same request could arrive multiple times, implement request-level deduplication at the Process layer using Object Store with idempotency key derivation | CC2 | 1 |
| 3.3 | Given customer context data from a System API (tier, churn risk, purchase history), construct a grounding prompt that provides the AI with factual context before it reasons about a decision | CC2 | 1 |
| 3.4 | Given AI service availability concerns, design a multi-tier fallback chain (AI Gateway → direct SDK → deterministic mimic) and determine which fallback level to use based on circuit breaker state | CC3 | 2 |
| 3.5 | Given an AI model response that recommends an action (APPROVE/DENY/ESCALATE/CLARIFY), determine which deterministic policy rules must be evaluated AFTER the AI decision before any mutation is permitted | CC3 | 2 |
| 3.6 | Given a set of mutation prerequisites (decision==APPROVE, identity verified, payload complete, policy matched), implement a multi-gate check that blocks irreversible actions unless ALL conditions are met | CC2 | 1 |
| 3.7 | Given a failed mutation, determine what information to persist in the Dead Letter Queue (correlation IDs, error classification, compensation metadata, retryable flag) and how to design for manual replay | CC2 | 1 |
| 3.8 | Given a circuit breaker backed by Object Store, configure the state transitions (failure threshold to open, cooldown duration, half-open probe behavior) for an AI service integration | CC2 | 1 |
| 3.9 | Given a set of failure scenarios (gateway timeout, model overloaded, invalid response, downstream rejection), classify each using the failure taxonomy and determine the appropriate retry/DLQ strategy | CC3 | 1 |
| 3.10 | Given an orchestration flow that calls multiple downstream services, determine the appropriate error handling strategy (on-error-continue for degradation vs. on-error-propagate for fatal failures) at each stage | CC2 | 1 |

**Enabling Knowledge:**
- Multi-stage pipeline design: variable initialization, safe defaults, stage status reporting
- AI Gateway invocation: OpenAI-compatible /chat/completions, system/user prompt construction, structured response parsing
- Amazon Bedrock invocation: InvokeAgent streaming API, session management, timeout handling
- Circuit breaker: Object Store state (tripCount, lastFailureTimestamp, state), threshold logic, cooldown math
- Policy enforcement: the principle that deterministic rules ALWAYS override probabilistic AI suggestions
- Mutation gating: multi-condition AND logic — all gates must pass, any failure blocks the action
- Dead Letter Queue design: what to persist, TTL, compensationNeeded flag, alerting
- Failure taxonomy: POLICY_REJECTED, GATEWAY_DEGRADED, BEDROCK_UNAVAILABLE, SERVICE_CLOUD_REJECTED, UNKNOWN_ERROR
- Deterministic mimic: rule-based fallback logic that approximates AI decisions when AI is unavailable
- DataWeave library functions for reusable policy logic

---

### Domain 4: System APIs as Agent Tools
**Weight: 15% | Items: 9 | Source: JTA Duty Area 4**

The candidate must be able to design and implement System APIs that expose backend capabilities as governed tools for AI agents, following the "execute never decide" principle and the "200 for all business outcomes" contract pattern.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 4.1 | Given a backend capability (Salesforce Case creation, refund issuance, data lookup), design a System API contract that reports business outcomes (success, rejection, escalation) in the response body rather than via HTTP status codes | CC2 | 1 |
| 4.2 | Given an upstream orchestrator that uses response body fields (not HTTP status codes) to route decisions, determine which System API failure scenarios should return HTTP 200 with a rejection payload vs. HTTP 5xx, and explain the consequence of using 5xx for business rejections (false circuit breaker trips) | CC2 | 1 |
| 4.3 | Given a mutation endpoint that could be called multiple times (retries, duplicate events), implement idempotency using a deterministic key derived from request parameters and SOQL-based duplicate detection | CC2 | 2 |
| 4.4 | Given fraud signals from the orchestrator (order number patterns, fraud score), implement a risk gate at the System API that blocks execution before any side effect occurs | CC2 | 1 |
| 4.5 | Given a Salesforce integration that fails with authentication errors after deployment to CloudHub, diagnose common misconfigurations (wrong token endpoint, missing IP relaxation, incorrect Run As user permissions, expired client secret) and determine the correct OAuth 2.0 Client Credentials setup | CC2 | 1 |
| 4.6 | Given a customer identity (email), implement the Data Cloud two-step query pattern (Contact Point Email → Party ID, Party ID → Individual profile) and explain why the two-step pattern is necessary | CC2 | 1 |
| 4.7 | Given an existing System API that must be consumable by both traditional REST clients and AI agents, design the MCP tool contract (name, description, input/output schema) in agent-network.yaml and determine how the tool description influences agent tool-selection accuracy | CC2 | 1 |
| 4.8 | Given expensive downstream queries (Data Cloud profile lookup), implement Object Store caching with appropriate TTL and determine when to invalidate the cache (after mutations that change the underlying data) | CC2 | 1 |

**Enabling Knowledge:**
- System API design philosophy: execute never decide, 200 for business outcomes, 5xx for technical failures only
- Response contract fields: status, decision, actionType, agentStatus, failureClass, retryable, decisionHint, errorCode
- Idempotency: key derivation from business fields (customerId + orderNumber + amount), SOQL Subject-based dedup
- Risk gate pattern: pre-execution check based on signal threshold (e.g., orderNumber.startsWith("999") AND fraudScore >= 70)
- Salesforce Data Cloud: two-step query via ssot__ContactPointEmail__dlm and ssot__Individual__dlm
- Salesforce Service Cloud: Case CRUD, Opportunity field updates, Autolaunched Flow invocation
- OAuth 2.0 Client Credentials: My Domain token endpoint, scope requirements (api, cdp_profile_api, cdp_query_api)
- MCP tool schema: name, description, inputSchema (JSON Schema), tool invocation pattern
- Object Store caching: TTL selection, max entries, cache-aside pattern

---

### Domain 5: Enterprise AI Service Configuration
**Weight: 12% | Items: 7 | Source: JTA Duty Area 5**

The candidate must be able to configure AI infrastructure (Bedrock Agents, AI Gateway, Agent Scanner) and wire it into the enterprise fabric with proper security, governance, and observability.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 5.1 | Given business requirements for an AI agent, configure an Amazon Bedrock Agent with appropriate foundation model selection, natural-language instructions that enforce tool ordering, and Action Groups that invoke Lambda functions | CC2 | 2 |
| 5.2 | Given a Bedrock Agent that invokes a Lambda but receives empty or malformed responses, diagnose the contract violation (missing messageVersion, wrong responseBody format, actionGroup mismatch) and determine the correct response structure | CC2 | 1 |
| 5.3 | Given an AI Gateway configuration requirement, set up an Agent and Tool Instance with Client-ID-Enforcement, SigV4 credential signing for upstream Bedrock access, and rate limiting policies | CC2 | 1 |
| 5.4 | Given an enterprise with AI agents deployed across AWS, Azure, and Salesforce that are invisible to the governance team, determine how to configure Agent Scanner discovery and explain why publishing metadata to Exchange (vs. a custom registry) enables downstream governance policy enforcement | CC2 | 1 |
| 5.5 | Given a Bedrock Agent that must call tools in a specific order (e.g., always score fraud before processing refund), write natural-language instructions that enforce mandatory ordering and test with adversarial scenarios | CC3 | 1 |
| 5.6 | Given a scenario where the AI Gateway is unavailable, implement a direct Bedrock SDK invocation (InvokeAgent streaming API) as a fallback with proper session management and timeout handling | CC2 | 1 |

**Enabling Knowledge:**
- Amazon Bedrock: Agents, Foundation Models (Claude via Bedrock), Action Groups, Aliases, Versions, Guardrails
- Bedrock Agent instructions: mandatory ("MUST call X before Y"), prohibitive ("NEVER proceed without"), conditional ("IF fraud score > threshold, THEN...")
- Lambda response contract for Bedrock Action Groups: required fields, responseBody as TEXT (not JSON)
- AI Gateway (Omni Gateway): Agent Instance vs. Tool Instance, Runtime/Downstream/Upstream configuration
- SigV4 credential signing: access key, secret key, region, service name for Bedrock
- Agent Scanner: discovery configuration, Exchange publication, daily sync cadence
- AWS IAM: least-privilege principle, separating development access from scanner read-only access
- Bedrock Agent Runtime API: InvokeAgent, streaming chunks, session timeout behavior

---

### Domain 6: Salesforce Platform Configuration for Agentic Context
**Weight: 10% | Items: 6 | Source: JTA Duty Area 6**

The candidate must be able to configure Salesforce Data Cloud and Service Cloud as the enterprise backbone that provides customer context (grounding) and action execution for the agentic network.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 6.1 | Given a requirement to provide customer context to AI agents, configure Data Cloud data ingestion (Data Streams from CRM) selecting appropriate fields and mapping Data Lake Objects to Data Model Objects | CC2 | 1 |
| 6.2 | Given a Data Cloud deployment where Identity Resolution produces zero Unified Individuals despite correct match rules, diagnose the root cause (Party field mapped from Email instead of Contact ID) and explain why this particular misconfiguration produces silent failure with no error message | CC3 | 1 |
| 6.3 | Given an identity resolution requirement, configure match rules (exact email match) and reconciliation rules (source priority, most frequent) and verify the resolution produces Unified Individuals | CC2 | 1 |
| 6.4 | Given an external application that needs Salesforce access, create a Connected App with OAuth 2.0 Client Credentials flow, configure the Run As user, relax IP restrictions for CloudHub, and assign required scopes | CC2 | 1 |
| 6.5 | Given a requirement for the agentic network to create Cases or update Opportunities, build an Autolaunched Flow with input variables and verify it is callable via the REST API | CC2 | 1 |
| 6.6 | Given a scenario where Data Cloud queries return empty results, diagnose common silent failures: wrong Party mapping (Email instead of Contact ID), missing data refresh, custom DMO field name mismatch, stale Identity Resolution | CC3 | 1 |

**Enabling Knowledge:**
- Data Cloud architecture: Data Streams, Data Lake Objects, Data Model Objects, Identity Resolution, Unified Individual
- DMO mapping canvas: Individual DMO, Contact Point Email DMO, Party field as the linking mechanism
- Identity Resolution: match rules (exact, fuzzy), reconciliation rules (source priority, most frequent, most recent)
- The critical pitfall: Party must map from Contact ID, not Email — mapping from Email silently fails with no error
- Connected App configuration: OAuth 2.0 Client Credentials, client_id/client_secret, Run As user, IP relaxation
- My Domain token endpoint: https://{mydomain}.my.salesforce.com/services/oauth2/token (NOT login.salesforce.com)
- Required OAuth scopes for Data Cloud: cdp_profile_api, cdp_query_api, api
- Autolaunched Flow: accessible via REST API at /services/data/vXX.X/actions/custom/flow/{flowApiName}
- Custom DMO field API names: must match exactly what SQL queries reference (LoyaltyTier not Loyalty_Tier)

---

### Domain 7: Agent Governance at Enterprise Scale
**Weight: 10% | Items: 6 | Source: JTA Duty Area 7**

The candidate must be able to govern agents across the enterprise using Agent Fabric capabilities (Discover, Govern, Orchestrate, Observe), applying policies that ensure security, cost control, and compliance without limiting agent effectiveness.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 7.1 | Given components in an agentic network, classify each by its Agent Fabric protocol type (MCP Server, Agent/A2A, LLM) and determine which require gateway governance vs. standard API management | CC2 | 1 |
| 7.2 | Given a governance requirement (PII protection, rate limiting, cost control, identity injection), select and apply the appropriate policy from the Agent Fabric policy library to an Agent or Tool Instance | CC2 | 2 |
| 7.3 | Given an existing REST API that needs to be exposed as an MCP tool, determine whether to use MCP Bridge (no-code, wizard-based) or hand-built MCP in Mule (custom logic) based on the requirements | CC3 | 1 |
| 7.4 | Given an enterprise scenario where agents are consuming excessive tokens with no attribution, determine which Agent Fabric capability (Discover, Govern, Orchestrate, Observe) to apply first and what specific configuration resolves the problem | CC2 | 1 |
| 7.5 | Given a governance scenario, distinguish between controls that belong in application code (e.g., business-policy.xml mutation gates) vs. platform policies (e.g., Omni Gateway rate limiting) and explain why each belongs at its level | CC3 | 1 |

**Enabling Knowledge:**
- Agent Fabric: four capabilities and their scope — Discover (visibility), Govern (policy enforcement), Orchestrate (routing/composition), Observe (monitoring/tracing)
- Agent Fabric protocol types: MCP Server, Agent/A2A, LLM — each with different governance requirements
- Governance policy library: PII Handling, Input Validation, Rate Limiting, Cost Threshold Alert, OAuth 2.0 OBO Credential Injection
- MCP Bridge: wizard-based creation from REST API spec (no code, quick, limited customization)
- Hand-built MCP in Mule: full control, custom validation, stateful behavior, business logic
- Agent Visualizer: end-to-end trace visualization across agent networks
- Application-level governance: business rules that require context (customer tier, fraud score, policy match)
- Platform-level governance: infrastructure concerns (rate limits, cost caps, auth enforcement, PII masking)
- agent-network.yaml: declarative tool/agent registry enabling version-controlled governance

---

### Domain 8: Deployment and Operations of Agentic Networks
**Weight: 6% | Items: 4 | Source: JTA Duty Area 8**

The candidate must be able to deploy multi-app agentic networks to CloudHub 2.0 in the correct dependency order, configure secrets securely, verify end-to-end health, and monitor operational status.

| Obj ID | Objective | CC | Items |
|--------|-----------|-----|-------|
| 8.1 | Given a multi-app agentic network that fails health checks after deployment, determine whether the root cause is incorrect deployment order (Experience layer deployed before its Process layer dependency is available) and recommend the correct sequencing strategy | CC2 | 1 |
| 8.2 | Given an application with sensitive credentials (OAuth secrets, API keys, encryption keys), implement the three-tier property strategy: non-sensitive defaults in config.yaml, environment-specific hosts in env-config.yaml, secrets in Runtime Manager encrypted properties | CC2 | 1 |
| 8.3 | Given a deployed agentic network, design an end-to-end verification test that exercises the full path (channel → orchestration → context enrichment → AI reasoning → action execution) and validates each stage status | CC2 | 1 |
| 8.4 | Given DLQ monitoring data (failure classifications, frequency trends, error codes), identify which downstream service is degraded and recommend the appropriate operational response | CC3 | 1 |

**Enabling Knowledge:**
- CloudHub 2.0: Shared Space, Maven plugin deployment, vCore sizing (0.1 minimum), startup time implications
- Deployment dependency ordering: downstream services must be available before upstream callers deploy
- Property hierarchy: config.yaml (defaults in JAR) < env-config.yaml (per-environment) < Runtime Manager (secrets, overrides)
- Secure properties: encrypted YAML with runtime key injection, never plaintext secrets in SCM
- Health probes: liveness (JVM alive) vs. readiness (dependencies connected, ready to serve)
- End-to-end verification: full-path smoke test, stage status validation, error code interpretation
- DLQ monitoring: failure classification trends indicate which downstream system is degraded
- Operational response patterns: increase cooldown, failover to fallback, alert on-call, retry DLQ batch

---

## Item Distribution Summary

| Domain | Weight | Items | CC2 | CC3 |
|--------|--------|-------|-----|-----|
| 1. Agentic Architecture Design | 15% | 9 | 6 | 3 |
| 2. Experience Layer Integration | 12% | 7 | 6 | 1 |
| 3. AI-Powered Process Orchestration | 20% | 12 | 7 | 5 |
| 4. System APIs as Agent Tools | 15% | 9 | 9 | 0 |
| 5. AI Service Configuration | 12% | 7 | 6 | 1 |
| 6. Salesforce Platform Configuration | 10% | 6 | 4 | 2 |
| 7. Agent Governance | 10% | 6 | 4 | 2 |
| 8. Deployment and Operations | 6% | 4 | 3 | 1 |
| **Total** | **100%** | **60** | **45 (75%)** | **15 (25%)** |

**CC Distribution:** 0% Recall / 75% Application / 25% Judgment

**Zero recall items.** Every question on this exam presents a scenario and requires the candidate to either apply a pattern (CC2) or make a judgment call between competing approaches (CC3). There are no "define this term" or "which of the following is true" questions.

This is a deliberate departure from typical MuleSoft certifications (which allocate 15-25% to CC1). The rationale: if a Hybrid Architect + Builder can diagnose a silent Data Cloud failure (CC3) or design a mutation gate (CC2), they necessarily know the underlying definitions. Testing recall separately would waste exam items on candidates who memorized a study guide but can't apply what they read.

The 75/25 split between CC2 and CC3 ensures the exam is primarily scenario-application (testing "can you do the job?") with a substantial judgment layer (testing "can you make the hard calls?"). Domain 3 (Process Orchestration) has the highest CC3 concentration (5 of 12 items = 42%) because that's where the hardest judgment calls live — policy vs. AI, fallback strategy selection, failure classification.

---

## CAT Engine Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **IRT Model** | 2-Parameter Logistic (2PL) | P(correct \| θ, a, b) = 1/(1+exp(-a*(θ-b))). Accounts for both difficulty and discrimination. |
| **Ability Estimation** | Expected A Posteriori (EAP) | Gaussian quadrature with N(0,1) prior over 49 points in [-4,4]. Always well-defined (unlike MLE). |
| **Classification** | SPRT with Wald boundaries | Upper: log((1-β)/α) ≈ 2.94. Lower: log(β/(1-α)) ≈ -2.94. |
| **Cut Score (θ_c)** | 0.0 (to be validated post-beta) | MQC ability on the IRT scale |
| **Indifference Region (δ)** | 0.2 | H_pass: θ_c + δ = 0.2; H_fail: θ_c - δ = -0.2. Prevents oscillation for borderline candidates. |
| **Maximum Items** | 40 | Hard ceiling — forced classification if SPRT has not crossed |
| **Minimum Items** | 5 | Safety floor — SPRT decisions before 5 items are suppressed |
| **Item Selection** | Weighted max-info + content balance | score = 0.7 × normalized_fisher_info + 0.3 × domain_deficit |
| **Content Boost** | First 8 items use w_content=0.5 | Ensures early broad domain sampling |
| **Exposure Control** | Sympson-Hetter per-item gating | Max 25% exposure rate per item; k-values tuned via simulation |
| **Starting Ability** | θ = 0.0 (or Bayesian prior if available) | First item selected at medium difficulty |
| **Time Limit** | 120 minutes | Same as legacy fixed-form; most candidates finish in <30 min due to short test length |

### Item Selection Algorithm

Each time the engine selects the next item:
1. **Filter** — exclude items already administered, retired items, and items gated by Sympson-Hetter (random draw > k_i)
2. **Score** — for each eligible item, compute:
   - `info_score = fisher_information(current_θ, a_i, b_i) / max_info_in_pool` (normalized 0–1)
   - `deficit_score` = how underrepresented item_i's domain is vs. blueprint target (normalized 0–1)
   - `composite = w_info × info_score + w_content × deficit_score`
3. **Select** — item with highest composite score

### Forced Decision at Ceiling

If 40 items are administered without SPRT crossing a boundary:
- If current θ > θ_c → **PASS**
- If current θ ≤ θ_c → **FAIL**
- The decision confidence is computed from the standard error of θ

---

## Pretest Item Strategy

In a CAT environment, pretest items are embedded seamlessly:

- **Pretest items** have `status: pretest` in the item bank. They are eligible for selection but do NOT contribute to SPRT classification or ability estimation.
- The engine presents pretest items according to the same selection algorithm (maximizing information at current θ for their calibration) but excludes their responses from all scoring calculations.
- **Target**: 10–15% of items presented in any session are pretest (typically 1–4 items per candidate depending on session length).
- **Calibration**: After 200+ candidate exposures, pretest items receive IRT parameter estimates (a, b) via marginal maximum likelihood. Items with discrimination ≥ 0.40 and acceptable fit statistics are promoted to `status: active`.
- **Advantage over fixed-form pretest**: every candidate contributes pretest data, not just a fixed pretest-form cohort. This accelerates item calibration by 3–5×.

---

## Item Pool Strategy

| Parameter | Value |
|-----------|-------|
| **Minimum viable pool** | 120 calibrated items (3× ceiling) |
| **Target pool** | 180+ items (enables robust exposure control and content balance) |
| **Beta exam** | 300 candidates minimum for initial parameter calibration |
| **Item lifecycle** | Draft → Pretest → Active → Retired |
| **Retirement criteria** | Discrimination (a) < 0.30, or exposure rate consistently >25% despite k-adjustment, or content becomes outdated |
| **Annual review** | Full blueprint review annually; item refresh as platform evolves |
| **New item pipeline** | Continuous — new items enter as pretest, graduate to active after calibration |
| **Exposure rebalancing** | Quarterly Sympson-Hetter k-value recalculation based on real usage data |

---

## Sample Question Stems by CC Level

### CC2 — Application & Analysis (Scenario → Apply Pattern)

> **Domain 3, Obj 3.6:**
> An architect is designing the mutation gate for a refund orchestration pipeline. The AI model has returned decision: "APPROVE" with fraudScore: 25. The customer's identity has been resolved. The refund amount is $47.50.
>
> Which condition, if unmet, should STILL block the mutation from executing?
>
> A. The AI model's confidence score is below 0.9
> B. The orchestration pipeline's circuit breaker is in HALF_OPEN state
> C. The mutation payload is missing the target Salesforce object ID
> D. The customer's loyalty tier is "Standard" rather than "Premium"

### CC2 — Application & Analysis (Scenario → Diagnose)

> **Domain 4, Obj 4.2:**
> A System API returns HTTP 503 when a customer's refund request is denied due to policy limits. The upstream orchestrator's circuit breaker trips after 3 such denials, causing ALL subsequent requests (including legitimate ones) to fail for 60 seconds.
>
> What change to the System API's response behavior resolves this problem?
>
> A. Return HTTP 200 with status: "REJECTED" and decisionHint: "POLICY_LIMIT_EXCEEDED" in the response body
> B. Return HTTP 429 with a Retry-After header so the circuit breaker waits before retrying
> C. Return HTTP 400 to signal a client error, which circuit breakers should not count as failures
> D. Increase the circuit breaker threshold from 3 to 10 to accommodate frequent policy rejections

### CC3 — Evaluation & Judgment

> **Domain 1, Obj 1.2:**
> A MuleSoft architect is designing a returns processing pipeline. The pipeline must: (1) validate that the order exists, (2) determine the appropriate refund action based on customer loyalty and order history, (3) check that the refund amount does not exceed $500, and (4) create a Case in Service Cloud.
>
> Applying the guided determinism principle, which stages should use AI reasoning and which should use deterministic logic?
>
> A. AI for stages 2 and 3; deterministic for stages 1 and 4
> B. AI for stage 2 only; deterministic for stages 1, 3, and 4
> C. AI for stages 1 and 2; deterministic for stages 3 and 4
> D. AI for all stages with deterministic policy override at the end

---

## Blueprint-to-Item Development Handoff

When this blueprint is approved, the item development team should:

1. **Write 3–4 items per objective** (180+ total) to build the adaptive item pool
2. **Tag each item** with: Domain, Objective ID, CC Level, Distractor rationale, **initial difficulty estimate** (SME rating 1–5 scale, converted to b-parameter after calibration)
3. **Vary difficulty within each objective** — the CAT engine needs items at multiple difficulty levels per domain. For each objective, write at least one item targeting each of: below-MQC (b ≈ -1.0), at-MQC (b ≈ 0.0), above-MQC (b ≈ +1.0)
4. **Ensure each distractor is plausible** — wrong answers should reflect common mistakes, not absurd choices. High-quality distractors increase item discrimination (a-parameter), which makes the CAT engine more efficient
5. **Include "what goes wrong" distractors** — options that describe real failure modes (wrong Party mapping, missing dedup, policy bypass) are excellent wrong answers
6. **Avoid "all of the above" / "none of the above"** — these test test-taking skill, not job skill
7. **Cross-reference the JTA** — every item must trace back to a specific task statement in JTA-Agentic-Enterprise.md
8. **Scenario length** — Every item MUST include a 2-4 sentence scenario that sets context. There are no direct-question recall items on this exam
9. **Avoid vendor-specific syntax** — test patterns and consequences, not XML tag names or DataWeave syntax details
10. **Item independence** — items must be answerable independently (no item should give away or depend on another item's answer). The CAT engine selects items in unpredictable order.
11. **IRT parameter format** — after calibration, each item carries: `a` (discrimination, expected 0.5–2.5), `b` (difficulty, expected -3.0 to +3.0), and fit statistics. Items with a < 0.30 are retired.

---

## Traceability Matrix: Blueprint → JTA → Course Module

| Blueprint Obj | JTA Task(s) | Course Module | Exercise |
|--------------|-------------|---------------|----------|
| 1.1 | 1.1 | Module 1 (Why Agentic) | — |
| 1.2 | 1.2 | Module 1 (Why Agentic) | — |
| 1.3 | 1.4 | Module 1 / Module 3 | Ex 3 (Slack Router) |
| 1.4 | 1.5 | Module 1 / Module 8 | Ex 8 (Agent Fabric) |
| 1.5 | 1.6 | Module 1 | — |
| 1.6 | 1.7 | Module 8 (Agent Fabric) | Ex 8 |
| 2.1 | 2.1 | Module 3 (Slack Layer) | Ex 3 |
| 2.2 | 2.2 | Module 3 (Slack Layer) | Ex 3 |
| 2.3 | 2.3 | Module 3 (Slack Layer) | Ex 3 |
| 2.4 | 2.4 | Module 3 (Slack Layer) | Ex 3 |
| 2.5 | 2.5 | Module 3 (Slack Layer) | Ex 3 |
| 2.6 | 2.6 | Module 3 / Module 5 | Ex 3, Ex 5 |
| 3.1 | 3.1 | Module 5 (Process Layer) | Ex 5 |
| 3.2 | 3.2 | Module 5 (Process Layer) | Ex 5 |
| 3.3 | 3.3 | Module 5 (Process Layer) | Ex 5, Ex 6 |
| 3.4 | 3.5, 3.6 | Module 5 (Process Layer) | Ex 5 |
| 3.5 | 3.7 | Module 5 (Process Layer) | Ex 5 |
| 3.6 | 3.8 | Module 5 (Process Layer) | Ex 5 |
| 3.7 | 3.9 | Module 5 (Process Layer) | Ex 5 |
| 3.8 | 3.6 | Module 5 (Process Layer) | Ex 5 |
| 3.9 | 3.10 | Module 5 (Process Layer) | Ex 5 |
| 3.10 | 3.1 | Module 5 (Process Layer) | Ex 5 |
| 4.1 | 4.1 | Module 6 (System APIs) | Ex 6 |
| 4.2 | 4.2 | Module 6 (System APIs) | Ex 6 |
| 4.3 | 4.3 | Module 6 (System APIs) | Ex 6 |
| 4.4 | 4.4 | Module 6 (System APIs) | Ex 6 |
| 4.5 | 4.5 | Module 6 / Module 2 | Ex 6, Ex 1 |
| 4.6 | 4.6 | Module 6 (System APIs) | Ex 6 |
| 4.7 | 4.8 | Module 6 / Module 8 | Ex 6, Ex 8 |
| 4.8 | 4.7 | Module 6 (System APIs) | Ex 6 |
| 5.1 | 5.1 | Module 4 (AI Gateway + Bedrock) | Ex 4 |
| 5.2 | 5.2 | Module 4 (AI Gateway + Bedrock) | Ex 4 |
| 5.3 | 5.3 | Module 4 (AI Gateway + Bedrock) | Ex 4 |
| 5.4 | 5.4 | Module 4 / Module 8 | Ex 4, Ex 8 |
| 5.5 | 5.6 | Module 4 (AI Gateway + Bedrock) | Ex 4 |
| 5.6 | 5.8 | Module 4 / Module 5 | Ex 4, Ex 5 |
| 6.1 | 6.1 | Module 2 (Salesforce Backbone) | Ex 1 |
| 6.2 | 6.2 | Module 2 (Salesforce Backbone) | Ex 1 |
| 6.3 | 6.3 | Module 2 (Salesforce Backbone) | Ex 1 |
| 6.4 | 6.5 | Module 2 (Salesforce Backbone) | Ex 1 |
| 6.5 | 6.6 | Module 2 (Salesforce Backbone) | Ex 1 |
| 6.6 | 6.7 | Module 2 (Salesforce Backbone) | Ex 1 |
| 7.1 | 7.1 | Module 8 (Agent Fabric) | Ex 8 |
| 7.2 | 7.2 | Module 8 (Agent Fabric) | Ex 8 |
| 7.3 | 7.5 | Module 8 (Agent Fabric) | Ex 8 |
| 7.4 | 7.1 | Module 8 (Agent Fabric) | Ex 8 |
| 7.5 | 7.7 | Module 8 / Module 5 | Ex 8, Ex 5 |
| 8.1 | 8.1 | Module 7 (Deployment) | Ex 7 |
| 8.2 | 8.2 | Module 7 (Deployment) | Ex 7 |
| 8.3 | 8.4 | Module 7 (Deployment) | Ex 7 |
| 8.4 | 8.5 | Module 7 (Deployment) | Ex 7 |

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-06-24 | Initial Draft | Created from JTA-Agentic-Enterprise.md, aligned with Salesforce Certification Exam Development Process Step 2 |
| 2026-06-24 | Rev 2 | Eliminated all CC1 (recall) items. Elevated 9 CC1 objectives to CC2/CC3 with scenario-based format. Added zero-recall rationale. |
| 2026-06-24 | Rev 3 | Converted delivery model from fixed-form (65 items, raw cut score) to Computerized Adaptive Testing (CAT) with SPRT classification. Updated metadata, added CAT engine parameters, revised pretest and item pool strategy to reflect adaptive delivery. Validated via 1000-candidate Monte Carlo simulation (96.6% accuracy, avg 14 items). |
