# Course Catch-Up System

This tool lets any student fast-forward to any exercise without manually completing earlier exercises.

---

## Quick Start

```bash
# 1. Install dependencies (once)
pip install -r setup/requirements.txt

# 2. Copy the credential template
cp setup/student.template.json student.json

# 3. Fill in your variable section (see below)
#    Ops pre-fills the stable section — do not change it

# 4. Run up to the checkpoint you need
python setup/catchup.py --student student.json --checkpoint 3
```

---

## Checkpoint Reference

| Checkpoint | Exercise | What it sets up |
|-----------|----------|----------------|
| CP1 | Exercise 1 | Golden Contacts in Service Cloud, Data Cloud DMO seed records |
| CP2 | Exercise 2 | Slack app manifest + bot token (1 manual browser step) |
| CP3 | Exercise 3 | Lambda, Bedrock Agent, Bedrock alias Production-v1 |
| CP4 | Exercise 4 | ai-orchestrator running locally on port 8082 |
| CP5 | Exercise 5 | data-cloud-sapi (:8083) + service-cloud-mcp (:8084) running locally |
| CP6 | Exercise 6 | All 4 apps deployed and running on CloudHub |

Each checkpoint is **idempotent** — safe to run multiple times. If the artifact already exists, it is skipped.

---

## CLI Reference

```
python setup/catchup.py --student PATH [options]

  --student PATH        Path to filled-in student.json (required)
  --checkpoint N        Run CPs 1 through N (default: 6)
  --only N              Run only CP N (for targeted re-runs)
  --dry-run             Print what would happen; make no changes
  --verbose             Show full API responses
```

**Examples:**

```bash
# Late arrival on Day 2 — need everything through Exercise 3
python setup/catchup.py --student student.json --checkpoint 3

# Restarted laptop — need to restart the local apps
python setup/catchup.py --student student.json --only 4
python setup/catchup.py --student student.json --only 5

# Preview what a full setup would do
python setup/catchup.py --student student.json --checkpoint 6 --dry-run
```

---

## student.json — What to Fill In

The `variable` section is **per-student**. Get these values from your Anypoint account:

| Field | Where to find it |
|-------|-----------------|
| `anypoint.orgId` | Anypoint Platform → Access Management → Business Groups |
| `anypoint.environmentId` | Anypoint → Environments → Sandbox → copy ID from URL |
| `anypoint.username` | Your Anypoint login email |
| `anypoint.password` | Your Anypoint login password |
| `anypoint.exchange.clientId` | Anypoint → Access Management → Connected Apps |
| `anypoint.exchange.clientSecret` | Same — copy when creating the Connected App |
| `cloudHub.deploymentTargetName` | Anypoint → Runtime Manager → Servers/Targets |
| `student.email` | Your email address |

The `stable` section is **pre-filled by ops** and shared across all students in the cohort.

---

## CP2 — The One Manual Step

Slack does not allow programmatic app creation without user OAuth consent. CP2 handles this by:

1. Generating the complete Slack app manifest JSON
2. Printing a link to `https://api.slack.com/apps` with instructions
3. **You click one link, authorize the app, paste back 2 tokens**
4. The script saves those tokens to your `student.json` automatically

This is the only step that cannot be fully automated.

---

## Pre-Built JARs

The Mule app JARs are published to GitHub Releases on each course update (tag: `course-v1.0`).

The catch-up script downloads them automatically on first run and caches them in `setup/jars/`. Students who prefer to build from source can run `mvn package` in each app directory — the JARs must be placed in `setup/jars/` with the filename `<app-name>.jar`.

---

## Ops Runbook

**One-time per cohort:**

1. Fill in the `stable` section of `student.template.json` with shared credentials
2. Commit the updated template (without secrets — use placeholder values in the repo, distribute actual values separately)
3. Build and publish JARs: tag a release on GitHub, upload all 4 JARs as release assets

**Per student, at course start:**

```bash
# Give each student their filled-in student.json (or have them fill in the variable section)
# No other per-student setup required
```

**If a student misses a session:**

```bash
python setup/catchup.py --student student.json --checkpoint N
# where N = the exercise number they are resuming
```

---

## Troubleshooting

**"student.json is missing required values"**
→ Open `student.json` and fill in all empty strings in the `variable` section.

**"check() raised: ..."** on CP1
→ Verify your Salesforce `serviceCloud.clientId/clientSecret` are for a Connected App with OAuth `client_credentials` grant and `api` scope.

**"check() raised: ..."** on CP3
→ Verify your AWS `accessKeyId/secretAccessKey` have `AmazonBedrockFullAccess` and the `bedrock:InvokeAgent` permission.

**CP4/CP5 timeout ("did not become healthy")**
→ Check the log file at `setup/jars/<app-name>.log`. Usually a missing secret or port conflict. Kill the process and re-run with `--only N`.

**"Deploy failed: 401"** on CP6
→ Your Exchange Connected App may be missing the `Runtime Manager` API scope. Add it in Anypoint → Access Management → Connected Apps → Scopes.
