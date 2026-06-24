# Certification: Architecting and Developing an Agentic Enterprise

**Complete documentation for the MuleSoft Agentic Enterprise Architect certification program.**

---

## Overview

This certification validates that a practitioner can design, build, deploy, and govern multi-system agentic solutions using AI reasoning (LLMs, Bedrock Agents) within enterprise-grade MuleSoft integration networks.

**Target Candidate:** Hybrid Architect + Builder — designs AND implements agentic enterprise systems

**Prerequisites:** Salesforce Certified MuleSoft Developer (SCMD) recommended

**Exam Delivery:** Computerized Adaptive Testing (CAT) with Sequential Probability Ratio Test (SPRT) classification

---

## Project Structure

```
Architecting-and-Developing-Agentic-Enterprise/
│
├── cert/                                    # Certification content
│   ├── JTA-Agentic-Enterprise.md           # Job Task Analysis (8 duty areas, weights, tasks)
│   └── Exam-Blueprint-Agentic-Enterprise.md # Exam blueprint (49 objectives, CC levels, CAT parameters)
│
├── cert-engine/                             # CAT exam engine (FastAPI + PostgreSQL)
│   ├── app/
│   │   ├── irt/                            # Pure IRT math (2PL, EAP, SPRT)
│   │   ├── services/                       # Business logic (item selection, stopping rules)
│   │   ├── routers/                        # API endpoints (exam lifecycle, admin)
│   │   ├── models/                         # SQLAlchemy ORM (items, sessions, candidates)
│   │   └── schemas/                        # Pydantic request/response schemas
│   │
│   ├── data/
│   │   └── seed_items.yaml                 # 24 initial exam items (3 per domain)
│   │
│   ├── scripts/
│   │   ├── seed_items.py                   # Load items into database
│   │   └── simulate_cat.py                 # Monte Carlo validation
│   │
│   ├── tests/                              # 46 unit tests + integration tests
│   │   ├── test_irt/                       # IRT math tests (2PL, EAP, SPRT)
│   │   └── test_services/                  # CAT engine tests
│   │
│   ├── docs/
│   │   ├── DESIGN.md                       # IRT theory, SPRT math, architecture decisions
│   │   ├── OPERATIONS.md                   # Deployment, monitoring, item lifecycle
│   │   └── DEVELOPMENT.md                  # How to extend, test, contribute
│   │
│   ├── README.md                           # Quick start, API overview, validation results
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml
│
└── CERTIFICATION-OVERVIEW.md               # This file
```

---

## Documentation Map

### For Certification Program Managers

**Start here:**
1. **[cert/JTA-Agentic-Enterprise.md](cert/JTA-Agentic-Enterprise.md)** — The foundation. Defines the 8 duty areas, weights (why 20% for Process Orchestration, 6% for Deployment), and 62 task statements. Includes full rationale for why 8 areas (not 7 or 9), how weights were derived, and validation criteria.

2. **[cert/Exam-Blueprint-Agentic-Enterprise.md](cert/Exam-Blueprint-Agentic-Enterprise.md)** — Maps the JTA to 49 exam objectives with Cognitive Complexity (CC) levels. **Zero recall items** — every question is scenario-based (CC2 or CC3). Includes CAT delivery model parameters, item pool strategy, and traceability to course modules.

**Key decisions documented:**
- Why CAT vs. fixed-form (65% shorter exams for most candidates)
- Why SPRT classification (statistical rigor, optimal test length)
- Why zero CC1 (recall testing doesn't predict job performance for hybrid architect+builder role)
- Blueprint-to-JTA-to-Course traceability matrix (every objective traces to a task and course module)

### For Psychometricians

**Start here:**
1. **[cert-engine/docs/DESIGN.md](cert-engine/docs/DESIGN.md)** — Deep dive into IRT theory, SPRT mathematics, item selection algorithm, content balancing, and exposure control. Includes formulas, worked examples, and validation methodology.

2. **[cert-engine/README.md](cert-engine/README.md)** — Monte Carlo validation results (96.6% classification accuracy, avg 14 items, domain coverage within ±1.2%).

**Key psychometric decisions:**
- 2PL IRT model (discrimination + difficulty; no guessing parameter for now)
- EAP ability estimation (always well-defined, stable for early stopping)
- SPRT with Wald boundaries (α=β=0.05, optimal for binary classification)
- Indifference region δ=0.2 (prevents oscillation for borderline candidates)
- Content balancing: 0.7 Fisher Information + 0.3 domain deficit
- Sympson-Hetter exposure control (max 25% per item)

**Item calibration process documented in:** [cert-engine/docs/OPERATIONS.md](cert-engine/docs/OPERATIONS.md) → Item Lifecycle Management

### For Software Engineers

**Start here:**
1. **[cert-engine/README.md](cert-engine/README.md)** — Quick start, project structure, API overview, key concepts (IRT, SPRT, content balancing).

2. **[cert-engine/docs/DEVELOPMENT.md](cert-engine/docs/DEVELOPMENT.md)** — Development setup, code style, testing strategy, how to add features (with worked examples).

**Key technical decisions:**
- FastAPI + async SQLAlchemy (high concurrency, type safety)
- Layered architecture (routers → services → IRT math; pure functions, no side effects in IRT module)
- PostgreSQL with JSONB for config snapshots (versioned exam parameters)
- Docker Compose for local dev, production-ready for CloudHub/AWS ECS

**How to extend:**
- Add 3PL model (guessing parameter) — [example in DEVELOPMENT.md](cert-engine/docs/DEVELOPMENT.md#irt-model-extensions)
- Add confidence interval to session status — [example in DEVELOPMENT.md](cert-engine/docs/DEVELOPMENT.md#adding-new-features)
- Database migrations with Alembic — [best practices in DEVELOPMENT.md](cert-engine/docs/DEVELOPMENT.md#database-migrations)

### For Operations / DevOps

**Start here:**
1. **[cert-engine/docs/OPERATIONS.md](cert-engine/docs/OPERATIONS.md)** — Deployment procedures, configuration management, monitoring, security, backup/DR, troubleshooting runbooks.

**Key operational procedures:**
- Deployment checklist (backup, migrations, smoke test, rollback plan)
- Item lifecycle: draft → pretest → active → retired (calibration after 200+ responses)
- Monitoring metrics (uptime, pass rate, test length, item exposure)
- Alert rules (critical: API down, database failures; warning: pass rate drift, high exposure)
- Incident response (SEV-1 to SEV-4, post-mortem template)
- Routine maintenance (daily, weekly, monthly, quarterly, annual tasks)

**Disaster recovery:**
- RTO: 1 hour
- RPO: 24 hours (daily backups)
- Runbook for database restore, emergency maintenance mode

### For Item Writers / SMEs

**Start here:**
1. **[cert/Exam-Blueprint-Agentic-Enterprise.md](cert/Exam-Blueprint-Agentic-Enterprise.md)** → Blueprint-to-Item Development Handoff section

2. **[cert-engine/data/seed_items.yaml](cert-engine/data/seed_items.yaml)** — 24 example items (3 per domain) with proper format, IRT parameters, scenario structure, and distractor rationale.

**Item writing guidelines:**
- Every item MUST have a 2-4 sentence scenario (zero recall items)
- 4 options with detailed rationale (why each is correct/incorrect)
- Vary difficulty within each objective (write items targeting below-MQC, at-MQC, above-MQC)
- Tag with domain_id, objective_id, cc_level, SME-estimated a/b parameters
- "What goes wrong" distractors are excellent (wrong Party mapping, missing dedup, policy bypass)

**Calibration process:**
1. Items start as `status: "draft"` (not selectable)
2. Promote to `status: "pretest"` after SME review (selectable but don't contribute to score)
3. Collect 200+ responses per item
4. Calibrate a/b via marginal maximum likelihood (EM algorithm)
5. Promote to `status: "active"` if discrimination ≥ 0.40 and good fit
6. Retire if discrimination < 0.30 or content outdated

---

## Certification Exam Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Item Pool Size** | 180+ calibrated items | Minimum 120 viable (3× ceiling), target 180 (enables robust exposure control) |
| **Items per Session** | 5–40 (adaptive) | Algorithm decides per candidate. Average ~14 items. |
| **Decision** | PASS or FAIL | Binary classification (no numeric score, no subscores) |
| **Cut Score (θ_c)** | 0.0 on IRT scale | MQC (minimally qualified candidate) ability |
| **Indifference Region (δ)** | 0.2 | H_pass: θ_c + δ = 0.2; H_fail: θ_c - δ = -0.2 |
| **Error Rates** | α=β=0.05 | ≤5% false pass, ≤5% false fail (validated: 1.6%/1.8%) |
| **Maximum Items** | 40 | Forced decision if SPRT hasn't crossed |
| **Minimum Items** | 5 | Safety floor (content validity, measurement stability) |
| **Time Limit** | 120 minutes | Most candidates finish in <30 min due to early stopping |
| **Starting Ability** | θ=0.0 | Neutral prior (or Bayesian prior if candidate has history) |
| **Item Selection** | 0.7 Fisher Info + 0.3 domain deficit | First 8 items use 0.5/0.5 for broad sampling |
| **Exposure Control** | Sympson-Hetter, max 25% | No item appears in >1 in 4 exams |

---

## Validation Status

### Monte Carlo Simulation (1000 Candidates)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Classification accuracy** | >95% | 96.6% | ✅ PASS |
| **Type I error (false pass)** | ≤5% | 1.6% | ✅ Conservative |
| **Type II error (false fail)** | ≤5% | 1.8% | ✅ Conservative |
| **Avg items (clear pass, θ>0.5)** | <20 | 8.1 | ✅ Efficient |
| **Avg items (clear fail, θ<-0.5)** | <20 | 8.8 | ✅ Efficient |
| **Avg items (borderline, -0.2<θ<0.2)** | approaches 40 | 25.1 | ✅ Expected |
| **Overall avg items** | — | 13.9 | 65% shorter than ceiling |
| **Domain coverage** | ±5% | ±1.2% | ✅ Balanced |
| **Theta estimation RMSE** | <0.5 | 0.382 | ✅ Accurate |
| **Correlation (true vs. estimated)** | >0.9 | 0.963 | ✅ Excellent |

**Interpretation:** The CAT engine meets or exceeds all psychometric standards. Ready for operational beta with real candidates.

### Item Bank Status

| Status | Count | Description |
|--------|-------|-------------|
| **Seed items** | 24 | 3 per domain, pre-calibrated by SME estimates, loaded into database |
| **Target pool** | 180 | Minimum viable: 120 (3× ceiling); target 180 for robust exposure control |
| **Items to write** | 156 | 3–4 per objective (49 objectives × 3.2 avg = 157) |

**Next steps:**
1. Write 156 additional items following blueprint (see seed_items.yaml for format)
2. Import via `/api/v1/admin/items/import` endpoint
3. Promote to pretest after SME review
4. Run 300-candidate operational beta
5. Calibrate items after 200+ exposures each
6. Promote high-quality items (a ≥ 0.40) to active pool

---

## Domain Structure

| Domain | Weight | Tasks | Objectives | Sample Items (seed) |
|--------|--------|-------|------------|---------------------|
| **1. Agentic Architecture Design** | 15% | 7 | 6 | 3 (arch-001, arch-002, arch-003) |
| **2. Experience Layer Integration** | 12% | 7 | 6 | 3 (exp-001, exp-002, exp-003) |
| **3. AI-Powered Process Orchestration** | 20% | 12 | 10 | 3 (proc-001, proc-002, proc-003) |
| **4. System APIs as Agent Tools** | 15% | 10 | 8 | 3 (sys-001, sys-002, sys-003) |
| **5. Enterprise AI Service Configuration** | 12% | 8 | 6 | 3 (ai-001, ai-002, ai-003) |
| **6. Salesforce Platform Configuration** | 10% | 7 | 6 | 3 (sf-001, sf-002, sf-003) |
| **7. Agent Governance at Scale** | 10% | 7 | 5 | 3 (gov-001, gov-002, gov-003) |
| **8. Deployment and Operations** | 6% | 6 | 4 | 3 (ops-001, ops-002, ops-003) |
| **Total** | **100%** | **64** | **49** | **24** |

**Cognitive Complexity Distribution:**
- CC1 (Recall): 0% — Zero recall items (deliberate design decision)
- CC2 (Application): 75% — Scenario-based application and analysis
- CC3 (Judgment): 25% — Evaluation and judgment (competing approaches, trade-offs)

**Rationale for zero CC1:** If a candidate can diagnose a silent Data Cloud failure (CC3) or design a mutation gate (CC2), they necessarily know the underlying definitions. Testing recall separately wastes exam items on candidates who memorized a study guide but can't apply what they read. See [Exam Blueprint → CC Levels](cert/Exam-Blueprint-Agentic-Enterprise.md#cognitive-complexity-cc-levels) for full rationale.

---

## Key Design Decisions

### 1. Why CAT vs. Fixed-Form?

**Problem:** Traditional fixed-form exams present every candidate with the same 60–80 items.
- High-ability candidates waste time on easy items (measurement inefficiency)
- Low-ability candidates are demoralized by items beyond their level
- Security risk: With only 2 parallel forms, every item is seen by 50% of candidates

**Solution:** Computerized Adaptive Testing (CAT)
- Tailors difficulty to each candidate (selects items near current ability estimate)
- Terminates early when statistical confidence is reached (SPRT classification)
- Average test length: 14 items (65% shorter than 40-item ceiling)
- Security: 180+ item pool + exposure control (max 25% per item)

**Validated:** 96.6% classification accuracy, error rates 1.6%/1.8% (well below 5% targets)

### 2. Why SPRT vs. Other Stopping Rules?

**Alternatives considered:**
- **Confidence interval method:** Stop when SE(θ̂) is small enough. Problem: Doesn't directly control error rates (α, β).
- **Information threshold:** Stop when total information exceeds target. Problem: Doesn't account for WHERE θ̂ falls relative to cut score.
- **Fixed length with CAT item selection:** Adaptive selection but fixed N items. Problem: Misses the efficiency gain from early stopping.

**SPRT advantages:**
- **Optimal:** Minimizes expected test length for any given error rates (Wald, 1945)
- **Exact error control:** Specify α=0.05, β=0.05 → guaranteed ≤5% false pass/fail
- **Incremental:** After each item, update a single statistic (log-likelihood ratio); no complex recalculation

**Tradeoff:** SPRT is binary classification only (PASS/FAIL, no subscores). Acceptable for this high-stakes credential.

### 3. Why Zero Recall Items?

**Traditional MuleSoft certifications allocate 15–25% to CC1 (recall).** This exam has **ZERO recall items.**

**Rationale:**
1. **The target candidate is a Hybrid Architect + Builder.** If they can't apply knowledge to a scenario, recalling a definition has no value.
2. **Pure recall tests study skill, not job skill.** Memorizing "what are the four Agent Fabric capabilities" doesn't predict whether someone can govern an agent network.
3. **Scenario-based items have higher discrimination.** CC2/CC3 items better separate qualified from unqualified candidates.
4. **This matches the course philosophy.** The course teaches through building, not lecture. Every concept is introduced in the context of a real system.

**Validation:** 24 seed items are all scenario-based (2-4 sentence context). See [seed_items.yaml](cert-engine/data/seed_items.yaml).

### 4. Why EAP vs. MLE for Ability Estimation?

**Maximum Likelihood Estimation (MLE):**
- ✅ Unbiased (asymptotically)
- ❌ Undefined for extreme response patterns (all correct → θ̂=∞, all incorrect → θ̂=-∞)
- ❌ Unstable early in exam

**Expected A Posteriori (EAP):**
- ✅ Always well-defined (uses Bayesian prior)
- ✅ Stable early (regularized by prior)
- ✅ Can incorporate candidate history (custom prior for candidates with prerequisites)
- ❌ Slight regression toward prior mean (acceptable for early stopping)

**Decision:** Use EAP for robust early stopping. After 5–10 items, EAP provides stable θ̂ for SPRT classification.

### 5. Why Separate CAT Engine Service?

**Alternatives considered:**
- Build CAT into existing course platform (Flask app)
- Use third-party exam platform (Webassessor, Kryterion with their CAT modules)

**Decision:** Standalone FastAPI service

**Rationale:**
1. **Psychometric control:** We own the IRT algorithms, SPRT classification, item selection logic. Can tune parameters (δ, α, β) without vendor negotiation.
2. **Item bank security:** Item pool stays in our database, not exported to third-party vendor.
3. **Analytics:** Full access to response data for item calibration, equity audits, content refresh.
4. **Extensibility:** Can add 3PL model, multi-stage CAT, confidence intervals without waiting for vendor roadmap.
5. **Cost:** No per-candidate licensing fee (only infrastructure cost).

**Tradeoff:** We maintain the infrastructure (deployment, monitoring, security). Acceptable given we already run course platform.

---

## Operational Readiness

### Phase 1-3: Complete ✅

- [x] IRT math module (2PL, EAP, SPRT) — 46 unit tests pass
- [x] CAT engine orchestrator — Integration tests pass
- [x] API layer (exam lifecycle, admin endpoints) — Functional
- [x] Database schema (items, sessions, responses, candidates, config) — Migrations ready
- [x] Monte Carlo validation — 96.6% accuracy, all targets met
- [x] Documentation — DESIGN.md, OPERATIONS.md, DEVELOPMENT.md complete
- [x] Seed items — 24 items covering all 8 domains, scenario-based format

### Phase 4: Admin UI (Not Yet Implemented)

- [ ] Item bank management UI (CRUD, bulk import, status transitions)
- [ ] Session viewer (theta trajectory chart, item-by-item log, decision trace)
- [ ] Analytics dashboard (pass rate trends, domain coverage, exposure distribution)
- [ ] Configuration editor (adjust θ_c, α, β, domain weights via UI)

**Tech stack:** Jinja2 templates + HTMX (server-rendered, no heavy JS framework)

### Phase 5: Hardening (Not Yet Implemented)

- [ ] Concurrency tests (100 parallel sessions, verify no race conditions)
- [ ] Exposure control tuning (adjust Sympson-Hetter k-values from real usage)
- [ ] Alembic migration setup (schema versioning for production)
- [ ] Full API test coverage (integration tests for all routers)
- [ ] Load testing (1000 requests/minute, p95 response time < 500ms)

### Item Pool Expansion

**Current:** 24 seed items  
**Minimum viable:** 120 items (3× ceiling of 40)  
**Target:** 180+ items (robust exposure control + content validity)

**To write:** 156 items (3–4 per objective)

---

## Timeline to Launch

### Beta Phase (300 Candidates)

**Prerequisites:**
- [ ] 120+ items written and imported (pretest status)
- [ ] Beta candidate cohort identified (mix of abilities)
- [ ] Proctor integration (or honor-code policy for beta)

**Beta goals:**
1. Calibrate item parameters (a, b) from real responses
2. Validate pass rate (~60–70% expected)
3. Validate test length distribution (avg ~14, borderline ~25)
4. Identify items for retirement (a < 0.30, poor fit)
5. Collect candidate feedback (exam length, item clarity, technical issues)

**Duration:** 6–8 weeks (allow time for 200+ exposures per item)

### Post-Beta

**Data analysis (2 weeks):**
- Item calibration via marginal maximum likelihood
- Cut score validation (Modified Angoff with SME panel)
- Equity audit (check for differential item functioning by subgroup)
- Item retirement decisions

**Item pool refinement (2 weeks):**
- Promote high-quality pretest items to active (a ≥ 0.40, good fit)
- Retire low-quality items (a < 0.30, misfit, outdated content)
- Write replacement items if active pool < 120

**Production launch (1 week):**
- Deploy to production environment
- Enable public registration
- Announce certification availability

**Total:** 11–13 weeks from beta start to production launch

---

## Contact and Maintenance

### Document Ownership

| Document | Owner | Last Updated |
|----------|-------|--------------|
| JTA-Agentic-Enterprise.md | Certification Psychometrician | 2026-06-24 |
| Exam-Blueprint-Agentic-Enterprise.md | Content Lead + Psychometrician | 2026-06-24 |
| cert-engine/ (all code) | CAT Engine Development Team | 2026-06-24 |
| docs/DESIGN.md | Tech Lead + Psychometrician | 2026-06-24 |
| docs/OPERATIONS.md | DevOps Lead | 2026-06-24 |
| docs/DEVELOPMENT.md | Tech Lead | 2026-06-24 |

### Questions?

- **Psychometric design:** [Your certification psychometrician]
- **Technical architecture:** [Your development lead]
- **Item writing:** [Your content lead]
- **Operations/deployment:** [Your DevOps lead]
- **Exam content:** See `cert/Exam-Blueprint-Agentic-Enterprise.md` and `cert/JTA-Agentic-Enterprise.md`

---

## Appendix: Quick Reference

### Glossary

| Term | Definition |
|------|------------|
| **CAT** | Computerized Adaptive Testing — exam adapts difficulty per candidate |
| **SPRT** | Sequential Probability Ratio Test — binary classification with optimal test length |
| **IRT** | Item Response Theory — models probability of correct response given ability + item parameters |
| **2PL** | 2-Parameter Logistic model — P(correct) = f(θ, a, b) |
| **θ (theta)** | Candidate ability on logit scale (mean=0, SD=1) |
| **θ_c** | Cut score (MQC ability = 0.0) |
| **a** | Item discrimination (0.5–2.5; higher = better item) |
| **b** | Item difficulty (-3 to +3; 0 = MQC level) |
| **EAP** | Expected A Posteriori — Bayesian ability estimation |
| **Fisher Information** | How much an item tells us about ability (I = a² P Q) |
| **Sympson-Hetter** | Exposure control method (per-item gating probability k) |
| **CC1/CC2/CC3** | Cognitive Complexity levels (Recall / Application / Judgment) |
| **MQC** | Minimally Qualified Candidate |

### File Locations

| What | Where |
|------|-------|
| **JTA** | `cert/JTA-Agentic-Enterprise.md` |
| **Exam Blueprint** | `cert/Exam-Blueprint-Agentic-Enterprise.md` |
| **Seed Items** | `cert-engine/data/seed_items.yaml` |
| **IRT Math** | `cert-engine/app/irt/models.py`, `estimation.py`, `sprt.py` |
| **CAT Engine** | `cert-engine/app/services/cat_engine.py` |
| **API** | `cert-engine/app/routers/exam.py` |
| **Tests** | `cert-engine/tests/` |
| **Docs** | `cert-engine/docs/` |
| **Simulation** | `cert-engine/scripts/simulate_cat.py` |

---

**Document Version:** 1.0  
**Created:** 2026-06-24  
**Maintained By:** Certification Program Team
