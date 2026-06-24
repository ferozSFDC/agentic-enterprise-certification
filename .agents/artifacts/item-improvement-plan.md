# Item Improvement Plan

## Length Cues Identified (Manual Review)

From visual inspection of seed_items.yaml, these items have significant length cues:

1. **exp-001** (line 105): Correct answer is 40+ words, distractors ~20-30 words
   - Fix: Trim correct to "Return 200 OK immediately, process in background, post result via Slack API"

2. **sys-001** (line 259): Correct answer is ~50 words, distractors ~30 words
   - Fix: Already flagged in psychometric analysis - trim to match distractor length

3. **sys-002** (line 281): Correct answer is ~60 words, distractors ~25-35 words
   - Fix: Trim correct to "Query Salesforce for existing refund by hash(customerId + orderNumber + amount); return existing if found"

4. **sys-003** (line 307): Correct answer is ~45 words, distractors ~30 words
   - Fix: Trim to "Query ContactPointEmail by email → get PartyId → query Individual by PartyId"

5. **exp-003** (line 153): Correct answer is ~45 words, distractors ~25 words
   - Fix: Trim to "Open circuit, return degraded response, probe after cooldown"

6. **proc-003** (line 231): Correct answer is ~35 words, distractors ~25 words
   - Fix: Minor - acceptable ratio

## New Items Needed (36 total)

### Easy Items (12 items, b < -1.0)
Target: Simple 1-2 sentence scenarios, basic pattern recognition

**Domains to cover:**
- Domain 1 (Architecture): 2 items
- Domain 2 (Experience): 2 items  
- Domain 3 (Process): 2 items
- Domain 4 (System APIs): 2 items
- Domain 5 (AI Services): 1 item
- Domain 6 (Salesforce): 1 item
- Domain 7 (Governance): 1 item
- Domain 8 (Operations): 1 item

**Example easy item:**
```yaml
- id: "arch-004"
  domain_id: 1
  objective_id: "1.1"
  cc_level: 2
  status: "pretest"
  discrimination: 1.0
  difficulty: -1.2
  scenario: |
    An API endpoint returns HTTP 200 with body: {"status": "REJECTED", "reason": "Insufficient inventory"}.
  stem: "Is this a technical failure or a business outcome?"
  options:
    - text: "Technical failure — HTTP 200 means success, but REJECTED is a failure"
      rationale: "..."
    - text: "Business outcome — the API executed successfully and returned a valid business decision"
      rationale: "CORRECT. This is the '200 for business outcomes' pattern..."
    - text: "Technical failure — should return HTTP 422 Unprocessable Entity"
      rationale: "..."
    - text: "Business outcome — but should return HTTP 201 Created instead of 200"
      rationale: "..."
  correct_index: 1
  tags: ["200-for-business-outcomes", "http-status"]
```

### Medium Items (18 items, 0.0 ≤ b < 1.0)
Continue current scenario complexity (3-4 sentences)

**Distribution:**
- Domain 1: 2 items
- Domain 2: 3 items
- Domain 3: 3 items
- Domain 4: 2 items
- Domain 5: 2 items
- Domain 6: 2 items
- Domain 7: 2 items
- Domain 8: 2 items

### Hard Items (6 items, b ≥ 1.0)
4-5 sentence scenarios, high cognitive load, multi-domain integration

**Distribution:**
- Domain 1: 1 item (architecture + AI)
- Domain 3: 2 items (process orchestration + governance)
- Domain 4: 1 item (System APIs + Data Cloud)
- Domain 6: 1 item (Salesforce + identity)
- Domain 7: 1 item (governance + operations)

### Exhibit Items (6 items, mixed difficulty)
"Refer to the exhibit..." pattern

**Types:**
1. RAML specification (URI construction) - Domain 4
2. Mule XML config (flow structure) - Domain 2
3. JSON payload (DataWeave transform) - Domain 3
4. agent-network.yaml (MCP tool schema) - Domain 7
5. Data Cloud DMO schema (query pattern) - Domain 6
6. Circuit breaker config (state transitions) - Domain 2

## Pretest Marking Strategy

After adding 36 items (total 60):
- Mark 30 items (50%) as "pretest"
- Ensure each domain has ~50% pretest items
- Current 24 items: mark 12 as pretest
- New 36 items: mark 18 as pretest

## Implementation Steps

1. Fix length cues in existing 24 items (Edit seed_items.yaml)
2. Generate 12 easy items (Write to temp file)
3. Generate 18 medium items (Write to temp file)
4. Generate 6 hard items (Write to temp file)
5. Generate 6 exhibit items (Write to temp file)
6. Merge all into seed_items.yaml
7. Update item count metadata
8. Commit and push

## Success Criteria

- ✅ All items have correct_length ≤ 1.2× max_distractor_length
- ✅ Difficulty distribution: 20% easy, 60% medium, 20% hard
- ✅ 50% items marked as "pretest"
- ✅ All 8 domains have 5-8 items each
- ✅ CC distribution maintained: 75% CC2, 25% CC3
- ✅ 10% items use "Refer to the exhibit" pattern
