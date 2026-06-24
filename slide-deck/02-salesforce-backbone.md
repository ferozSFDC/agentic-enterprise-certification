## Module 2: The Salesforce Backbone — Data Cloud and Service Cloud

---

### Slide 2.1 — Where We Are

> [DIAGRAM — reuse the north star architecture from 1.5, but highlight ONLY the bottom two boxes: Salesforce Data Cloud and Salesforce Service Cloud. Grey out everything else. Label: "You are here."]

This module covers the **foundation layer** — the Salesforce org that provides:
- **Context** (Data Cloud) — who is this customer?
- **Action** (Service Cloud) — what should we do for them?

Without this foundation, the agent has no memory and no hands.

---

### Slide 2.2 — Two Sides of the Same Org

| Capability | Data Cloud | Service Cloud |
|-----------|-----------|---------------|
| Role | **Context** — who is this customer? | **Action** — what should we do? |
| Data direction | Read (queries) | Write (create/update) |
| API pattern | SQL API (`/ssot/query`) | REST API + Flow invocation |
| Agent use | Grounding — "Platinum tier, low churn" | Execution — "Create refund case" |
| MuleSoft app | `data-cloud-sapi` | `service-cloud-mcp` |

The AI can't make a good decision without context. It can't act on a decision without Service Cloud.

---

### Slide 2.3 — Data Cloud: Not a Database — An Identity Engine

> [DIAGRAM — horizontal pipeline: scattered records on left → Identity Resolution funnel in center → single Unified Individual on right]

Data Cloud takes fragmented customer data and produces **one truth**:

```
Contact: sarah.chen@globaltech.com (CRM)
Contact: s.chen@globaltech.com (Marketing Cloud)
Web visitor: sarah_c@gmail.com (matched by name)
                    ↓
        Identity Resolution
                    ↓
Unified Individual: ONE profile, queryable via SQL API
  • Name: Sarah Chen
  • Loyalty: Platinum
  • Churn Risk: Low
```

The agent queries this unified profile — not scattered records across systems.

---

### Slide 2.4 — Data Cloud Architecture: How Data Flows

> [DIAGRAM — vertical flow, full page. Key mental model for the exercise.]

```
┌─────────────┐
│ CRM Contact │  (source of truth)
│ 21 records  │
└──────┬──────┘
       │  Data Stream (ingestion)
       ▼
┌─────────────────┐
│ Data Lake Object │  Contact_Home
│ (raw, unmapped) │  13 fields selected
└──────┬──────────┘
       │  Field Mapping (visual canvas)
       ▼
┌──────────────────────────────────────────┐
│         Data Model Objects (DMOs)         │
│                                          │
│  ┌──────────────┐    ┌────────────────┐  │
│  │  Individual  │    │ Contact Point  │  │
│  │  • Id        │    │ Email          │  │
│  │  • FirstName │    │ • EmailAddress │  │
│  │  • LastName  │◀───│ • Party (FK)   │  │
│  │  • Loyalty   │    │ • Id           │  │
│  │  • ChurnRisk │    └────────────────┘  │
│  └──────────────┘                        │
└──────────────────────┬───────────────────┘
                       │  Identity Resolution
                       ▼
┌──────────────────────────────────────────┐
│         Unified Individual                │
│  Queryable: /services/data/v62.0/ssot/query │
└──────────────────────────────────────────┘
```

---

### Slide 2.5 — The Two-Step Query Pattern

This is exactly what the MuleSoft `data-cloud-sapi` app implements:

**Step 1** — Email → Party ID:
```sql
SELECT ssot__PartyId__c
FROM ssot__ContactPointEmail__dlm
WHERE ssot__EmailAddress__c = 'sarah.chen@globaltech.com'
```

**Step 2** — Party ID → Full Profile:
```sql
SELECT ssot__Id__c, ssot__FirstName__c, ssot__LastName__c,
       Loyalty_Tier__c, Churn_Risk__c
FROM ssot__Individual__dlm
WHERE ssot__Id__c = '003dL000027fyeNQAQ'
```

**Why two steps?** Contact Point Email is a separate DMO. The `Party` field is the foreign key that links them. This is Data Cloud's normalized identity model.

---

### Slide 2.6 — The Party Field: Silent Killer

> [DIAGRAM — side-by-side comparison. Left: correct mapping (green arrows). Right: wrong mapping (red arrow on Party). Both show "Identity Resolution: Success" but right shows "Query: empty result".]

```
✅ CORRECT                          ❌ WRONG (looks fine, breaks silently)
──────────────                      ──────────────────────────────────────
Contact ID → Individual Id          Contact ID → Individual Id
Contact ID → Party                  Email → Party          ← WRONG SOURCE
Email      → Email Address          Email → Email Address
```

If you map `Email` → `Party`:
- Identity Resolution completes without errors
- No warnings in the UI
- The SQL join returns **nothing**
- The agent gets empty context and makes uninformed decisions

This is the #1 Data Cloud setup failure. You'll verify it explicitly in the exercise.

---

### Slide 2.7 — Service Cloud: Giving the Agent Hands

> [DIAGRAM — simple input/output box diagram of the Autolaunched Flow]

```
REST API Call                              Salesforce Flow
─────────────                              ───────────────
POST /actions/custom/flow/                 ┌─────────────────────┐
  Agent_Issue_Refund_Case                  │ Get Contact by Email │
{                                          └──────────┬──────────┘
  email: "sarah.chen@..."                             │
  orderId: "ORD-123"           ──────▶               ▼
  amount: 45.00                            ┌─────────────────────┐
  reason: "Late delivery"                  │ Create Case          │
}                                          │ • Contact = found    │
                                           │ • Subject = "Refund..│
                                           │ • Status = New       │
                                           └──────────┬──────────┘
                                                      │
{ "isSuccess": true }          ◀──────               ▼
```

Why a Flow (not Apex)?
- Declarative — admins can inspect without code
- Invocable via REST — no custom endpoints needed
- Auditable — visible in Setup
- Deployable as metadata XML — automatable via CLI

---

### Slide 2.8 — Connected App: OAuth 2.0 Client Credentials

> [DIAGRAM — sequence diagram: MuleSoft on left, Salesforce on right, arrows showing token exchange then API call]

```
MuleSoft App                              Salesforce (My Domain)
    │                                              │
    │── POST /services/oauth2/token ──────────────▶│
    │   grant_type = client_credentials            │
    │   client_id = <Consumer Key>                 │
    │   client_secret = <Consumer Secret>          │
    │                                              │
    │◀──── { access_token: "00D..." } ────────────│
    │                                              │
    │── POST /services/data/v62.0/ssot/query ─────▶│
    │   Authorization: Bearer 00D...               │
    │                                              │
    │◀──── { data: [{ Sarah Chen, Platinum }] } ──│
```

**Why Client Credentials?**
- No password, no security token to rotate
- Server-to-server — no interactive login
- "Run As" user determines permissions
- Token endpoint = **My Domain URL** (not login.salesforce.com)

---

### Slide 2.9 — What Can Go Wrong

| Failure | Silent? | Root Cause | Prevention |
|---------|---------|-----------|------------|
| Query returns empty | ✅ Yes | Party → Email (wrong source) | Verify: Party → Contact ID |
| 0 Unified Profiles | ❌ Visible | Contact Point Email not mapped | Both DMOs must be mapped |
| Token returns 401 | ❌ Visible | Wrong token endpoint | Use My Domain URL |
| CloudHub "invalid_grant" | ❌ Visible | IP restrictions | Relax IP restrictions |
| Flow returns 404 | ❌ Visible | Flow not activated | Check Active status |
| Case has no Contact | ✅ Yes | Email mismatch | Golden Contact email = Slack user email |

The silent failures are the dangerous ones. The exercise has explicit verification steps for each.

---

### Slide 2.10 — [VIDEO PLACEHOLDER] Data Cloud + Service Cloud in 90 Seconds

> **Demo video (90 sec)**: Live terminal session — acquire token via Client Credentials → query Data Cloud → get Sarah Chen's profile → invoke the Flow → show Case appear in Salesforce UI. No slides, just commands and results.

---

### Slide 2.11 — Exercise Time

## 🔨 Exercise 1: Salesforce Org Setup

**What you'll build:**
- Custom fields on Contact (Loyalty Tier, Churn Risk)
- Golden Contact record (Sarah Chen — Platinum, Low)
- Data Cloud: Data Stream → DMO Mapping → Identity Resolution
- Service Cloud: Autolaunched Flow (`Agent_Issue_Refund_Case`)
- Connected App with OAuth 2.0 Client Credentials

**What you'll prove works before leaving this exercise:**
- ✅ Token acquisition via Client Credentials
- ✅ Data Cloud SQL queries return unified profile
- ✅ Flow invocation creates Case linked to correct Contact
- ✅ Opportunity query/update confirms full CRUD access

**Time**: ~90 minutes

📖 **Open**: `exercise-guide/01-salesforce-org-setup.md`

---
