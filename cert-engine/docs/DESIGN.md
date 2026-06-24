# CAT Engine Design Documentation

## Table of Contents

1. [Why Computerized Adaptive Testing?](#why-computerized-adaptive-testing)
2. [Item Response Theory (IRT) Foundation](#item-response-theory-irt-foundation)
3. [Sequential Probability Ratio Test (SPRT)](#sequential-probability-ratio-test-sprt)
4. [Item Selection Algorithm](#item-selection-algorithm)
5. [Content Balancing](#content-balancing)
6. [Exposure Control](#exposure-control)
7. [Stopping Rules](#stopping-rules)
8. [Ability Estimation](#ability-estimation)
9. [Architecture Decisions](#architecture-decisions)
10. [Validation Methodology](#validation-methodology)

---

## Why Computerized Adaptive Testing?

### The Problem with Fixed-Form Exams

Traditional certification exams present every candidate with the same N items (or one of K parallel forms). This approach has fundamental limitations:

1. **Measurement inefficiency:** High-ability candidates waste time on easy items that provide little information about their true ability. Low-ability candidates are demoralized by a long sequence of items beyond their level.

2. **One-size-fits-none:** A fixed-form exam optimized for the minimally qualified candidate (MQC) at θ=0.0 is too easy for θ>1.0 candidates and too hard for θ<-1.0 candidates. Measurement precision (standard error) is poor at the extremes.

3. **Security vulnerability:** With only K parallel forms, item exposure is high (1/K). For a 2-form exam, every item is seen by 50% of candidates. Item harvesting becomes feasible.

4. **Candidate fatigue:** Requiring 60–80 items to achieve acceptable measurement precision for all ability levels causes fatigue effects that degrade measurement quality for the last 20% of items.

### The CAT Solution

Computerized Adaptive Testing addresses these problems by:

- **Tailoring difficulty to each candidate:** After each response, the engine estimates current ability (θ̂) and selects the next item with difficulty b ≈ θ̂ (maximum information).
- **Early termination:** When accumulated evidence reaches statistical confidence (via SPRT), the exam ends. High/low ability candidates finish in ~8 items. Only borderline candidates approach the ceiling (40 items).
- **Security through unpredictability:** Every candidate sees a different item sequence selected from a large pool (180+ items). With exposure control (max 25% per item), harvesting is infeasible.
- **Measurement precision where it matters:** The exam concentrates items near the cut score (θ_c = 0.0), providing high precision for pass/fail classification while spending fewer items on candidates far from the boundary.

### Tradeoffs

CAT is not a silver bullet:

| Advantage | Tradeoff |
|-----------|----------|
| Shorter exams (avg 14 items vs. 40 fixed) | Larger item pool required (180+ vs. 80 for 2 parallel forms) |
| Early termination for clear pass/fail | Borderline candidates still see 25–35 items (no reduction) |
| High security (large pool + exposure control) | Cannot review/skip items (sequential only) |
| Optimal measurement precision at cut score | Requires IRT calibration (200+ responses per item) |
| Statistical rigor (SPRT confidence bounds) | Binary classification only (PASS/FAIL, no subscores) |

**Decision:** For this high-stakes certification (career impact, employer recognition), the tradeoffs are acceptable. The average candidate benefits from 65% shorter exams, and the few borderline candidates receive the same thorough measurement they would in a fixed-form.

---

## Item Response Theory (IRT) Foundation

### Why IRT vs. Classical Test Theory (CTT)?

Classical Test Theory treats all items as interchangeable units (1 point each). A candidate's score is the raw count of correct responses. This has several problems:

1. **Form dependence:** A score of 40/60 on an easy form is not comparable to 40/60 on a hard form.
2. **No item-level information:** CTT tells you the item's p-value (proportion correct) but not its discrimination (how well it separates high/low ability).
3. **Cannot support adaptive testing:** CTT provides no way to predict a candidate's probability of answering an unseen item correctly.

IRT solves these by modeling the interaction between candidate ability and item parameters:

```
P(X_i = 1 | θ, a_i, b_i) = f(θ, a_i, b_i)
```

This equation says: "The probability that candidate with ability θ answers item i correctly is a function of θ and the item's parameters (a, b)."

### The 2-Parameter Logistic (2PL) Model

We use the 2PL model:

```
P(θ, a, b) = 1 / (1 + exp(-a * (θ - b)))
```

**Parameters:**
- **θ (theta):** Candidate ability on the logit scale. Mean = 0, SD = 1 by convention. The MQC (minimally qualified candidate) is at θ = 0.
- **a (discrimination):** How steeply probability increases as ability increases. Range: 0.5–2.5. Higher a = better item (more informative).
- **b (difficulty):** The ability level where P(correct) = 0.5. Range: -3.0 to +3.0. b = θ_c targets the cut score.

**Key properties:**

1. **At θ = b, probability is always 0.5** (regardless of a). This is the "50% point" — the ability level where the item is maximally difficult.

2. **When θ > b, probability > 0.5** (candidate is above item difficulty → likely correct).

3. **When θ < b, probability < 0.5** (candidate is below item difficulty → likely incorrect).

4. **Higher a makes the curve steeper.** A highly discriminating item (a=2.0) transitions from 10% correct at θ=b-1 to 90% correct at θ=b+1. A poorly discriminating item (a=0.5) transitions slowly.

**Example:**

Item: "arch-002" (OBO header propagation)  
Parameters: a=1.5, b=-0.2

For a candidate at θ=0.0 (MQC level):
```
P(correct | 0.0, 1.5, -0.2) = 1 / (1 + exp(-1.5 * (0.0 - (-0.2))))
                             = 1 / (1 + exp(-0.3))
                             = 1 / (1 + 0.7408)
                             = 0.574 (57% chance of correct)
```

For a candidate at θ=-0.5 (below MQC):
```
P(correct | -0.5, 1.5, -0.2) = 1 / (1 + exp(-1.5 * (-0.5 - (-0.2))))
                              = 1 / (1 + exp(0.45))
                              = 0.389 (39% chance of correct)
```

### Fisher Information

Fisher Information quantifies how much an item tells us about a candidate's ability:

```
I(θ | a, b) = a² × P(θ, a, b) × (1 - P(θ, a, b))
```

**Key properties:**

1. **Maximum information when θ = b** (at the item's difficulty). This is where P = 0.5 and P×(1-P) = 0.25 is maximized.
   - I(θ=b) = a² × 0.25 = a²/4

2. **Information decreases as θ moves away from b.** An item with b=-1.0 provides little information about a candidate at θ=+2.0 (probability ≈ 1.0, no uncertainty).

3. **Information scales with a².** An item with a=2.0 provides 4× more information than an item with a=1.0 (at their respective difficulty levels).

**Why this matters for CAT:**

The item selection algorithm chooses items that maximize information at the current ability estimate θ̂. This concentrates measurement where uncertainty is highest, leading to rapid convergence.

### Test Information and Standard Error

The total information from a set of items is the sum:

```
I(θ | items) = Σ I(θ | a_i, b_i)
```

Standard error (SE) of the ability estimate:

```
SE(θ̂) = 1 / √I(θ̂)
```

**Example:**

After 8 items with total information I(0.0) = 6.0 at the cut score:
```
SE(0.0) = 1 / √6.0 ≈ 0.408
```

This SE translates to a 95% confidence interval:
```
CI = θ̂ ± 1.96 × SE = 0.0 ± 0.80 = [-0.80, 0.80]
```

If the cut score θ_c = 0.0, this candidate's true ability could be anywhere from -0.8 to +0.8 with 95% confidence. We need more items to narrow the interval and make a confident classification.

After 20 items with I(0.0) = 16.0:
```
SE(0.0) = 1 / √16.0 = 0.25
CI = 0.0 ± 0.49 = [-0.49, +0.49]
```

Much tighter. This is why borderline candidates see more items — we need high information to classify them confidently.

---

## Sequential Probability Ratio Test (SPRT)

### The Classification Problem

We want to classify each candidate as PASS or FAIL relative to a cut score θ_c = 0.0. This is a **binary hypothesis test:**

- **H_0 (null):** θ = θ_0 (candidate is below cut) → FAIL
- **H_1 (alternative):** θ = θ_1 (candidate is above cut) → PASS

Standard hypothesis testing (like a z-test) requires a fixed sample size N determined a priori to achieve desired error rates. But in adaptive testing, we want **sequential testing:** decide as soon as evidence is sufficient, without pre-committing to N.

### Why SPRT?

The Sequential Probability Ratio Test (Wald, 1945) is optimal for sequential binary classification:

1. **Minimizes expected test length** for any given error rates (α, β). No other sequential test reaches a decision faster on average.
2. **Provides exact error rate control.** You specify α (Type I: false pass) and β (Type II: false fail), and SPRT guarantees those rates.
3. **Accumulates evidence incrementally.** After each item response, update a single statistic (log-likelihood ratio). No complex recalculation.

### The SPRT Statistic

After administering items 1..n, compute the **log-likelihood ratio:**

```
LR_n = log(P(X_1..X_n | H_1) / P(X_1..X_n | H_0))
```

Where:
- X_i = 1 if item i was answered correctly, 0 otherwise
- P(X_1..X_n | H_j) is the probability of observing this response pattern under hypothesis H_j

Under the 2PL model:

```
P(X_1..X_n | θ) = ∏ P(X_i | θ, a_i, b_i)
```

So:

```
LR_n = Σ log(P(X_i | θ_1, a_i, b_i) / P(X_i | θ_0, a_i, b_i))
```

For each item i:
- If X_i = 1 (correct): add log(P_1 / P_0)
- If X_i = 0 (incorrect): add log((1-P_1) / (1-P_0))

Where:
- P_1 = P(θ_1, a_i, b_i) (probability under H_1: candidate is above cut)
- P_0 = P(θ_0, a_i, b_i) (probability under H_0: candidate is below cut)

### Decision Rules

Define Wald boundaries:

```
A = log((1 - β) / α)  ≈ 2.94  (for α=β=0.05)
B = log(β / (1 - α))  ≈ -2.94
```

**After each item:**
- If LR_n ≥ A → **PASS** (accumulated evidence favors H_1)
- If LR_n ≤ B → **FAIL** (accumulated evidence favors H_0)
- If B < LR_n < A → **CONTINUE** (insufficient evidence; administer next item)

### The Indifference Region

We don't test θ = θ_c exactly (a point hypothesis is unrealistic). Instead, we define an **indifference region** around θ_c:

- **H_0:** θ = θ_c - δ (candidate is δ below cut) → FAIL
- **H_1:** θ = θ_c + δ (candidate is δ above cut) → PASS

Where δ = 0.2 (configurable).

**Rationale:** A candidate at θ = θ_c exactly is neither clearly passing nor clearly failing. The indifference region prevents SPRT oscillation for candidates very close to the boundary. If true θ is within [θ_c - δ, θ_c + δ], SPRT may take many items to classify (this is expected — borderline candidates require more measurement).

### Error Rate Interpretation

- **α = 0.05 (Type I):** If a candidate's true ability is θ_0 = θ_c - δ = -0.2 (below cut), the probability of incorrectly classifying them as PASS is ≤ 5%.
- **β = 0.05 (Type II):** If a candidate's true ability is θ_1 = θ_c + δ = +0.2 (above cut), the probability of incorrectly classifying them as FAIL is ≤ 5%.

For candidates with true ability far from the boundary (θ < -0.5 or θ > +0.5), the actual error rates are much lower (< 1%) because the evidence accumulates faster.

### Example

Candidate starts at θ̂ = 0.0 (neutral prior). Cut score θ_c = 0.0, δ = 0.2.

**Item 1:** arch-001 (a=1.2, b=0.3)
- P_1 = P(0.2, 1.2, 0.3) = 0.494
- P_0 = P(-0.2, 1.2, 0.3) = 0.422
- Candidate answers **correctly** (X_1 = 1)
- LR_1 = log(0.494 / 0.422) = log(1.171) = 0.158

B < 0.158 < A → **CONTINUE**

**Item 2:** arch-003 (a=1.3, b=0.5)
- P_1 = P(0.2, 1.3, 0.5) = 0.412
- P_0 = P(-0.2, 1.3, 0.5) = 0.327
- Candidate answers **correctly** (X_2 = 1)
- LR_2 = LR_1 + log(0.412 / 0.327) = 0.158 + 0.232 = 0.390

Still CONTINUE...

After 8 items, all correct:
- LR_8 ≈ 3.1 > A=2.94 → **PASS**

If the candidate had answered 5 correct, 3 incorrect:
- LR_8 ≈ 0.5 → CONTINUE (needs more items)

If the candidate had answered 2 correct, 6 incorrect:
- LR_8 ≈ -3.2 < B=-2.94 → **FAIL**

---

## Item Selection Algorithm

### Objective

After each response, select the next item from the eligible pool that:

1. **Maximizes Fisher Information** at the current ability estimate θ̂ (for measurement efficiency)
2. **Balances content** to ensure domain coverage matches the blueprint weights
3. **Respects exposure control** to prevent item overuse

### The Composite Scoring Function

Each eligible item i receives a score:

```
score_i = w_info × info_score_i + w_content × content_score_i
```

Where:
- `w_info = 0.7, w_content = 0.3` (default weights)
- For the first 8 items: `w_info = 0.5, w_content = 0.5` (early-exam boost for broad sampling)

**Information score (normalized 0–1):**

```
info_score_i = I(θ̂ | a_i, b_i) / max_info_in_pool
```

This normalizes Fisher Information so the best item gets score=1.0.

**Content score (normalized 0–1):**

```
content_score_i = deficit(domain_of_item_i) / max_deficit_across_domains
```

Where deficit for domain d:

```
deficit_d = max(0, target_proportion_d - actual_proportion_d) / target_proportion_d
```

**Example:**

Blueprint target for Domain 3 (Process Orchestration): 20%  
After 5 items: Domain 3 count = 0 items (0%)  
Deficit_3 = (0.20 - 0.00) / 0.20 = 1.0 (maximum deficit — this domain is underrepresented)

Blueprint target for Domain 8 (Deployment): 6%  
After 5 items: Domain 8 count = 1 item (20%)  
Deficit_8 = (0.06 - 0.20) / 0.06 = -2.33 → max(0, -2.33) = 0.0 (no deficit — overrepresented, don't boost)

### Selection Process

```python
def select_next_item(state: EngineState, eligible_items: List[ItemCandidate]) -> ItemCandidate:
    # 1. Filter
    eligible = [item for item in eligible_items 
                if item.item_id not in state.administered_item_ids
                and sympson_hetter_gate(item)]
    
    # 2. Score
    max_info = max(fisher_information(state.theta, item.a, item.b) for item in eligible)
    max_deficit = max(deficit(item.domain_id, state) for item in eligible)
    
    w_info = 0.5 if state.items_administered < 8 else 0.7
    w_content = 1.0 - w_info
    
    scores = []
    for item in eligible:
        info = fisher_information(state.theta, item.a, item.b)
        info_score = info / max_info
        
        content_score = deficit(item.domain_id, state) / max_deficit if max_deficit > 0 else 0.0
        
        composite = w_info * info_score + w_content * content_score
        scores.append((composite, item))
    
    # 3. Select
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[0][1]  # item with highest composite score
```

### Why Composite Scoring?

**Pure max-information selection** (w_info=1.0, w_content=0.0) would be most efficient psychometrically, but:
- Early in the exam (items 1-5), we don't have a good θ̂ estimate. Selecting items near θ̂=0.0 might miss the candidate's actual level.
- Pure max-info can cause domain imbalance. If Domain 3 items happen to have higher discrimination, they'll be selected disproportionately.
- For content validity, the exam must sample all 8 domains per the blueprint (even if some domains have lower-discrimination items).

**Pure content-balanced selection** (w_info=0.0, w_content=1.0) would ensure exact blueprint proportions, but:
- Measurement efficiency suffers. We might select a low-discrimination item just because its domain is underrepresented.
- SPRT takes longer to converge (more items needed to reach confidence boundaries).

**Composite scoring (0.7 / 0.3)** balances these:
- Primarily driven by information (measurement efficiency)
- Content deficit provides a tiebreaker and ensures no domain is completely ignored
- Validated via Monte Carlo: all domains within ±1.2% of blueprint targets across 1000 sessions

---

## Content Balancing

### The Blueprint Weights

From the exam blueprint (`cert/Exam-Blueprint-Agentic-Enterprise.md`), the domain weights are:

| Domain | Target % | Explanation |
|--------|----------|-------------|
| 1. Agentic Architecture Design | 15% | Foundational design decisions |
| 2. Experience Layer Integration | 12% | Channel adapters (Slack, chat) |
| 3. AI-Powered Process Orchestration | 20% | The "brain" — highest weight, most complexity |
| 4. System APIs as Agent Tools | 15% | Backend wrappers for AI agents |
| 5. Enterprise AI Service Configuration | 12% | Bedrock, AI Gateway setup |
| 6. Salesforce Platform Configuration | 10% | Data Cloud, Service Cloud config |
| 7. Agent Governance at Enterprise Scale | 10% | Policy enforcement, observability |
| 8. Deployment and Operations | 6% | CloudHub deployment, monitoring |

### Tracking Domain Counts

The `EngineState` maintains:

```python
domain_counts: dict[str, int] = {
    "1": 0, "2": 0, "3": 0, "4": 0,
    "5": 0, "6": 0, "7": 0, "8": 0
}
```

After each item, `domain_counts[domain_id] += 1`.

### Deficit Calculation

For domain d, after n items administered:

```
actual_proportion_d = domain_counts[d] / n
target_proportion_d = blueprint_weight_d
deficit_d = max(0, target_proportion_d - actual_proportion_d) / target_proportion_d
```

**Normalization:** Divide by target_proportion so domains with small weights (6% for Domain 8) aren't permanently disadvantaged relative to large weights (20% for Domain 3).

**Example after 10 items:**

Domain 3 (target 20%): 1 item administered (10% actual)
```
deficit_3 = (0.20 - 0.10) / 0.20 = 0.50 (50% below target)
```

Domain 1 (target 15%): 2 items administered (20% actual)
```
deficit_1 = (0.15 - 0.20) / 0.15 = -0.33 → max(0, -0.33) = 0.0 (no deficit)
```

When selecting item 11, Domain 3 items get a content_score boost proportional to 0.50, while Domain 1 items get 0.0.

### Early-Exam Content Boost

For the first 8 items, we use `w_content = 0.5` (vs. 0.3 thereafter). **Rationale:**

- Early in the exam, θ̂ is uncertain (based on 1-2 responses). Max-info selection might cluster around θ̂=0.0, missing the candidate's actual level.
- Broad domain sampling in the first 8 items ensures we "cover the waterfront" — hitting all major content areas early.
- After 8 items, we have a reasonable θ̂ estimate and can afford to focus more on information (w_info=0.7).

### Validation

Monte Carlo simulation (1000 candidates, 180-item pool) showed domain coverage:

| Domain | Target % | Actual % (mean) | Deviation |
|--------|----------|-----------------|-----------|
| 1 | 15.0% | 15.2% | +0.2% |
| 2 | 12.0% | 11.8% | -0.2% |
| 3 | 20.0% | 20.3% | +0.3% |
| 4 | 15.0% | 14.7% | -0.3% |
| 5 | 12.0% | 12.1% | +0.1% |
| 6 | 10.0% | 9.9% | -0.1% |
| 7 | 10.0% | 10.2% | +0.2% |
| 8 | 6.0% | 5.8% | -0.2% |

All within ±0.3%, well below the ±5% tolerance for content validity.

---

## Exposure Control

### The Problem

Without exposure control, adaptive item selection gravitates toward a small set of "best" items (high discrimination, difficulty near cut score). In a 180-item pool:
- ~20 items near b=0.0 with a>1.5 might be selected 80% of the time
- ~160 items are rarely selected (b far from cut, or low discrimination)

This creates:
1. **Security risk:** High-exposure items can be harvested and shared
2. **Item pool inefficiency:** Most items are under-utilized
3. **Measurement bias:** Overused items may have memorized answer keys circulating

### Sympson-Hetter Method

Each item i has a control parameter `k_i ∈ [0, 1]`. Before considering item i for selection:

1. Generate random r ~ Uniform(0, 1)
2. If r > k_i, **gate the item** (exclude from this candidate's eligible pool)
3. If r ≤ k_i, **allow the item** (it can be selected if its composite score is highest)

**Target exposure rate:** 25% (no item should appear in more than 1 in 4 exams).

### Tuning k-values

Set k_i such that:

```
exposure_rate_i = k_i × P(item_i_is_selected | item_i_is_eligible)
```

We want `exposure_rate_i ≤ 0.25`.

**Initial k-values:** Start with k_i = 1.0 for all items (no gating). Run simulation to measure actual exposure rates.

**After calibration:** If item i has exposure_rate = 0.40 (too high):

```
k_i_new = 0.25 / 0.40 = 0.625
```

Now item i is gated ~38% of the time (1 - 0.625), reducing exposure to target.

**Iterative refinement:** Recompute k-values quarterly using real exam data:

```python
for item in item_bank:
    actual_exposure = item.exposure_count / total_sessions
    if actual_exposure > 0.25:
        item.sympson_hetter_k *= (0.25 / actual_exposure)
    # Don't increase k above 1.0 (no point gating less than current)
    item.sympson_hetter_k = min(1.0, item.sympson_hetter_k)
```

### Implementation

In `app/models/item.py`:

```python
class Item(Base):
    ...
    sympson_hetter_k: Mapped[float] = mapped_column(Float, default=1.0)
    exposure_count: Mapped[int] = mapped_column(Integer, default=0)
```

In `app/services/exposure_control.py`:

```python
def is_item_eligible(item: ItemCandidate) -> bool:
    r = random.random()
    return r <= item.sympson_hetter_k
```

In `app/services/item_selection.py`:

```python
eligible_items = [item for item in all_items
                  if item.item_id not in administered_ids
                  and is_item_eligible(item)]
```

### Validation

Monte Carlo simulation (1000 candidates, 180 items, uniform k=1.0) showed:
- Items near b=0.0 with a>1.5: exposure ~45% (too high)
- Items at b=-2.0 or b=+2.0: exposure ~2% (underused but acceptable)

After tuning k-values:
- Max exposure reduced to 26% (close to target 25%)
- Mean exposure: 18% (healthy distribution)
- Min exposure: 1% (extreme-difficulty items; this is expected)

---

## Stopping Rules

The exam terminates when one of three conditions is met:

### 1. SPRT Crosses Upper Boundary (PASS)

```
LR_n ≥ log((1-β)/α) ≈ 2.94
```

Interpretation: The accumulated evidence strongly favors H_1 (candidate is above cut). Continuing would provide little additional information. Classify as **PASS** with high confidence.

### 2. SPRT Crosses Lower Boundary (FAIL)

```
LR_n ≤ log(β/(1-α)) ≈ -2.94
```

Interpretation: The accumulated evidence strongly favors H_0 (candidate is below cut). Classify as **FAIL** with high confidence.

### 3. Ceiling Reached (Forced Decision)

```
n = max_items (40)
```

If SPRT has not crossed a boundary after 40 items, force a decision:

```
if θ̂_n > θ_c:
    decision = PASS
else:
    decision = FAIL
```

**Why force at 40 items?**

- **Practical constraint:** Candidates cannot sit for unlimited-length exams. 40 items = ~60 minutes for borderline candidates (reasonable).
- **Borderline candidates:** Those with true θ very close to θ_c (within the indifference region) may never cross SPRT boundaries. After 40 items, the measurement is precise enough (SE ≈ 0.25) to make a final call.
- **Psychometric validity:** At 40 items, total information I(θ_c) ≈ 16, giving SE(θ̂) = 0.25. The 95% CI is θ̂ ± 0.49. If θ̂ = 0.1 and θ_c = 0.0, the CI is [-0.39, +0.59]. This overlaps θ_c, so the candidate is borderline. We classify based on the point estimate (θ̂ > θ_c → PASS).

### Minimum Items Constraint

Even if SPRT crosses a boundary early (e.g., 3 correct responses with high-discrimination items), we enforce:

```
n ≥ min_items (5)
```

**Rationale:**

1. **Content validity:** A 3-item exam cannot sample all 8 domains. We need at least 5 items for minimal coverage.
2. **Measurement stability:** Early θ̂ estimates are volatile. A lucky guess on item 1 might spike θ̂ = +2.0, triggering SPRT prematurely. After 5 items, θ̂ is more stable.
3. **Face validity:** Stakeholders (employers, candidates) expect a certification exam to have some minimum substance. A 3-item exam looks like a quiz, not a professional credential.

### Implementation

In `app/services/stopping_rule.py`:

```python
def evaluate_stopping_with_theta_c(
    items_administered: int,
    cumulative_lr: float,
    current_theta: float,
    config: SessionConfig
) -> StoppingResult:
    # Minimum items not yet reached
    if items_administered < config.min_items:
        return StoppingResult(
            should_stop=False,
            decision=Decision.CONTINUE,
            reason="Below minimum item count"
        )
    
    # SPRT upper boundary
    if cumulative_lr >= config.upper_boundary:
        return StoppingResult(
            should_stop=True,
            decision=Decision.PASS,
            reason="SPRT crossed upper boundary",
            confidence=compute_confidence(cumulative_lr, config)
        )
    
    # SPRT lower boundary
    if cumulative_lr <= config.lower_boundary:
        return StoppingResult(
            should_stop=True,
            decision=Decision.FAIL,
            reason="SPRT crossed lower boundary",
            confidence=compute_confidence(cumulative_lr, config)
        )
    
    # Ceiling reached
    if items_administered >= config.max_items:
        decision = Decision.PASS if current_theta > config.theta_c else Decision.FAIL
        return StoppingResult(
            should_stop=True,
            decision=decision,
            reason="Maximum items reached, forced classification",
            confidence=1.0 - norm.cdf(abs(current_theta - config.theta_c) / theta_se)
        )
    
    # Continue
    return StoppingResult(should_stop=False, decision=Decision.CONTINUE)
```

---

## Ability Estimation

After each response, we update the candidate's ability estimate θ̂. Two methods are available:

### Expected A Posteriori (EAP)

**Used by default** because it is always well-defined.

EAP treats ability as a random variable with a prior distribution, then computes the posterior mean after observing responses:

```
θ̂_EAP = E[θ | X_1..X_n] = ∫ θ × P(θ | X_1..X_n) dθ
                         = ∫ θ × P(X_1..X_n | θ) × p(θ) dθ / ∫ P(X_1..X_n | θ) × p(θ) dθ
```

Where:
- `p(θ)` is the prior (standard normal: N(0, 1))
- `P(X_1..X_n | θ)` is the likelihood (product of 2PL probabilities)

**Numerical integration via Gaussian quadrature:**

We discretize the ability scale into 49 points from -4.0 to +4.0 (step size ≈ 0.1667), compute posterior at each point, then take the weighted mean:

```python
def estimate_theta_eap(responses, prior_mean=0.0, prior_sd=1.0, n_quadrature=49):
    theta_points = np.linspace(-4.0, 4.0, n_quadrature)
    prior = norm.pdf(theta_points, loc=prior_mean, scale=prior_sd)
    
    likelihood = np.ones(n_quadrature)
    for (a, b, correct) in responses:
        p = probability_2pl_vector(theta_points, a, b)
        likelihood *= (p if correct else (1 - p))
    
    posterior = likelihood * prior
    posterior /= np.sum(posterior)  # Normalize
    
    theta_hat = np.sum(theta_points * posterior)
    posterior_sd = np.sqrt(np.sum(((theta_points - theta_hat) ** 2) * posterior))
    
    return theta_hat, posterior_sd
```

**Advantages:**

- **Always defined:** Even with all-correct or all-incorrect responses, EAP gives a finite estimate (pulled toward the prior).
- **Stable:** Early estimates are regularized by the prior (prevents wild swings from lucky/unlucky guesses).
- **Bayesian interpretation:** If a candidate has a known history (e.g., passed a prerequisite exam), we can set a custom prior (e.g., N(0.5, 1.0) for above-average prior).

**Disadvantages:**

- **Regression toward prior mean:** Very high/low ability candidates are slightly underestimated/overestimated early in the exam (before accumulating enough responses to overwhelm the prior).

### Maximum Likelihood Estimation (MLE)

**Available but not used by default.**

MLE finds the θ that maximizes the likelihood:

```
θ̂_MLE = argmax_θ P(X_1..X_n | θ)
```

Equivalently, maximize log-likelihood:

```
LL(θ) = Σ [X_i × log(P_i) + (1 - X_i) × log(1 - P_i)]
```

Solved via Newton-Raphson iteration:

```
θ_(t+1) = θ_t + LL'(θ_t) / LL''(θ_t)
```

Where:
- LL'(θ) = first derivative (score function)
- LL''(θ) = second derivative (information)

**Advantages:**

- **Unbiased (asymptotically):** As n → ∞, θ̂_MLE → true θ.
- **No prior assumptions:** Pure maximum likelihood, no Bayesian priors.

**Disadvantages:**

- **Undefined for extreme response patterns:**
  - All correct → θ̂_MLE = +∞
  - All incorrect → θ̂_MLE = -∞
- **Unstable early:** After 1-2 items, θ̂_MLE can jump wildly.

**Why we use EAP:**

For early stopping (SPRT classification), we need stable θ̂ estimates after just 5-10 items. EAP provides this. MLE would require ad-hoc bounds (cap θ̂ at ±4.0) and wouldn't converge for extreme response patterns.

---

## Architecture Decisions

### Why FastAPI?

**Alternatives considered:** Flask, Django, Node.js/Express

**Decision:** FastAPI

**Rationale:**

1. **Async support:** Exam sessions involve I/O-bound operations (database reads/writes, authentication). FastAPI's native async/await enables high concurrency (100+ simultaneous exams on 1 vCore).
2. **Type safety:** Pydantic schemas provide request/response validation and auto-generated OpenAPI docs. Reduces bugs vs. Flask's untyped request.json.
3. **Developer experience:** Auto-reload, interactive docs at /docs, clear error messages.
4. **Performance:** ASGI (uvicorn) is faster than WSGI (gunicorn) for I/O-bound workloads.

### Why PostgreSQL?

**Alternatives considered:** MySQL, MongoDB, DynamoDB

**Decision:** PostgreSQL 16

**Rationale:**

1. **ACID transactions:** Exam session state (theta, SPRT cumulative LR, domain counts) must be updated atomically. NoSQL eventual consistency is unacceptable.
2. **JSON support:** ExamSession stores config_snapshot and domain_counts as JSONB (flexible schema without migrations for config changes).
3. **Mature ecosystem:** Alembic (migrations), asyncpg (fast async driver), SQLAlchemy ORM (type-safe queries).
4. **Analytics queries:** Admin dashboard needs aggregations (AVG test length by decision, domain coverage by session). Postgres excels at this vs. document stores.

### Why Async SQLAlchemy?

**Alternatives considered:** Django ORM, raw asyncpg, Tortoise ORM

**Decision:** SQLAlchemy 2.0 with asyncio extension

**Rationale:**

1. **Type safety:** Mapped columns with type hints enable mypy validation.
2. **Testability:** ORM models are pure Python classes (no database needed for unit tests of business logic).
3. **Migration support:** Alembic autogenerate detects schema changes.
4. **Ecosystem compatibility:** Works with FastAPI's dependency injection (`Depends(get_db)`).

### Pure IRT Math Module

**Decision:** `app/irt/` contains zero database, zero FastAPI, zero state.

**Rationale:**

1. **Reusability:** The same 2PL functions are used in:
   - API runtime (ability estimation)
   - Monte Carlo simulation (offline validation)
   - Item calibration scripts (marginal maximum likelihood)
   - Unit tests (pytest with synthetic data)

2. **Testability:** Pure functions are trivial to test. `test_irt/test_2pl.py` has 46 tests covering edge cases (extreme theta, overflow, vectorization) without mocking a database.

3. **Portability:** If we later build a desktop exam client (offline mode), we can reuse `irt/` without carrying FastAPI dependencies.

**Contrast:** Django ORM couples models to database. Testing requires a test database. Our design separates:
- **IRT math** (pure, stateless)
- **Business logic** (services/, stateless but coordinates IRT + database)
- **Infrastructure** (routers/, database/, async I/O)

### Item Response Persistence

**Decision:** Store every response in `item_responses` table.

**Alternatives considered:**
- Store only final theta (discard response history)
- Store responses in JSONB array on exam_session

**Rationale:**

1. **Item analysis:** To recalibrate item parameters (update a, b after 200+ responses), we need per-response data (item_id, theta_after, is_correct).
2. **Audit trail:** High-stakes exams require forensic review (suspected cheating, score challenges). Need item-by-item history.
3. **Analytics:** "Which item has highest p-value?" "What's the correlation between item 5 and final decision?" Both require per-response queries.

**Tradeoff:** More storage (60 bytes per response × 40 items × 1000 candidates = 2.4 MB). Acceptable for SSD databases.

### Theta Trajectory in Session

**Decision:** `exam_session` has current_theta and theta_se, updated after each response.

**Alternatives considered:**
- Recompute theta from scratch on every request (stateless)
- Store only responses, compute theta in a view

**Rationale:**

- **Performance:** EAP estimation requires iterating 49 quadrature points × N responses. Recomputing from scratch after item 30 would be 30× slower than incremental update.
- **SPRT needs current theta:** The SPRT likelihood ratio uses θ_1 = current_theta + δ and θ_0 = current_theta - δ. Storing current_theta avoids recomputation.

**Incremental update:** After each response, call `estimate_theta_eap(all_responses_so_far)`. Not truly incremental (EAP requires full history), but fast enough (49×40 = 1960 operations at ceiling, ~1ms).

### No Subscore Reporting

**Decision:** PASS/FAIL only. No domain-level subscores (e.g., "scored 75% in Domain 3").

**Rationale:**

1. **CAT incompatibility:** Adaptive tests don't administer the same items to all candidates. Candidate A might see 3 easy Domain 3 items (all correct), Candidate B might see 2 hard Domain 3 items (1 correct). Comparing raw counts is meaningless.

2. **Statistical precision:** Domain subscores require 8–12 items per domain for acceptable SE. With an average of 14 total items, we'd have ~2 items per domain (completely unreliable).

3. **Certification philosophy:** This is a CREDENTIAL, not a report card. Employers want a binary signal: "does this person meet the MQC standard?" Subscores invite misinterpretation ("they passed, but weak in Domain 3 → maybe not qualified").

**Future enhancement:** If subsccore reporting is required, switch to a multi-stage CAT:
- Stage 1: Classify PASS/FAIL (14 items, binary SPRT)
- Stage 2 (if PASS): Administer 8 items per domain for diagnostic subscores (48 additional items, ~60 total)

---

## Validation Methodology

### Monte Carlo Simulation

**Goal:** Validate that the CAT engine achieves target error rates (α=β=0.05) and reasonable test lengths (avg <20 items).

**Method:**

1. **Generate synthetic candidates** (N=1000):
   - True abilities: θ_true ~ N(0, 1.5²)
   - This distribution represents a population where 50% are above cut (θ>0), 50% below

2. **Simulate responses:**
   - For each item selected by the CAT engine, generate response X_i:
     ```
     P(correct) = 1 / (1 + exp(-a_i * (θ_true - b_i)))
     X_i = Bernoulli(P(correct))
     ```
   - Feed responses to the engine, which updates θ̂ and selects next item

3. **Record outcomes:**
   - Final decision (PASS/FAIL)
   - Number of items administered
   - Final θ̂ and SE(θ̂)
   - Domain counts

4. **Compute metrics:**
   ```python
   # Classification accuracy
   correct_classifications = sum(
       (true_theta > theta_c and decision == PASS) or
       (true_theta <= theta_c and decision == FAIL)
   )
   accuracy = correct_classifications / N
   
   # Error rates
   false_pass = sum((true_theta <= theta_c - delta) and (decision == PASS))
   false_fail = sum((true_theta > theta_c + delta) and (decision == FAIL))
   alpha_actual = false_pass / sum(true_theta <= theta_c - delta)
   beta_actual = false_fail / sum(true_theta > theta_c + delta)
   
   # Test length
   avg_length = mean(items_administered)
   avg_length_pass = mean(items_administered | decision == PASS)
   avg_length_fail = mean(items_administered | decision == FAIL)
   avg_length_borderline = mean(items_administered | abs(true_theta - theta_c) < 0.2)
   ```

### Results

See `scripts/simulate_cat.py` output:

```
=== CAT Engine Validation Results ===
Candidates simulated: 1000

Classification Accuracy: 96.6%
  (Target: >95%)

Error Rates:
  Type I (false pass):  1.6%  (target ≤ 5%)
  Type II (false fail): 1.8%  (target ≤ 5%)

Test Length:
  Average (all):            13.9 items
  Average (clear pass):      8.1 items
  Average (clear fail):      8.8 items
  Average (borderline):     25.1 items

Domain Coverage:
  All 8 domains within ±1.2% of blueprint targets

Theta Estimation:
  RMSE: 0.382
  Correlation: 0.963
```

**Interpretation:**

- ✅ **Accuracy 96.6%:** Exceeds 95% target. Misclassifications occur only for candidates very close to θ_c (within indifference region), which is expected.
- ✅ **Error rates 1.6% / 1.8%:** Well below 5% targets. Conservative (better to fail a borderline candidate than falsely pass).
- ✅ **Avg 13.9 items:** 65% shorter than 40-item ceiling. Clear pass/fail candidates finish in 8 items (saving 75% of items).
- ✅ **Borderline 25 items:** Candidates near cut (±0.2) require more items for confident classification (this is psychometrically sound).
- ✅ **Domain coverage ±1.2%:** Content validity maintained despite adaptive selection.

### Operational Beta

**Next step:** Run 300-candidate beta with real item pool (180 items written from blueprint).

**Metrics to track:**

1. **Pass rate:** Should be 60–70% (if much higher/lower, cut score θ_c needs adjustment)
2. **Item exposure:** Max exposure should be <30% after Sympson-Hetter tuning
3. **Test length distribution:** Should match simulation (mean ~14, borderline ~25)
4. **Item statistics:** After 200+ exposures per item, calibrate a/b via marginal MLE
5. **Candidate feedback:** "Did the exam feel too short?" "Were items relevant to the job?"

**Item calibration process:**

1. Collect 200+ responses per item (from beta candidates)
2. Fit 2PL model via marginal maximum likelihood (EM algorithm):
   - E-step: Estimate θ for each candidate given current a/b
   - M-step: Estimate a/b for each item given current θ
   - Iterate until convergence
3. Compare calibrated (a, b) to SME estimates (initial seed values)
4. Retire items with a < 0.30 (poor discrimination) or misfit (high residual variance)
5. Promote items with a ≥ 0.40 and good fit from pretest → active

---

## Future Enhancements

### 3-Parameter Logistic (3PL) Model

Add a guessing parameter c (pseudo-chance level):

```
P(θ, a, b, c) = c + (1 - c) / (1 + exp(-a * (θ - b)))
```

**When to use:** Multiple-choice items have non-zero probability of correct even at θ=-∞ (random guessing). The 3PL models this.

**Tradeoff:** 3PL requires larger sample sizes for calibration (300+ responses vs. 200 for 2PL). Only use if guessing is prevalent (4-option items with obvious distractors).

### Multistage Adaptive Testing (MST)

Hybrid between CAT and fixed-form:
- Stage 1: Short routing test (8 items) → classify into High/Medium/Low ability
- Stage 2: Targeted module (16 items matched to stage-1 classification)

**Advantages:** Allows item review (entire stage at once), easier logistics (pre-assembled modules)

**Disadvantages:** Less efficient than full CAT, still requires large item pool

### Bayesian Prior from Candidate History

If candidate has taken related exams (e.g., prerequisite "MuleSoft Developer Level 1"):
- Set prior N(μ, σ²) where μ = 0.5 (above-average prior for someone with prerequisite)
- Reduces test length for candidates with known history

**Implementation:** Add `prior_mean` and `prior_sd` columns to `candidates` table, use in EAP estimation.

---

## References

- **Wald, A.** (1945). *Sequential Analysis*. Wiley. (Original SPRT derivation)
- **Lord, F. M.** (1980). *Applications of Item Response Theory to Practical Testing Problems*. Erlbaum. (2PL model, Fisher Information)
- **Sympson, J. B., & Hetter, R. D.** (1985). *Controlling Item-Exposure Rates in Computerized Adaptive Testing*. Proceedings of the 27th annual meeting of the Military Testing Association. (Exposure control method)
- **van der Linden, W. J.** (2010). *Elements of Adaptive Testing*. Springer. (Modern CAT theory)
- **Weiss, D. J., & Kingsbury, G. G.** (1984). *Application of Computerized Adaptive Testing to Educational Problems*. Journal of Educational Measurement, 21(4), 361–375. (Content balancing in CAT)

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-24  
**Maintained By:** Certification Engine Team
