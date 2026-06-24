# CAT Engine Development Guide

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Architecture](#project-architecture)
3. [Code Style and Standards](#code-style-and-standards)
4. [Testing Strategy](#testing-strategy)
5. [Adding New Features](#adding-new-features)
6. [IRT Model Extensions](#irt-model-extensions)
7. [Database Migrations](#database-migrations)
8. [API Design Patterns](#api-design-patterns)
9. [Performance Profiling](#performance-profiling)
10. [Contributing Guidelines](#contributing-guidelines)

---

## Development Setup

### Prerequisites

- **Python 3.10+** (for `X | None` type hints)
- **PostgreSQL 16+** (or Docker for local development)
- **Git** for version control
- **Code editor** with Python LSP (VS Code, PyCharm, or vim + coc.nvim)

### Local Environment

**1. Clone and create virtual environment:**

```bash
git clone https://github.com/your-org/cat-engine.git
cd cat-engine

python3.13 -m venv venv  # Or python3.10+
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**2. Install dependencies:**

```bash
# Core dependencies
pip install --upgrade pip
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings python-jose passlib \
    numpy scipy pyyaml

# Development dependencies
pip install pytest pytest-asyncio pytest-cov httpx \
    black isort mypy ruff ipython
```

Or use `pyproject.toml`:

```bash
pip install -e ".[dev]"  # Installs package + dev dependencies
```

**3. Start local database:**

```bash
docker-compose up -d postgres

# Wait for postgres to be ready
sleep 5

# Verify connection
docker-compose exec postgres psql -U cat_user -d cat_engine -c "\dt"
```

**4. Run migrations:**

```bash
alembic upgrade head
```

**5. Seed items:**

```bash
python scripts/seed_items.py
```

**6. Start dev server:**

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**7. Verify:**

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","database":"connected",...}
```

### IDE Configuration

**VS Code (`.vscode/settings.json`):**

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.rulers": [88]  // Black line length
  }
}
```

**PyCharm:**

- Settings → Tools → Black → Enable "On save"
- Settings → Tools → External Tools → Add mypy
- Settings → Editor → Code Style → Python → Set line length to 88

---

## Project Architecture

### Layered Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ Presentation Layer (routers/)                                  │
│  • HTTP request/response handling                              │
│  • Input validation (Pydantic schemas)                         │
│  • Authentication/authorization                                │
│  • Serialization (SQLAlchemy models → Pydantic schemas)        │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│ Business Logic Layer (services/)                               │
│  • Orchestration (cat_engine.py)                               │
│  • Domain logic (item selection, stopping rules)               │
│  • Stateless functions (no database access in this layer)      │
│  • Delegates to IRT module for math                            │
└─────────┬──────────────────────────────────────────────────────┘
          │
          ├───────────────────────────────────────┐
          ▼                                       ▼
┌─────────────────────────┐      ┌────────────────────────────────┐
│ IRT Math (irt/)         │      │ Data Layer (models/)           │
│  • Pure functions       │      │  • SQLAlchemy ORM models       │
│  • No side effects      │      │  • Database schema definition  │
│  • No database          │      │  • Relationships               │
│  • Framework-agnostic   │      └────────────────────────────────┘
└─────────────────────────┘
```

### Dependency Flow

```
routers/exam.py
  → services/cat_engine.py
      → services/item_selection.py → irt/models.py (fisher_information)
      → services/stopping_rule.py → irt/sprt.py (sprt_update)
      → irt/estimation.py (estimate_theta_eap)
  → models/exam_session.py (database I/O)
```

**Key principle:** Lower layers have NO knowledge of upper layers.

- ✅ `irt/models.py` does not import anything from `services/` or `routers/`
- ✅ `services/cat_engine.py` does not import from `routers/`
- ❌ Never import `routers/` from `services/` (circular dependency)

### Why This Architecture?

1. **Testability:** `irt/` is pure math → test with synthetic data, no database mocks
2. **Reusability:** `irt/` functions used in API, Monte Carlo simulation, offline calibration
3. **Separation of concerns:** HTTP details (headers, status codes) are isolated in `routers/`
4. **Maintainability:** Change database schema (models/) without touching business logic (services/)

---

## Code Style and Standards

### Formatting

**Black (code formatter):**

```bash
# Format all Python files
black app/ tests/ scripts/

# Check without modifying
black --check app/
```

**isort (import sorting):**

```bash
# Sort imports
isort app/ tests/ scripts/

# Check without modifying
isort --check app/
```

**Configuration (pyproject.toml):**

```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["app"]
```

### Type Checking

**mypy (static type checker):**

```bash
mypy app/
```

**Configuration (pyproject.toml):**

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # All functions must have type hints
ignore_missing_imports = true  # For libraries without stubs
```

**Example type-annotated function:**

```python
def estimate_theta_eap(
    responses: list[tuple[float, float, bool]],
    prior_mean: float = 0.0,
    prior_sd: float = 1.0,
    n_quadrature: int = 49,
    theta_range: tuple[float, float] = (-4.0, 4.0)
) -> tuple[float, float]:
    """
    Estimate ability using Expected A Posteriori (EAP).
    
    Args:
        responses: List of (a, b, is_correct) tuples
        prior_mean: Prior distribution mean
        prior_sd: Prior distribution standard deviation
        n_quadrature: Number of quadrature points
        theta_range: (min, max) ability range
    
    Returns:
        (theta_hat, posterior_sd): Ability estimate and standard error
    """
    ...
```

### Linting

**ruff (fast Python linter):**

```bash
ruff check app/ tests/ scripts/
```

**Configuration (pyproject.toml):**

```toml
[tool.ruff]
line-length = 88
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]
```

### Docstrings

**Use Google-style docstrings:**

```python
def fisher_information(theta: float, a: float, b: float) -> float:
    """
    Calculate Fisher Information for a 2PL item at a given ability level.

    Fisher Information quantifies how much an item tells us about a candidate's
    ability. It is maximized when theta equals the item's difficulty (b).

    Args:
        theta: Candidate ability on the logit scale (typically -4 to +4).
        a: Item discrimination parameter (typically 0.5 to 2.5).
        b: Item difficulty parameter (typically -3 to +3).

    Returns:
        Fisher Information value (always non-negative).

    Examples:
        >>> fisher_information(0.0, 1.0, 0.0)
        0.25  # Maximum info when theta = b

        >>> fisher_information(2.0, 1.0, 0.0)
        0.10  # Less info when theta >> b
    """
    p = probability_2pl(theta, a, b)
    q = 1.0 - p
    return (a ** 2) * p * q
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| **Variables** | snake_case | `theta_hat`, `cumulative_lr` |
| **Functions** | snake_case | `estimate_theta_eap()`, `select_next_item()` |
| **Classes** | PascalCase | `ExamSession`, `ItemCandidate` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_ITEMS`, `WALD_UPPER_BOUNDARY` |
| **Private** | _leading_underscore | `_compute_likelihood()` (internal helper) |
| **Pydantic schemas** | PascalCase + suffix | `ExamStartRequest`, `ItemResponse` |
| **SQLAlchemy models** | PascalCase | `ExamSession`, `Item` |

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── test_irt/
│   ├── test_2pl.py              # 2PL model tests (18 tests)
│   ├── test_estimation.py       # EAP/MLE tests (12 tests)
│   └── test_sprt.py             # SPRT tests (16 tests)
├── test_services/
│   └── test_cat_engine.py       # Integration tests for CAT orchestrator
└── test_routers/
    └── test_exam.py             # API endpoint tests (not yet implemented)
```

### Unit Tests (Pure Functions)

**Example: Testing 2PL probability**

```python
# tests/test_irt/test_2pl.py
import pytest
from app.irt.models import probability_2pl

class TestProbability2PL:
    def test_at_difficulty_equals_fifty_percent(self):
        """When theta = b, probability should be 0.5 regardless of discrimination."""
        assert probability_2pl(theta=1.0, a=1.0, b=1.0) == pytest.approx(0.5)
        assert probability_2pl(theta=0.0, a=2.0, b=0.0) == pytest.approx(0.5)
        assert probability_2pl(theta=-1.5, a=0.5, b=-1.5) == pytest.approx(0.5)

    def test_above_difficulty_greater_than_fifty(self):
        """When theta > b, probability should exceed 0.5."""
        p = probability_2pl(theta=1.0, a=1.0, b=0.0)
        assert p > 0.5

    def test_extreme_theta_does_not_overflow(self):
        """Very large/small theta should not cause overflow."""
        p_high = probability_2pl(theta=100.0, a=3.0, b=0.0)
        p_low = probability_2pl(theta=-100.0, a=3.0, b=0.0)
        assert p_high == pytest.approx(1.0, abs=1e-6)
        assert p_low == pytest.approx(0.0, abs=1e-6)
```

**Run unit tests:**

```bash
pytest tests/test_irt/ -v
```

### Integration Tests (CAT Engine)

**Example: Testing process_response**

```python
# tests/test_services/test_cat_engine.py
from app.services.cat_engine import EngineState, process_response, SessionConfig

def test_correct_response_increases_theta(sample_items, default_config):
    state = EngineState.new_session(default_config)
    item = sample_items[20]  # Middle difficulty

    result = process_response(
        state=state,
        item=item,
        response_index=0,
        correct_index=0,  # Correct
        eligible_items=sample_items,
    )

    assert result.is_correct is True
    assert result.new_theta > default_config.starting_theta
```

**Run integration tests:**

```bash
pytest tests/test_services/ -v
```

### API Tests (E2E)

**Example: Testing exam start endpoint**

```python
# tests/test_routers/test_exam.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_start_exam():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/exam/start",
            json={"candidate_id": "test-001", "email": "test@example.com"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "item" in data
    assert data["item"]["sequence_number"] == 1
```

**Run API tests:**

```bash
pytest tests/test_routers/ -v
```

### Test Coverage

```bash
# Run all tests with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

**Coverage targets:**

- `irt/`: 100% (pure math, easy to test)
- `services/`: 90%+ (business logic, critical path)
- `routers/`: 80%+ (I/O layer, some edge cases may be integration-tested only)

### Fixtures (Shared Test Data)

```python
# tests/conftest.py
import pytest
from app.services.item_selection import ItemCandidate

@pytest.fixture
def sample_items():
    """A small item bank for testing."""
    return [
        ItemCandidate(
            item_id=f"item-{i:03d}",
            domain_id=(i % 8) + 1,
            discrimination=1.0 + (i % 5) * 0.2,
            difficulty=-2.0 + i * 0.2,
            sympson_hetter_k=1.0,
        )
        for i in range(40)
    ]

@pytest.fixture
def default_config():
    """Default session configuration for testing."""
    from app.services.cat_engine import SessionConfig

    return SessionConfig(
        theta_c=0.0,
        delta=0.2,
        alpha=0.05,
        beta=0.05,
        max_items=40,
        min_items=5,
        w_info=0.7,
        w_content=0.3,
        starting_theta=0.0,
        domain_weights={
            "1": 0.15, "2": 0.12, "3": 0.20, "4": 0.15,
            "5": 0.12, "6": 0.10, "7": 0.10, "8": 0.06,
        },
        max_exposure_rate=0.25,
        time_limit_minutes=120,
    )
```

---

## Adding New Features

### Example: Add Confidence Interval to Session Status Response

**1. Define requirement:**

> "When a candidate queries their session status, return a 95% confidence interval for their ability estimate (not just the point estimate θ̂)."

**2. Update business logic (services/):**

```python
# app/services/cat_engine.py
from scipy.stats import norm

def compute_confidence_interval(
    theta: float,
    theta_se: float,
    confidence_level: float = 0.95
) -> tuple[float, float]:
    """
    Compute confidence interval for ability estimate.
    
    Args:
        theta: Ability point estimate
        theta_se: Standard error of theta
        confidence_level: Confidence level (0.95 = 95%)
    
    Returns:
        (lower_bound, upper_bound)
    """
    z = norm.ppf((1 + confidence_level) / 2)  # 1.96 for 95%
    margin = z * theta_se
    return (theta - margin, theta + margin)
```

**3. Update Pydantic schema (schemas/):**

```python
# app/schemas/exam.py
class ExamStatusResponse(BaseModel):
    session_id: str
    status: str
    decision: str | None
    final_theta: float | None
    theta_se: float | None
    theta_ci_lower: float | None  # NEW
    theta_ci_upper: float | None  # NEW
    items_administered: int
    completed_at: str | None
```

**4. Update router (routers/):**

```python
# app/routers/exam.py
from app.services.cat_engine import compute_confidence_interval

@router.get("/{session_id}/status")
async def get_exam_status(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Compute CI if session is completed
    ci_lower, ci_upper = None, None
    if session.status == "completed" and session.theta_se is not None:
        ci_lower, ci_upper = compute_confidence_interval(
            session.final_theta, session.theta_se
        )
    
    return ExamStatusResponse(
        session_id=session.id,
        status=session.status,
        decision=session.decision,
        final_theta=session.final_theta,
        theta_se=session.theta_se,
        theta_ci_lower=ci_lower,
        theta_ci_upper=ci_upper,
        items_administered=session.items_administered,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )
```

**5. Write test:**

```python
# tests/test_services/test_cat_engine.py
def test_compute_confidence_interval():
    from app.services.cat_engine import compute_confidence_interval
    
    # theta = 0.0, SE = 0.5 → 95% CI = [-0.98, +0.98]
    lower, upper = compute_confidence_interval(0.0, 0.5)
    assert lower == pytest.approx(-0.98, abs=0.01)
    assert upper == pytest.approx(0.98, abs=0.01)
```

**6. Run tests:**

```bash
pytest tests/test_services/test_cat_engine.py::test_compute_confidence_interval -v
```

**7. Document:**

Update `docs/DESIGN.md` → Ability Estimation section with CI formula.

---

## IRT Model Extensions

### Adding 3-Parameter Logistic (3PL) Model

The 3PL adds a **guessing parameter c** (pseudo-chance level):

```
P(θ, a, b, c) = c + (1 - c) / (1 + exp(-a * (θ - b)))
```

**1. Add to `app/irt/models.py`:**

```python
def probability_3pl(theta: float, a: float, b: float, c: float) -> float:
    """
    3PL item response probability.
    
    Args:
        theta: Ability
        a: Discrimination
        b: Difficulty
        c: Guessing parameter (0.0 to 0.5, typically ~0.20 for 4-option MC)
    
    Returns:
        Probability of correct response
    """
    if not (0.0 <= c < 1.0):
        raise ValueError(f"Guessing parameter c must be in [0, 1), got {c}")
    
    exponent = a * (theta - b)
    exponent = max(-30.0, min(30.0, exponent))  # Prevent overflow
    return c + (1 - c) / (1 + math.exp(-exponent))


def fisher_information_3pl(theta: float, a: float, b: float, c: float) -> float:
    """
    Fisher Information for 3PL model.
    
    Formula: I = [a² (1-c)² P_star² Q] / [P² (1-P)]
    Where:
      P_star = 1 / (1 + exp(-a(θ-b)))  # 2PL probability
      P = c + (1-c) P_star              # 3PL probability
      Q = 1 - P_star
    """
    p_star = 1.0 / (1.0 + math.exp(-a * (theta - b)))
    q_star = 1.0 - p_star
    p = c + (1 - c) * p_star
    
    if p <= 0.0 or p >= 1.0:
        return 0.0
    
    numerator = (a ** 2) * ((1 - c) ** 2) * (p_star ** 2) * q_star
    denominator = (p ** 2) * (1 - p)
    return numerator / denominator
```

**2. Add database column:**

```python
# alembic/versions/xxx_add_3pl_guessing.py
def upgrade():
    op.add_column('items', sa.Column('guessing', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('items', 'guessing')
```

**3. Update item selection:**

```python
# app/services/item_selection.py
def select_next_item(state: EngineState, eligible_items: list[ItemCandidate]) -> ItemCandidate:
    # ...
    for item in eligible_items:
        if item.guessing is not None:
            info = fisher_information_3pl(state.theta, item.a, item.b, item.guessing)
        else:
            info = fisher_information(state.theta, item.a, item.b)  # 2PL fallback
        # ...
```

**4. Write tests:**

```python
# tests/test_irt/test_3pl.py
def test_3pl_reduces_to_2pl_when_c_is_zero():
    """When c=0, 3PL should equal 2PL."""
    theta, a, b = 0.5, 1.2, 0.0
    p_2pl = probability_2pl(theta, a, b)
    p_3pl = probability_3pl(theta, a, b, c=0.0)
    assert p_2pl == pytest.approx(p_3pl)

def test_3pl_lower_asymptote_at_c():
    """As theta → -∞, P(θ) → c (guessing floor)."""
    p = probability_3pl(theta=-10.0, a=1.0, b=0.0, c=0.25)
    assert p == pytest.approx(0.25, abs=0.01)
```

---

## Database Migrations

### Creating a Migration

**1. Make schema changes in `app/models/`:**

```python
# app/models/item.py
class Item(Base):
    __tablename__ = "items"
    
    # NEW COLUMN
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
```

**2. Generate migration:**

```bash
alembic revision --autogenerate -m "Add tags column to items"
```

This creates `alembic/versions/xxx_add_tags_column_to_items.py`.

**3. Review migration:**

```python
# alembic/versions/xxx_add_tags_column_to_items.py
def upgrade():
    op.add_column('items', sa.Column('tags', sa.ARRAY(sa.String()), nullable=True))

def downgrade():
    op.drop_column('items', 'tags')
```

**4. Apply migration:**

```bash
alembic upgrade head
```

**5. Verify:**

```bash
docker-compose exec postgres psql -U cat_user -d cat_engine \
  -c "\d items"  # Show table schema
```

### Migration Best Practices

- ✅ **Always test rollback:** Run `alembic downgrade -1` to verify downgrade works
- ✅ **Add indexes in separate migration:** Large tables lock during index creation
- ✅ **Set default values for new NOT NULL columns:** `server_default='[]'` prevents breaking existing rows
- ❌ **Never edit applied migrations:** Create a new migration to fix mistakes
- ❌ **Don't mix schema changes and data migrations:** Separate them for clarity

**Example: Data migration (populate tags from objective_id):**

```python
# alembic/versions/xxx_populate_item_tags.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    connection = op.get_bind()
    
    # Fetch items and derive tags from objective_id
    items = connection.execute(sa.text("SELECT id, objective_id FROM items")).fetchall()
    for item_id, objective_id in items:
        domain = objective_id.split('.')[0]  # "1.2" → "1"
        tags = [f"domain-{domain}", objective_id]
        connection.execute(
            sa.text("UPDATE items SET tags = :tags WHERE id = :id"),
            {"tags": tags, "id": item_id}
        )

def downgrade():
    op.execute("UPDATE items SET tags = NULL")
```

---

## API Design Patterns

### Request/Response Schemas

**Always use Pydantic for validation:**

```python
# app/schemas/exam.py
from pydantic import BaseModel, Field, validator

class ExamStartRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    
    @validator('candidate_id')
    def validate_candidate_id(cls, v):
        if v.startswith('test-') and not settings.DEBUG:
            raise ValueError('Test candidates only allowed in development')
        return v

class ExamStartResponse(BaseModel):
    session_id: str
    item: ItemPresentation
    
    class Config:
        # Allow SQLAlchemy models to be converted
        orm_mode = True
```

### Error Handling

**Use HTTPException for client errors:**

```python
from fastapi import HTTPException

@router.post("/{session_id}/respond")
async def respond_to_item(session_id: str, ...):
    session = await db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(404, detail="Session not found")
    
    if session.status == "completed":
        raise HTTPException(400, detail="Session already completed")
    
    # Validate response_index
    if response.response_index >= len(item.options):
        raise HTTPException(400, detail="Invalid response index")
```

**Use try/except for unexpected errors:**

```python
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

try:
    result = process_response(state, item, ...)
except ValueError as e:
    logger.error(f"Invalid input: {e}", exc_info=True)
    raise HTTPException(400, detail=str(e))
except Exception as e:
    logger.exception("Unexpected error in process_response")
    raise HTTPException(500, detail="Internal server error")
```

### Dependency Injection

**Database session:**

```python
# app/dependencies.py
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

# Usage
@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    items = await db.execute(select(Item).filter_by(status='active'))
    return items.scalars().all()
```

**Current user:**

```python
# app/dependencies.py
async def get_current_candidate(token: str = Depends(oauth2_scheme)) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return payload["sub"]  # candidate_id

# Usage
@router.get("/{session_id}/status")
async def get_status(
    session_id: str,
    candidate_id: str = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db)
):
    session = await db.get(ExamSession, session_id)
    if session.candidate_id != candidate_id:
        raise HTTPException(403, "Not your session")
    return session
```

---

## Performance Profiling

### CPU Profiling

```python
# scripts/profile_cat.py
import cProfile
import pstats
from app.services.cat_engine import process_response

def run_100_responses():
    state = EngineState.new_session(config)
    for i in range(100):
        item = sample_items[i % len(sample_items)]
        result = process_response(state, item, ...)

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    run_100_responses()
    profiler.disable()
    
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions by cumulative time
```

**Expected hotspots:**

- `estimate_theta_eap()`: ~30% of time (Gaussian quadrature)
- `fisher_information()`: ~20% of time (called for every eligible item)
- Database I/O: ~15% of time

### Memory Profiling

```bash
pip install memory_profiler

# Add @profile decorator to functions
from memory_profiler import profile

@profile
def estimate_theta_eap(...):
    ...

# Run with memory profiling
python -m memory_profiler scripts/profile_cat.py
```

### Query Profiling

**Log slow queries:**

```python
# app/database.py
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

**Use EXPLAIN:**

```sql
EXPLAIN ANALYZE
SELECT * FROM items
WHERE status = 'active'
  AND domain_id = 3
ORDER BY exposure_count
LIMIT 10;
```

---

## Contributing Guidelines

### Git Workflow

**1. Create feature branch:**

```bash
git checkout -b feature/add-3pl-model
```

**2. Make changes, commit often:**

```bash
git add app/irt/models.py tests/test_irt/test_3pl.py
git commit -m "Add 3PL probability function and tests"
```

**3. Push and create PR:**

```bash
git push origin feature/add-3pl-model
# Create PR on GitHub
```

**4. Address review feedback:**

```bash
# Make changes
git add .
git commit -m "Address review: add edge case tests"
git push
```

**5. Merge (squash commits):**

```bash
# On GitHub: "Squash and merge"
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding tests
- `refactor`: Code refactoring (no behavior change)
- `perf`: Performance improvement
- `chore`: Build/tooling changes

**Example:**

```
feat(irt): Add 3PL model with guessing parameter

- Implement probability_3pl() and fisher_information_3pl()
- Add database column for guessing parameter
- Update item selection to use 3PL when available
- Add 12 unit tests for 3PL edge cases

Closes #42
```

### PR Checklist

- [ ] Code follows style guide (black, isort, mypy pass)
- [ ] All tests pass (`pytest`)
- [ ] New features have tests (coverage ≥ 80%)
- [ ] Documentation updated (docstrings + relevant .md files)
- [ ] Migration tested (upgrade + downgrade)
- [ ] No secrets committed (.env files in .gitignore)

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-24  
**Maintained By:** CAT Engine Development Team
