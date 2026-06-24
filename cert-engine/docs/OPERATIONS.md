# CAT Engine Operations Guide

## Table of Contents

1. [Deployment](#deployment)
2. [Configuration Management](#configuration-management)
3. [Item Lifecycle Management](#item-lifecycle-management)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Security Best Practices](#security-best-practices)
6. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)
9. [Incident Response](#incident-response)
10. [Routine Maintenance](#routine-maintenance)

---

## Deployment

### Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Load Balancer (AWS ALB / Nginx)                           │
│  • HTTPS termination                                        │
│  • Health check: /health                                    │
│  • Rate limiting: 100 req/sec per IP                        │
└────────────────┬────────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
┌──────────────┐      ┌──────────────┐
│ API Server 1 │      │ API Server 2 │
│ (uvicorn)    │      │ (uvicorn)    │
│ 2 vCPU       │      │ 2 vCPU       │
│ 4 GB RAM     │      │ 4 GB RAM     │
└──────┬───────┘      └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  ▼
         ┌─────────────────┐
         │ PostgreSQL 16   │
         │ (RDS / managed) │
         │ 4 vCPU, 16 GB   │
         │ 100 GB SSD      │
         └─────────────────┘
```

### Deployment Steps (Docker Compose)

**1. Clone and configure**

```bash
cd /opt/cat-engine
git pull origin main

# Copy production config
cp .env.production .env

# Edit secrets (use vault/parameter store in real deployment)
vim .env
```

**2. Build images**

```bash
docker-compose build
```

**3. Run database migrations**

```bash
# Backup current schema first
docker-compose exec postgres pg_dump -U cat_user -Fc cat_engine > backup-$(date +%Y%m%d).dump

# Run migrations
docker-compose run --rm app alembic upgrade head
```

**4. Start services**

```bash
docker-compose up -d

# Verify health
curl https://exam-api.example.com/health
# Expected: {"status":"healthy","database":"connected",...}
```

**5. Smoke test**

```bash
# Create test candidate
curl -X POST https://exam-api.example.com/api/v1/exam/start \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "smoke-test-001", "email": "test@example.com"}' \
  | jq .

# Expected: session_id and first item returned
```

### Deployment Checklist

- [ ] Database backup created
- [ ] Migrations applied successfully
- [ ] Health endpoint returns 200 OK
- [ ] Smoke test passes (start session + respond to 1 item)
- [ ] Log aggregation configured (CloudWatch / ELK / Datadog)
- [ ] Alerts configured (see Monitoring section)
- [ ] Rollback plan ready (previous Docker image tagged)

### Rollback Procedure

**If deployment fails:**

```bash
# Stop current version
docker-compose down

# Checkout previous tag
git checkout v1.2.3

# Rebuild and start
docker-compose build
docker-compose up -d

# Rollback migrations if schema changed
docker-compose run --rm app alembic downgrade -1
```

### Blue-Green Deployment

**For zero-downtime upgrades:**

```bash
# Deploy to "green" environment (separate docker-compose.green.yml)
docker-compose -f docker-compose.green.yml up -d

# Run smoke tests on green
curl https://exam-api-green.example.com/health

# Switch load balancer target from blue → green
# (AWS: update ALB target group, Nginx: update upstream)

# Monitor for 15 minutes
# If errors: switch back to blue
# If stable: decommission blue after 24 hours
```

---

## Configuration Management

### Environment Variables

All config via environment variables (12-factor app pattern):

```bash
# Database
CAT_DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/cat_engine

# Exam parameters
CAT_THETA_C=0.0
CAT_DELTA=0.2
CAT_ALPHA=0.05
CAT_BETA=0.05
CAT_MAX_ITEMS=40
CAT_MIN_ITEMS=5
CAT_TIME_LIMIT_MINUTES=120

# Item selection
CAT_W_INFO=0.7
CAT_W_CONTENT=0.3
CAT_MAX_EXPOSURE_RATE=0.25

# Security
CAT_SECRET_KEY=<generate with: openssl rand -hex 32>
CAT_ADMIN_API_KEY=<generate with: openssl rand -base64 32>
CAT_CORS_ORIGINS=https://exam-portal.example.com

# Observability
CAT_LOG_LEVEL=INFO  # DEBUG for troubleshooting
CAT_SENTRY_DSN=https://...@sentry.io/...  # Error tracking
```

### Secrets Management

**Never commit secrets to git.** Use:

**AWS Systems Manager Parameter Store:**

```bash
aws ssm put-parameter \
  --name /cat-engine/prod/secret-key \
  --value "$(openssl rand -hex 32)" \
  --type SecureString \
  --overwrite

# Retrieve in startup script
export CAT_SECRET_KEY=$(aws ssm get-parameter \
  --name /cat-engine/prod/secret-key \
  --with-decryption --query Parameter.Value --output text)
```

**HashiCorp Vault:**

```bash
vault kv put secret/cat-engine/prod \
  secret_key="$(openssl rand -hex 32)" \
  admin_api_key="$(openssl rand -base64 32)"

# Retrieve in docker-compose via vault agent
```

**Environment-specific config:**

```
.env.development    # Local dev (sqlite, debug logging)
.env.staging        # Staging (shared postgres, info logging)
.env.production     # Production (RDS, warn logging, Sentry)
```

### Configuration Versioning

**Exam parameters (θ_c, α, β) are versioned in the database:**

```sql
-- exam_configs table
id | theta_c | delta | alpha | beta | max_items | domain_weights | is_active | created_at
1  | 0.0     | 0.2   | 0.05  | 0.05 | 40        | {...}          | false     | 2026-01-15
2  | 0.0     | 0.2   | 0.05  | 0.05 | 40        | {...}          | true      | 2026-06-24
```

**To update exam config:**

```bash
# Via API (requires admin API key)
curl -X POST https://exam-api.example.com/api/v1/admin/config \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "theta_c": 0.0,
    "delta": 0.2,
    "alpha": 0.05,
    "beta": 0.05,
    "max_items": 40,
    "min_items": 5,
    "domain_weights": {
      "1": 0.15, "2": 0.12, "3": 0.20, "4": 0.15,
      "5": 0.12, "6": 0.10, "7": 0.10, "8": 0.06
    }
  }'

# This creates a new config (id=3) and sets is_active=true
# Previous config (id=2) is automatically set is_active=false
# Existing sessions continue using their config_snapshot (immutable)
```

**Why version configs?**

- **Audit trail:** See what cut score / error rates were used for sessions on 2026-01-15 vs. 2026-06-24
- **Session isolation:** A candidate who starts a session on June 1 (config v2) and finishes on July 1 (after config v3 is deployed) uses config v2 consistently (stored in `exam_session.config_snapshot`)

---

## Item Lifecycle Management

### Item Status States

```
┌────────┐     ┌─────────┐     ┌────────┐     ┌─────────┐
│ draft  │ --> │ pretest │ --> │ active │ --> │ retired │
└────────┘     └─────────┘     └────────┘     └─────────┘
```

| Status | Description | Selectable in CAT? | Contributes to Score? |
|--------|-------------|-------------------|----------------------|
| **draft** | Under review by SMEs, not yet validated | No | No |
| **pretest** | Embedded in live exams for calibration | Yes | No (invisible to SPRT) |
| **active** | Fully calibrated, used for classification | Yes | Yes |
| **retired** | Outdated, over-exposed, or poor fit | No | No |

### Workflow: Draft → Pretest → Active

**1. Item authoring**

```yaml
# data/new_items.yaml
items:
  - id: "arch-101"
    domain_id: 1
    objective_id: "1.2"
    cc_level: 3
    status: "draft"
    discrimination: 1.3  # SME estimate
    difficulty: 0.4     # SME estimate (will be calibrated)
    scenario: |
      An architect is designing...
    stem: "Which approach..."
    options: [...]
    correct_index: 2
    tags: ["guided-determinism", "draft-batch-2026-07"]
```

**2. SME review**

- Content validity: Does item test the stated objective?
- Distractor quality: Are wrong answers plausible?
- Scenario clarity: Can candidate understand the context?
- Bias review: Any language/cultural assumptions?

**3. Promote to pretest**

```bash
# Via API
curl -X PATCH https://exam-api.example.com/api/v1/admin/items/arch-101/status \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "pretest"}'
```

**4. Collect calibration data**

- Item appears in live exams (selected by CAT engine like any other item)
- BUT responses are NOT used for SPRT classification or ability estimation
- Target: 200+ exposures per item

**5. Calibrate parameters**

```bash
# Run offline calibration script
python scripts/calibrate_items.py --status pretest --min-responses 200

# This fits 2PL model via marginal maximum likelihood (EM algorithm)
# Outputs: calibrated (a, b) for each item + fit statistics (RMSE, infit/outfit)
```

**6. Review calibration results**

```sql
SELECT id, discrimination_sme, discrimination_calibrated, 
       difficulty_sme, difficulty_calibrated, 
       rmse, exposure_count
FROM items
WHERE status = 'pretest' AND exposure_count >= 200;
```

**Quality criteria:**
- Discrimination (a) ≥ 0.40 (acceptable), ≥ 0.80 (good), ≥ 1.20 (excellent)
- RMSE < 0.15 (good fit)
- Infit/outfit in range [0.7, 1.3] (no severe misfit)

**7. Promote to active**

```bash
# For items meeting criteria
curl -X PATCH https://exam-api.example.com/api/v1/admin/items/arch-101/status \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"status": "active", "discrimination": 1.42, "difficulty": 0.38}'
  # ^ Use calibrated values, not SME estimates
```

**8. Retire items failing criteria**

```bash
# For items with a < 0.30 or poor fit
curl -X PATCH https://exam-api.example.com/api/v1/admin/items/arch-102/status \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"status": "retired", "retirement_reason": "Low discrimination (a=0.28)"}'
```

### Bulk Import

```bash
# Import 50 items from YAML
curl -X POST https://exam-api.example.com/api/v1/admin/items/import \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [...],  # Array of item objects
    "default_status": "draft"
  }'

# Response: {"imported": 50, "skipped": 0, "errors": []}
```

### Content Refresh Cycle

**Quarterly review:**

1. **Exposure analysis:** Identify items with exposure > 30% (overused)
2. **Statistical drift:** Re-calibrate active items every 6 months (check if a/b have drifted due to curriculum updates, candidate population changes)
3. **Content validity:** Retire items referencing deprecated platform features (e.g., "Bedrock Agent v1" → v2)
4. **New items:** Target 15-20 new items per quarter (maintain 180+ pool size)

**Annual review:**

1. **Blueprint alignment:** Verify item distribution matches current JTA/blueprint weights
2. **Equity audit:** Review pass rates by subgroup (region, language, prerequisite path) — investigate if any items show differential item functioning (DIF)
3. **Cut score validation:** Modified Angoff with SME panel — recalibrate θ_c if pass rate drifts significantly from target (60-70%)

---

## Monitoring and Alerting

### Key Metrics

**1. API Health**

- **Uptime:** Target 99.9% (< 9 hours downtime per year)
- **Response time:** p50 < 200ms, p95 < 500ms, p99 < 1000ms
- **Error rate:** < 0.1% of requests return 5xx

**2. Exam Session Metrics**

- **Sessions started:** Count per hour/day
- **Sessions completed:** Count + completion rate (completed / started)
- **Sessions abandoned:** % of sessions started but not completed (target < 5%)
- **Average test length:** Mean items administered (should be ~14 ± 3)
- **Pass rate:** % of completed sessions classified PASS (target 60-70%)

**3. Item Metrics**

- **Exposure distribution:** Histogram of exposure counts (no item > 30%)
- **Item usage:** % of active items used at least once per week (target > 80%)
- **Pretest calibration:** Count of pretest items with ≥ 200 responses (ready for promotion)

**4. Database Metrics**

- **Connection pool:** Active connections, idle connections, wait time
- **Query performance:** Slow query log (queries > 100ms)
- **Disk usage:** Available space (alert when < 20% free)

### Monitoring Stack

**Option 1: Prometheus + Grafana**

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: <set-password>
```

**Expose metrics from FastAPI:**

```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)  # /metrics endpoint
```

**Option 2: AWS CloudWatch**

```python
# app/routers/exam.py
import boto3
cloudwatch = boto3.client('cloudwatch')

@router.post("/start")
async def start_exam(...):
    # Emit custom metric
    cloudwatch.put_metric_data(
        Namespace='CATEngine',
        MetricData=[{
            'MetricName': 'ExamStarted',
            'Value': 1,
            'Unit': 'Count'
        }]
    )
```

### Alert Rules

**Critical (page on-call immediately)**

| Condition | Threshold | Action |
|-----------|-----------|--------|
| API uptime | < 99% over 5 minutes | Page on-call engineer |
| Database connection failures | > 10 in 1 minute | Page + auto-restart API container |
| Error rate (5xx) | > 1% over 5 minutes | Page + check logs |

**Warning (Slack notification, no page)**

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Average test length | > 18 or < 10 (3σ from mean) | Alert psychometrician (possible item pool issue) |
| Pass rate | > 80% or < 50% over 24 hours | Alert content team (cut score may need adjustment) |
| Item exposure | Any item > 35% | Alert item manager (tune Sympson-Hetter k-value) |
| Abandoned sessions | > 10% over 24 hours | Alert UX team (check proctor issues, time limits) |

**Info (weekly report, no immediate alert)**

| Metric | Report |
|--------|--------|
| Total sessions completed | Count by day |
| Domain coverage | Actual vs. blueprint (±% deviation) |
| Item calibration queue | Count of pretest items with 150-200 responses (approaching promotion) |

### Logging Best Practices

**Structured logging (JSON format):**

```python
# app/main.py
import structlog

logger = structlog.get_logger()

@router.post("/respond")
async def respond_to_item(session_id: str, response: ExamRespondRequest):
    logger.info(
        "item_response",
        session_id=session_id,
        item_id=response.item_id,
        is_correct=(response.response_index == item.correct_index),
        theta_after=updated_state.theta,
        cumulative_lr=updated_state.cumulative_lr,
        decision=result.decision if result.should_stop else None
    )
```

**Log levels:**

- **DEBUG:** Detailed IRT calculations (EAP quadrature points, Fisher Information per item) — only in development
- **INFO:** Session lifecycle (started, response, stopped), item selection, SPRT decisions
- **WARN:** Unexpected but recoverable (candidate submitted invalid item ID, session timeout)
- **ERROR:** Application errors (database connection failed, IRT calculation NaN)
- **CRITICAL:** System-level failures (out of memory, disk full)

**Log aggregation:**

- ELK Stack (Elasticsearch + Logstash + Kibana)
- Splunk
- AWS CloudWatch Logs Insights
- Datadog Logs

**Sample queries:**

```sql
-- Find all sessions that reached ceiling (40 items) in past 24 hours
SELECT session_id, candidate_id, decision, final_theta
FROM exam_sessions
WHERE completed_at > NOW() - INTERVAL '24 hours'
  AND items_administered = 40;

-- Calculate average test length by decision
SELECT decision, AVG(items_administered) as avg_length, COUNT(*) as count
FROM exam_sessions
WHERE status = 'completed'
  AND completed_at > NOW() - INTERVAL '7 days'
GROUP BY decision;
```

---

## Security Best Practices

### Authentication & Authorization

**Candidate Authentication (JWT):**

```python
# app/routers/auth.py
from jose import jwt

def create_candidate_token(candidate_id: str) -> str:
    payload = {
        "sub": candidate_id,
        "type": "candidate",
        "exp": datetime.utcnow() + timedelta(hours=3)  # Exam time limit + buffer
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

# Validate on every request
def get_current_candidate(token: str = Depends(oauth2_scheme)) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != "candidate":
        raise HTTPException(401, "Invalid token type")
    return payload["sub"]  # candidate_id
```

**Admin Authentication (API Key):**

```python
# app/routers/items.py
def verify_admin_api_key(api_key: str = Header(..., alias="X-API-Key")):
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    # Look up in database (admin_users table, api_key_hash column)
    admin = db.query(AdminUser).filter_by(api_key_hash=hashed_key).first()
    if not admin:
        raise HTTPException(403, "Invalid API key")
    return admin
```

**Best practices:**

- ✅ Use HTTPS only (TLS 1.2+). Redirect HTTP → HTTPS at load balancer.
- ✅ Rotate JWT SECRET_KEY every 90 days (invalidates all tokens — schedule maintenance window).
- ✅ Rate limit: 100 requests/minute per IP for exam endpoints, 1000 req/min for admin (authenticated).
- ✅ SQL injection prevention: Always use parameterized queries (SQLAlchemy ORM handles this).
- ❌ Never log secrets (JWT tokens, API keys, database passwords).

### Exam Integrity

**Prevent cheating:**

1. **Item pool security:** Admin API requires API key. Item bank database exports are encrypted at rest.
2. **Session isolation:** Candidate A cannot see Candidate B's session (enforced by JWT candidate_id).
3. **No item review:** CAT is sequential only. Cannot skip ahead or go back (prevents answer key extraction).
4. **Randomized options:** (Future enhancement) Shuffle option order per candidate.
5. **Proctor integration:** (Future enhancement) Integrate with ProctorU / Examity for identity verification and screen monitoring.

**Anomaly detection:**

```sql
-- Flag sessions with suspiciously fast completion
SELECT session_id, candidate_id, items_administered,
       EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_sec
FROM exam_sessions
WHERE status = 'completed'
  AND EXTRACT(EPOCH FROM (completed_at - started_at)) < 300  -- < 5 minutes
ORDER BY duration_sec;

-- Flag candidates with multiple sessions same day (possible repeat attempts)
SELECT candidate_id, COUNT(*) as session_count, 
       ARRAY_AGG(session_id) as session_ids
FROM exam_sessions
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY candidate_id
HAVING COUNT(*) > 1;
```

### Data Privacy (GDPR / CCPA Compliance)

**Candidate data retention:**

- **Active sessions:** Retained indefinitely (audit trail for credential validity).
- **Abandoned sessions:** Purge after 90 days (never completed, no credential issued).
- **Personally Identifiable Information (PII):** `candidate.email` is the only PII. Hash or pseudonymize after credential issuance if required by policy.

**Right to erasure:**

```sql
-- Anonymize a candidate's data (if they request deletion)
UPDATE candidates
SET email = CONCAT('deleted-', id, '@example.com'),
    name = 'Deleted User'
WHERE id = '<candidate-id>';

-- DO NOT delete exam_sessions (they record certification history)
-- But remove PII link by setting candidate_id = NULL
UPDATE exam_sessions
SET candidate_id = NULL
WHERE candidate_id = '<candidate-id>';
```

**Encryption:**

- **At rest:** Database encryption (AWS RDS encryption, or PGCrypto extension).
- **In transit:** TLS 1.2+ for all API calls, PostgreSQL SSL connections.

---

## Backup and Disaster Recovery

### Backup Strategy

**Database backups (PostgreSQL):**

```bash
# Daily full backup (automated via cron)
0 2 * * * docker-compose exec -T postgres pg_dump -U cat_user -Fc cat_engine \
  > /backups/cat-engine-$(date +\%Y\%m\%d).dump

# Retention: 7 daily, 4 weekly, 12 monthly
# Delete backups older than 90 days
find /backups -name "*.dump" -mtime +90 -delete
```

**S3 replication (AWS):**

```bash
# Upload to S3 with versioning enabled
aws s3 cp /backups/cat-engine-$(date +%Y%m%d).dump \
  s3://cat-engine-backups/daily/
```

**Backup validation:**

```bash
# Monthly restore test to staging environment
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml up -d postgres
sleep 5

# Restore latest backup
docker-compose -f docker-compose.staging.yml exec -T postgres \
  pg_restore -U cat_user -d cat_engine_staging -c < /backups/latest.dump

# Run smoke test
docker-compose -f docker-compose.staging.yml run --rm app pytest tests/
```

### Disaster Recovery

**RTO (Recovery Time Objective): 1 hour**  
**RPO (Recovery Point Objective): 24 hours** (acceptable data loss = up to 1 day of exam sessions)

**Disaster scenarios:**

| Scenario | Recovery Procedure |
|----------|-------------------|
| **API server failure** | Load balancer automatically routes to healthy server (no manual action). If all servers down, restart via docker-compose. |
| **Database corruption** | Restore from latest backup (daily = max 24 hours data loss). Candidates who completed exams in past 24h may need to re-take (notify via email). |
| **Region-wide outage (AWS)** | Failover to DR region (manual). Requires: (1) S3 backup replication to DR region, (2) Restore database in DR region, (3) Update DNS to point to DR load balancer. Total time: ~1 hour. |
| **Ransomware / malicious deletion** | Restore from immutable S3 backup (versioning enabled). Backups are in separate AWS account (not accessible to application IAM role). |

**DR Drill (quarterly):**

1. Announce maintenance window (Friday 10pm PT)
2. Simulate region failure (shut down all production servers)
3. Restore database from backup to DR region
4. Start API servers in DR region
5. Run full test suite + smoke test
6. Measure time to recovery (target < 1 hour)
7. Document issues, update runbook

---

## Performance Tuning

### Database Optimization

**Indexes (already created via migrations):**

```sql
-- exam_sessions: lookup by session_id (primary key)
CREATE INDEX idx_sessions_candidate ON exam_sessions(candidate_id);
CREATE INDEX idx_sessions_status ON exam_sessions(status);
CREATE INDEX idx_sessions_completed ON exam_sessions(completed_at DESC) WHERE status = 'completed';

-- item_responses: join to sessions, filter by item
CREATE INDEX idx_responses_session ON item_responses(session_id);
CREATE INDEX idx_responses_item ON item_responses(item_id);

-- items: filter by status, domain, exposure
CREATE INDEX idx_items_status ON items(status) WHERE status IN ('pretest', 'active');
CREATE INDEX idx_items_domain ON items(domain_id);
```

**Query optimization:**

```sql
-- Bad: Loads all responses into application memory, computes theta in Python
SELECT * FROM item_responses WHERE session_id = '<id>';

-- Good: Let database do the work (if computing summary stats)
SELECT COUNT(*) as total, SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
FROM item_responses
WHERE session_id = '<id>';
```

**Connection pooling:**

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,        # Max 20 concurrent connections per API server
    max_overflow=10,     # Allow 10 more if pool exhausted (total 30)
    pool_timeout=30,     # Wait 30s for available connection, then error
    pool_pre_ping=True,  # Verify connection before use (detect stale)
)
```

**Slow query log:**

```sql
-- Enable in postgresql.conf
log_min_duration_statement = 100  # Log queries > 100ms

-- Analyze slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### API Performance

**Async I/O (already implemented):**

- All database calls use `await` (asyncpg driver)
- FastAPI + uvicorn (ASGI) supports 1000+ concurrent requests on 2 vCPU

**Response caching (for read-heavy endpoints):**

```python
# app/routers/items.py
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@router.get("/items")
@cache(expire=300)  # Cache for 5 minutes
async def list_items():
    # Expensive query (joins, aggregations)
    return db.query(Item).filter_by(status='active').all()
```

**Load testing:**

```bash
# Install Apache Bench
apt-get install apache2-utils

# Test: 1000 requests, 50 concurrent
ab -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" \
  https://exam-api.example.com/api/v1/exam/<session-id>/status

# Expected: All requests succeed, mean response time < 200ms
```

### Scaling Strategies

**Horizontal scaling (add more API servers):**

```bash
# Update docker-compose.yml
services:
  app:
    deploy:
      replicas: 4  # Was 2, now 4
```

**Database read replicas (if read-heavy):**

```python
# app/database.py
read_engine = create_async_engine(settings.DATABASE_READ_URL)  # Replica
write_engine = create_async_engine(settings.DATABASE_URL)      # Primary

# Use read_engine for GET endpoints, write_engine for POST/PUT/DELETE
```

**Caching layer (Redis):**

```bash
# For hot data (active exam config, frequently-selected items)
docker-compose.yml:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

# app/main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis:6379", encoding="utf8")
    FastAPICache.init(RedisBackend(redis), prefix="cat-engine")
```

---

## Troubleshooting

### Common Issues

**1. "Database connection refused"**

**Symptoms:** API returns 500 error, logs show `asyncpg.exceptions.ConnectionRefusedError`

**Diagnosis:**
```bash
# Check if postgres is running
docker-compose ps postgres

# Check connection from API container
docker-compose exec app ping postgres
docker-compose exec app nc -zv postgres 5432
```

**Fix:**
- If postgres is down: `docker-compose up -d postgres`
- If connection refused: check `CAT_DATABASE_URL` (wrong host/port)
- If auth failure: check postgres credentials in `.env`

**2. "Item pool exhausted"**

**Symptoms:** API returns 500, logs show `No eligible items available for selection`

**Diagnosis:**
```sql
-- Check how many active items exist
SELECT COUNT(*) FROM items WHERE status = 'active';

-- Check how many are eligibile (not yet administered to this candidate)
SELECT COUNT(*) FROM items
WHERE status = 'active'
  AND id NOT IN (
    SELECT item_id FROM item_responses WHERE session_id = '<session-id>'
  );
```

**Fix:**
- If < 40 active items: Promote pretest items to active (see Item Lifecycle section)
- If Sympson-Hetter gating too aggressive: Increase k-values

**3. "SPRT oscillation (session reaches 40 items without crossing boundary)"**

**Symptoms:** Many sessions reach ceiling (40 items) with final theta near cut score (±0.3)

**Diagnosis:**
```sql
-- Count sessions at ceiling
SELECT COUNT(*) FROM exam_sessions
WHERE items_administered = 40
  AND ABS(final_theta - 0.0) < 0.5;
```

**Expected:** 10-15% of sessions reach ceiling (borderline candidates)  
**Problem:** > 30% reach ceiling (indifference region too wide, or items poorly discriminating)

**Fix:**
- Reduce indifference region: `CAT_DELTA=0.15` (from 0.2)
- Review item pool: Ensure mix of difficulties (not all clustered around b=0)
- Check discrimination: If many items have a < 0.8, replace with higher-discrimination items

**4. "Pass rate too high (> 80%)"**

**Symptoms:** Dashboard shows 85% of candidates pass

**Diagnosis:**
```sql
SELECT decision, COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM exam_sessions
WHERE status = 'completed'
  AND completed_at > NOW() - INTERVAL '30 days'
GROUP BY decision;
```

**Root causes:**
- Cut score θ_c too low (too easy to pass)
- Item pool too easy (too many items with b < -0.5)
- Candidate population shifted (higher ability than expected)

**Fix:**
- Convene SME panel for Modified Angoff review → adjust θ_c upward (e.g., from 0.0 to 0.2)
- Add harder items (b > 0.5) to pool
- Review prerequisite requirements (maybe need to tighten prerequisites)

**5. "High abandonment rate (> 10%)"**

**Symptoms:** Many sessions started but not completed

**Diagnosis:**
```sql
SELECT status, COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM exam_sessions
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY status;
```

**Root causes:**
- Technical issues (slow API, connection drops)
- Proctoring problems (candidate fails ID verification)
- Time limit too short (candidate runs out of time)
- Items too hard (candidate gets discouraged)

**Fix:**
- Check API response times (p95 should be < 500ms)
- Review proctor logs (if integrated)
- Extend time limit if many sessions timeout (currently 120 min)
- Review first-5-item pass rate (if many candidates fail early, items may be too hard)

---

## Incident Response

### Severity Levels

| Level | Definition | Response Time | Example |
|-------|------------|---------------|---------|
| **SEV-1 (Critical)** | Complete outage, all candidates cannot access exam | < 15 minutes | Database down, API crashes on startup |
| **SEV-2 (High)** | Partial outage, some candidates affected | < 1 hour | Item selection fails for Domain 3, 503 errors for 10% of requests |
| **SEV-3 (Medium)** | Degraded performance, workaround available | < 4 hours | Slow response times (p95 > 2 seconds), single API server down (load balancer routes to backup) |
| **SEV-4 (Low)** | Cosmetic issue, no functional impact | Next business day | Typo in item text, dashboard chart not loading |

### Incident Workflow

**1. Detect**

- Monitoring alert fires (PagerDuty / OpsGenie)
- User report via support channel

**2. Assess**

- Check dashboard: How many candidates affected?
- Check logs: What error is occurring?
- Assign severity level

**3. Notify**

- SEV-1: Page on-call engineer + manager + stakeholder (certification director)
- SEV-2: Page on-call engineer, Slack alert to #cat-engine-alerts
- SEV-3: Slack alert only

**4. Mitigate**

- SEV-1: Immediate mitigation (restart services, failover to DR, enable maintenance mode)
- SEV-2: Investigate root cause, deploy hotfix if available
- SEV-3: Schedule fix for next deployment

**5. Resolve**

- Deploy fix
- Verify resolution (run smoke tests)
- Update status page / notify affected candidates

**6. Post-mortem (for SEV-1 and SEV-2)**

- What happened? (timeline, root cause)
- What was the impact? (# candidates affected, duration)
- Why did it happen? (what defenses failed?)
- How do we prevent recurrence? (action items with owners and deadlines)

**Example post-mortem template:**

```markdown
# Incident Report: Database Connection Pool Exhausted

**Date:** 2026-07-15  
**Severity:** SEV-2  
**Duration:** 45 minutes (10:15 AM - 11:00 AM PT)  
**Impact:** 37 candidates unable to start new exam sessions (received 500 error)

## Timeline

10:15 AM: Monitoring alert fires: "Connection pool exhausted"  
10:17 AM: On-call engineer investigates, sees 30 connections in use (pool_size=20)  
10:25 AM: Root cause identified: Long-running query on item_responses table (no limit clause)  
10:30 AM: Hotfix deployed: Add LIMIT 1000 to query  
10:35 AM: Connection pool recovers, new sessions succeed  
11:00 AM: All affected candidates contacted, offered free re-take  

## Root Cause

The `/api/v1/admin/analytics/items` endpoint was added in v1.4.0 without a LIMIT clause.
When an admin requested "all item responses" for analysis, the query scanned 500K rows,
holding a database connection for 120+ seconds. 3 concurrent admin requests exhausted
the pool (20 connections), blocking all candidate exam sessions.

## Prevention

- [ ] Add LIMIT clause to all admin analytics queries (max 10K rows) — Owner: Alice, Due: 2026-07-20  
- [ ] Implement query timeout (30s max) at database level — Owner: Bob, Due: 2026-07-25  
- [ ] Separate connection pool for admin endpoints (5 connections) vs. candidate endpoints (15) — Owner: Alice, Due: 2026-08-01  
- [ ] Add integration test: "Admin query does not block candidate exam start" — Owner: Charlie, Due: 2026-07-22  
```

---

## Routine Maintenance

### Daily

- [ ] Check monitoring dashboard (uptime, error rate, session count)
- [ ] Review log aggregator for ERROR/CRITICAL entries
- [ ] Verify backup completed successfully (check S3 upload)

### Weekly

- [ ] Review test length distribution (avg should be ~14 ± 3)
- [ ] Review pass rate (should be 60-70%)
- [ ] Check item exposure (no item > 30%)
- [ ] Review pretest item calibration queue (promote items with ≥ 200 responses)

### Monthly

- [ ] Rotate admin API keys (generate new, update client systems, revoke old)
- [ ] Review security logs (failed auth attempts, suspicious IP patterns)
- [ ] Database maintenance (VACUUM, ANALYZE, index rebuild)
- [ ] Restore test from backup (verify DR procedure)

### Quarterly

- [ ] Disaster recovery drill (simulate region outage, measure RTO)
- [ ] Item exposure rebalancing (recalculate Sympson-Hetter k-values)
- [ ] Content review (retire outdated items, add new items for curriculum updates)
- [ ] Capacity planning (review growth trend, scale infrastructure if needed)

### Annually

- [ ] Cut score validation (Modified Angoff with SME panel)
- [ ] Blueprint alignment review (verify domain weights match current JTA)
- [ ] Security audit (penetration testing, dependency vulnerability scan)
- [ ] Equity audit (check for differential item functioning by subgroup)

---

## Appendix: Runbooks

### Runbook: Emergency Maintenance Mode

**When to use:** SEV-1 incident requiring immediate mitigation (all candidates locked out while fixing)

**Steps:**

```bash
# 1. Enable maintenance mode (return 503 for all exam endpoints)
curl -X POST https://exam-api.example.com/api/v1/admin/maintenance \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"enabled": true, "message": "System maintenance in progress. Exams will resume at 11:00 AM PT."}'

# 2. Update status page
echo "CAT Engine is undergoing emergency maintenance. ETA: 30 minutes" \
  | aws sns publish --topic-arn arn:aws:sns:us-east-1:123456:status-page

# 3. Fix the issue (restore database, deploy hotfix, etc.)

# 4. Smoke test
curl -X POST https://exam-api.example.com/api/v1/exam/start \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"candidate_id": "test-001", "email": "test@example.com"}'

# 5. Disable maintenance mode
curl -X POST https://exam-api.example.com/api/v1/admin/maintenance \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"enabled": false}'
```

### Runbook: Database Restore

**When to use:** Database corruption, data loss, DR failover

**Steps:**

```bash
# 1. Stop API servers (prevent writes during restore)
docker-compose stop app

# 2. Backup current database (even if corrupted — for forensics)
docker-compose exec postgres pg_dump -U cat_user -Fc cat_engine \
  > /backups/pre-restore-$(date +%Y%m%d-%H%M%S).dump

# 3. Drop and recreate database
docker-compose exec postgres psql -U cat_user -d postgres \
  -c "DROP DATABASE cat_engine;" \
  -c "CREATE DATABASE cat_engine;"

# 4. Restore from backup
docker-compose exec -T postgres pg_restore -U cat_user -d cat_engine \
  < /backups/cat-engine-20260724.dump

# 5. Run migrations (in case backup was from older schema)
docker-compose run --rm app alembic upgrade head

# 6. Start API servers
docker-compose up -d app

# 7. Smoke test
curl https://exam-api.example.com/health
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-24  
**Maintained By:** CAT Engine Operations Team
