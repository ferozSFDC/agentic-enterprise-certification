## Module 3: The Experience Layer — Slack as the Front Door

---

### Slide 3.1 — Where We Are

> [DIAGRAM — north star architecture, highlight the Experience Layer (slack-agent-router) and the Slack User. Grey out Process and System layers. Label: "You are here."]

You've built the foundation (Salesforce). Now we build the **front door** — the channel where humans interact with the agent.

---

### Slide 3.2 — Why Slack (and Not a Custom UI)

Enterprise agents live where employees already work.

| Alternative | Problem |
|-------------|---------|
| Custom web app | Context-switch required; low adoption |
| Email | Async, no real-time, no modals |
| Salesforce UI | Only for SF-licensed users |
| **Slack** | Already open, real-time, modals/threads/buttons, API-native |

The agent is a **participant in the conversation**, not a separate system.

---

### Slide 3.3 — Slack's Event Architecture

> [DIAGRAM — show Slack cloud on left pushing events to MuleSoft endpoint on right, with the 3-second clock emphasized]

Slack doesn't poll. It **pushes** events to your endpoint.

```
User: "@Agent Fabric refund for order 123"
         │
         │ HTTP POST (within milliseconds)
         ▼
┌──────────────────────────────────────┐
│ https://your-app/slack/events        │
│                                      │
│  You have 3 SECONDS to return 200.   │
│  After that, Slack retries.          │
│  Up to 3 retries.                    │
└──────────────────────────────────────┘
```

**Three endpoints you register in the Slack app:**

| Endpoint | Feature | Trigger |
|----------|---------|---------|
| `/slack/events` | Event Subscriptions | @mentions, DMs |
| `/slack/commands` | Slash Commands | `/refund ...` |
| `/slack/interactivity` | Interactivity | Modal submissions, buttons |

These are the three paths the MuleSoft `slack-agent-router` exposes.

---

### Slide 3.4 — The 3-Second Problem and Idempotency

> [DIAGRAM — timeline showing: event arrives at T=0, processing takes 4s, Slack retries at T=3, T=6, T=9. Show duplicate actions without idempotency vs. clean dedup with Object Store]

Agent reasoning takes 10+ seconds. Slack gives you 3.

**Pattern**: Acknowledge immediately (200 OK), process asynchronously, respond via `chat.postMessage`.

But what about the retries that already fired?

```
WITHOUT idempotency:              WITH idempotency (Object Store):
─────────────────────             ─────────────────────────────────
Event → process → case created    Event → store ID → process → case
Retry → process → DUPLICATE       Retry → ID exists → 200 (skip)
Retry → process → TRIPLICATE      Retry → ID exists → 200 (skip)
```

**Rule**: Deduplicate by event ID in Object Store (TTL 30 min), not by retry header.

---

### Slide 3.5 — Bot Token Scopes: Only What You Need

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Detect @mentions |
| `chat:write` | Post responses |
| `commands` | Handle `/refund` |
| `im:history` | Read DM context |
| `im:read` | Access DM channel info |
| `im:write` | Send DMs |
| `users:read` | Look up user profiles |
| `users:read.email` | **Get email for OBO identity** |

That last scope is the linchpin. Without `users:read.email`, the agent can't resolve which Salesforce customer is asking. Data Cloud query returns nothing. The agent is blind.

---

### Slide 3.6 — What to Listen For (and What NOT To)

| Event | Subscribe? | Why |
|-------|-----------|-----|
| `app_mention` | ✅ | User explicitly addresses the bot |
| `message.im` | ✅ | DMs — private/sensitive requests |
| `message.channels` | ❌ | Every message in every channel — privacy violation |
| `message.groups` | ❌ | Same problem in private channels |

**Only listen when explicitly addressed.** An enterprise agent that reads every message is a liability, not a feature.

---

### Slide 3.7 — The Challenge Handshake

When you set the Request URL, Slack sends a one-time verification:

```json
POST /slack/events
{
  "type": "url_verification",
  "challenge": "3eZbrw1aBm2rZgRNFdx..."
}
```

Your app echoes it back: `{ "challenge": "3eZbrw1aBm2rZgRNFdx..." }`

**Implication**: The MuleSoft `slack-agent-router` must be **deployed and running** before you can verify the URL. If it's not running, configuration fails.

> This creates a chicken-and-egg: you need the Slack token to deploy the MuleSoft app, but you need the MuleSoft app running to verify the Slack URL. Solution: deploy MuleSoft first with a placeholder token, verify the URL, then update with the real token.

---

### Slide 3.8 — One Credential to Rule Them All

| Credential | Format | Used by MuleSoft? |
|------------|--------|-------------------|
| **Bot User OAuth Token** | `xoxb-...` | ✅ Calls Slack API |
| Signing Secret | hex string | ❌ (request verification — future enhancement) |
| App Token | `xapp-...` | ❌ (Socket Mode — we use HTTP) |

The Bot Token is the ONLY Slack credential the MuleSoft app needs.

It's used as: `Authorization: Bearer xoxb-...` when calling `chat.postMessage`, `views.open`, etc.

---

### Slide 3.9 — [VIDEO PLACEHOLDER] Slack App Configuration Walkthrough

> **Screencast video (3 min)**: Walk through api.slack.com — create app, add scopes, set Event Subscriptions URL, create slash command. Show the URL verification succeeding (green checkmark). This replaces 10 slides of screenshots.

---

### Slide 3.10 — Exercise Time

## 🔨 Exercise 2: Slack Workspace & App Setup

**What you'll build:**
- Slack workspace (personal email → transfer ownership to work email)
- Slack app "Agent Fabric" with 8 bot scopes
- Event Subscriptions → `/slack/events`
- Interactivity → `/slack/interactivity`
- Slash command `/refund` → `/slack/commands`

**What you'll record:**
- Bot User OAuth Token (`xoxb-...`) — the one credential MuleSoft needs

**Time**: ~30 minutes

> **Note**: Event Subscriptions URL verification requires the MuleSoft app to be running. You may complete that step after Exercise 3.

📖 **Open**: `exercise-guide/02-slack-workspace.md`

---
