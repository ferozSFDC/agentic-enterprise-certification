# Beta Readiness TODO List

**Status:** ⚠️ INCOMPLETE - Areas identified in psychometric analysis need attention  
**Target:** Complete before beta launch (300 candidates)  
**Priority:** HIGH  

---

## ✅ Completed (Ready for Beta)

1. **Core CAT Engine** - Fully implemented and validated
   - 2PL IRT model with EAP estimation
   - SPRT classification (α=β=0.05)
   - Fisher Information item selection + content balancing
   - Sympson-Hetter exposure control
   - Monte Carlo validation (96.6% accuracy, avg 13.9 items)

2. **Documentation** - Comprehensive and production-ready
   - CERTIFICATION-OVERVIEW.md (executive summary)
   - cert/PSYCHOMETRIC-ANALYSIS.md (item quality analysis vs MuleSoft)
   - cert/Exam-Blueprint-Agentic-Enterprise.md (CAT delivery model)
   - cert-engine/README.md (quick start)
   - cert-engine/docs/DESIGN.md (technical deep dive)
   - cert-engine/docs/OPERATIONS.md (production operations)
   - cert-engine/docs/DEVELOPMENT.md (developer guide)

3. **Seed Items** - 24 scenario-based items created
   - All CC2/CC3 (zero recall items per requirement)
   - All 8 domains covered (3 items each)
   - MuleSoft-style language (professional, direct, detailed rationales)
   - IRT parameters estimated (SME judgment)

4. **Repository** - Clean and ready
   - New dedicated repo: https://github.com/ferozSFDC/agentic-enterprise-certification
   - 470 files committed (22,451 lines)
   - Clean git history with detailed commit message

---

## ⚠️ Critical Before Beta (Identified in Psychometric Analysis)

### 1. Fix Length Cues in Existing 24 Items

**Problem:** Some correct answers are 1.5-2× longer than distractors (test-wiseness cue)

**Items needing fixes:**
- **exp-001** (line 105): Correct=40 words, distractors=20-30 words
  - Fix: Trim to "Return 200 OK immediately, process in background, post result via Slack API"
  
- **sys-001** (line 259): Correct=50 words, distractors=30 words
  - Fix: Trim to "Circuit breaker treats 403 as failure; after 3 policy rejections, circuit opens and blocks all requests"
  
- **sys-002** (line 281): Correct=60 words, distractors=25-35 words
  - Fix: Trim to "Query for existing refund by hash(customerId + orderNumber + amount); return existing if found"
  
- **sys-003** (line 307): Correct=45 words, distractors=30 words
  - Fix: Trim to "Query ContactPointEmail by email → get PartyId → query Individual by PartyId"
  
- **exp-003** (line 153): Correct=45 words, distractors=25 words
  - Fix: Trim to "Open circuit, return degraded response, probe after cooldown"

**Impact:** Reduces test-wiseness advantage for weak candidates

**Effort:** 2-3 hours (careful rewording to preserve meaning)

---

### 2. Expand Item Pool (Currently 24, Target 60 for Beta, 180 for Production)

**Current difficulty distribution:**
- Very Easy (b < -1.0): **0 items (0%)** ❌ Need 12
- Easy (-1.0 ≤ b < 0.0): 6 items (25%) ✅
- Medium (0.0 ≤ b < 1.0): 17 items (71%) ✅
- Hard (1.0 ≤ b < 2.0): 1 item (4%) ❌ Need 6

**Problem:** Missing easy items for early screening (clear fail candidates finish fast) and hard items for clear pass candidates.

**For Beta (target 60 items):**
- 12 easy items (b < -1.0) - Simple 1-2 sentence scenarios
- 18 medium items (0.0 ≤ b < 1.0) - Continue current complexity
- 6 hard items (b ≥ 1.0) - 4-5 sentences, multi-domain integration

**Example easy item needed:**
```yaml
scenario: |
  An API returns HTTP 200 with body: {"status": "REJECTED", "reason": "Insufficient inventory"}.
stem: "Is this a technical failure or a business outcome?"
# (Tests basic understanding of 200-for-business-outcomes pattern)
```

**Example hard item needed:**
```yaml
scenario: |
  [4-5 sentence scenario integrating guided determinism + OBO headers + circuit breaker + policy evaluation]
stem: "Given these constraints, which components would fail and in what order?"
# (Requires holding 4+ concepts in working memory)
```

**Impact:** 
- Without easy items: Clear-fail candidates take too long (30+ items instead of 8-10)
- Without hard items: Clear-pass candidates take too long (30+ items instead of 10-15)
- CAT efficiency drops from 65% reduction to ~30% reduction

**Effort:** 2-3 days per 12 items × 3 batches = ~1 week (SME + review time)

---

### 3. Add Exhibit-Based Items (Currently 0, Target 6 for Beta)

**Problem:** MuleSoft exams use ~15% exhibit items ("Refer to the exhibit..."). We have zero.

**Exhibits needed:**
1. RAML/OAS specification → test URI construction (Domain 4)
2. Mule XML config → test flow structure (Domain 2)
3. JSON payload → test DataWeave transform (Domain 3)
4. agent-network.yaml → test MCP tool schema (Domain 7)
5. Data Cloud DMO schema → test query pattern (Domain 6)
6. Circuit breaker state diagram → test state transitions (Domain 2)

**Example:**
```yaml
scenario: |
  Refer to the exhibit. This RAML specification defines a POST /refunds endpoint.
  
  ```yaml
  /refunds:
    /{orderId}:
      post:
        body:
          application/json:
            properties:
              amount: number
              reason: string
  ```
  
  What is the correct URI to create a refund for order ID '5001'?
```

**Impact:** Adds diversity to item types, tests specification-reading skills

**Effort:** 1-2 days (requires creating clean exhibit examples)

---

### 4. Mark 50% of Items as Pretest

**Current:** All 24 items marked as "active" (contribute to SPRT score)

**Problem:** 
- Need pretest items to calibrate IRT parameters empirically
- Pretest items don't affect pass/fail decision (candidate doesn't know which are pretest)
- After 200+ exposures, compare calibrated a/b to SME estimates

**Action:**
- Mark 12 of current 24 as "pretest"
- Mark 18 of new 36 as "pretest"
- Result: 30 pretest (50%), 30 active (50%)

**Strategy:**
- Each domain should have ~50% pretest (so content balance still works)
- Distribute pretest across difficulty levels

**Impact:** Allows empirical calibration during beta without affecting results

**Effort:** 30 minutes (change status field in YAML)

---

## 📋 Recommended Phasing

### Phase A: Minimal Viable Beta (MVP)
**Timeline:** 1 week  
**Scope:** Fix critical issues only

1. Fix 5 items with worst length cues (3 hours)
2. Add 12 easy items (2 days)
3. Mark 50% as pretest (30 min)
4. **Result:** 36 items, difficulty range improved, pretest enabled

**Why this works:** 
- 36 items is sufficient for beta (CAT uses 5-40 per candidate, avg ~14)
- Easy items enable fast clear-fail screening
- Pretest enables calibration

**Risk:** 
- Still missing hard items (clear-pass candidates take longer)
- No exhibits (less item diversity)

### Phase B: Full Beta Readiness
**Timeline:** 2 weeks  
**Scope:** Complete all recommendations

1. Fix all length cues (1 day)
2. Add 12 easy + 18 medium + 6 hard items (1 week)
3. Add 6 exhibit items (2 days)
4. Mark 50% as pretest (30 min)
5. SME review of all new items (2 days)
6. **Result:** 60 items, full difficulty range, exhibit diversity

**Why this is better:**
- Full CAT efficiency (avg 13.9 items per candidate)
- Exhibit items test specification-reading skills
- Hard items enable fast clear-pass screening

**Risk:** 
- Takes longer to launch beta
- But produces cleaner calibration data

---

## 🎯 Recommendation

**For Beta: Execute Phase A (Minimal Viable Beta)**

Rationale:
1. 36 items is sufficient for 300-candidate beta
2. Beta's primary goal is to calibrate IRT parameters empirically
3. Easy items are critical (enable clear-fail screening)
4. Hard items and exhibits can be added post-beta (before production)

**After Beta: Add Remaining Items for Production**
- Use beta calibration data to inform difficulty estimates for new items
- Add hard items + exhibits (24 more items → 60 total)
- Continue to 180 items over 3-6 months (ongoing item development)

---

## 📊 Current vs Target Metrics

| Metric | Current (24 items) | Phase A (36 items) | Phase B (60 items) | Production (180 items) |
|--------|-------------------|-------------------|-------------------|----------------------|
| **Item pool size** | 24 | 36 | 60 | 180 |
| **Very easy (b<-1)** | 0 (0%) | 12 (33%) | 12 (20%) | 36 (20%) |
| **Easy (-1≤b<0)** | 6 (25%) | 6 (17%) | 18 (30%) | 54 (30%) |
| **Medium (0≤b<1)** | 17 (71%) | 17 (47%) | 23 (38%) | 72 (40%) |
| **Hard (b≥1)** | 1 (4%) | 1 (3%) | 7 (12%) | 18 (10%) |
| **Exhibit items** | 0 (0%) | 0 (0%) | 6 (10%) | 27 (15%) |
| **Pretest %** | 0% | 50% | 50% | 30-40% |
| **Items per domain** | 3 | 4-5 | 5-8 | 20-25 |
| **Length cues fixed** | No | Top 5 | All | All |

---

## 🚀 Next Steps

1. **Review this document** with stakeholders
2. **Decide on phasing** (Phase A vs Phase B)
3. **Assign item writers** (need 1-2 SMEs for new items)
4. **Schedule item review** (psychometrician + SME review of new items)
5. **Execute chosen phase**
6. **Launch beta** once items are ready

---

## 📞 Questions for Stakeholders

1. **Beta timeline:** How soon do you need to launch beta? (Phase A=1 week, Phase B=2 weeks)
2. **Item writer capacity:** Do you have SMEs available to write 12-36 new items?
3. **Acceptable risk:** Are you comfortable launching beta with 36 items (no hard items, no exhibits)?
4. **Budget:** Do you want to invest in full 60-item pool now, or expand post-beta?

---

**Document Owner:** Certification Development Team  
**Last Updated:** 2026-06-24  
**Next Review:** After Phase A or B completion
