# Testing Guide

## 1. Test Architecture

The backend test suite lives in `backend/tests/` and is organized by layer:

```
backend/tests/
  conftest.py                      # Global test infrastructure
  utils.py                         # MockLLMClient, factories, helpers
  test_health.py                   # Health endpoint
  test_integration.py              # Full vertical-slice integration tests (requires DB)
  test_api/
    test_auth.py                   # Auth middleware (dev bypass, pipeline key)
  test_conversation/
    test_prompt_builder.py         # System prompt construction (constitution, persona, constraints)
    test_tool_executor.py          # Tool dispatch, risk-tier enforcement
    test_safety.py                 # Canary token detection (11 tests)
    test_exploitation.py           # Financial exploitation indicator detection (10 tests)
    test_integrity.py              # Conversation integrity monitoring (9 tests)
  test_pipeline/
    test_classification.py         # Tier 1 rule-based classifier
  test_services/
    test_todo_service.py           # Todo create/complete, bill side-effects
    test_push_notification.py      # Push notification dispatch
```

**Total: 57 unit tests + 23 integration tests = 80 tests**

**Unit tests** (`test_conversation/`, `test_pipeline/`, `test_services/`, `test_api/`) test individual functions with a real database session that rolls back after each test. No HTTP requests are involved.

**Integration tests** (`test_integration.py`) boot the full FastAPI app via `httpx.ASGITransport` and exercise real HTTP endpoints. They verify the vertical slice: health checks, CRUD for medications/bills/todos/appointments, section aggregates, document pipeline, notifications, conversation lifecycle, contacts, and integrations.

**Mobile tests** (`companion-app/__tests__/App.test.tsx`) use React Test Renderer via Jest. Currently a single smoke test that renders the root `<App />` component.

## 2. Running Tests Locally

### Prerequisites

- Python 3.12+
- PostgreSQL 16 and Redis 7 running locally (easiest via Docker Compose)
- Backend dev dependencies installed

### Database setup

```bash
# Start services
docker compose up -d postgres redis

# Create the test database
psql -h localhost -U companion -d postgres \
  -c "DROP DATABASE IF EXISTS companion_test;" \
  -c "CREATE DATABASE companion_test;"

# Run migrations
cd backend
export COMPANION_DATABASE_URL=postgresql+asyncpg://companion:test@localhost:5432/companion_test
export COMPANION_REDIS_URL=redis://localhost:6379/0
alembic upgrade head
```

### Run backend tests

```bash
cd backend
pip install -e ".[dev]"

export COMPANION_DATABASE_URL=postgresql+asyncpg://companion:test@localhost:5432/companion_test
export COMPANION_REDIS_URL=redis://localhost:6379/0
export COMPANION_ENVIRONMENT=test
export COMPANION_DEV_AUTH_BYPASS=true

pytest -v
```

### Run mobile tests

```bash
cd companion-app
npm install
npm test
```

## 3. Test Infrastructure

### conftest.py

Replaces the production database engine with a `NullPool` engine to avoid asyncpg event-loop conflicts with httpx's `ASGITransport`. It also ensures a test user (`test@companion.app`) exists in the database before any tests run. This user is resolved automatically by the dev-mode auth bypass.

Key exports used by test files:
- `_test_engine` -- NullPool async engine
- `_test_session_factory` -- async session maker bound to the test engine

### MockLLMClient

Defined in `tests/utils.py`. A deterministic replacement for the real LLM client:

```python
client = MockLLMClient(response='{"classification": "bill"}')
# or with dynamic responses:
client = MockLLMClient(response_fn=lambda system, msgs: "dynamic reply")
```

- Records all calls in `client.calls` for assertions
- Supports both `generate()` and `generate_stream()`
- Default response returns a bill classification with 0.9 confidence

### Factories

`tests/utils.py` provides factory functions that build model instances without persisting them:

| Factory | Model | Defaults |
|---------|-------|----------|
| `make_user()` | User | email=test@companion.app, language=en |
| `make_medication(user_id)` | Medication | Lisinopril 10mg daily |
| `make_bill(user_id)` | Bill | Electric Co $120, today, pending |
| `make_todo(user_id)` | Todo | "Buy groceries", general, user source |
| `make_appointment(user_id)` | Appointment | Dr. Smith, 2026-05-01 10:00 |

All factories accept keyword overrides. Add instances to a session with `db.add()` then `await db.flush()`.

### Authenticated client helper

`get_authenticated_client(app)` returns an `httpx.AsyncClient` wired to the FastAPI app. Under dev auth bypass, no Authorization header is needed.

### Database session fixture pattern

Most unit test files use this pattern for a session that auto-rolls-back:

```python
@pytest.fixture
async def db():
    from tests.conftest import _test_session_factory
    async with _test_session_factory() as session:
        async with session.begin():
            yield session
        # Rollback happens automatically on exit without commit
```

## 4. Writing New Tests

### Adding a unit test

1. Create a file in the appropriate `test_*/` directory.
2. Use the `db` and `user` fixture pattern shown above.
3. Import factories from `tests.utils` to build test data.
4. Flush (not commit) so the rollback cleans up automatically.

Example -- testing a new service function:

```python
from tests.utils import make_bill

async def test_my_new_feature(db, user):
    bill = make_bill(user.id, sender="Test Co", amount=Decimal("50.00"))
    db.add(bill)
    await db.flush()

    result = await my_service_function(db, user.id)
    assert result.something == expected_value
```

### Adding an integration test

Add a new test class in `test_integration.py` using the session-scoped `client` fixture:

```python
class TestMyFeature:
    async def test_endpoint(self, client: AsyncClient):
        r = await client.get("/api/v1/my-endpoint")
        assert r.status_code == 200
        assert "expected_key" in r.json()
```

### Testing with mock LLM responses

```python
from tests.utils import MockLLMClient

async def test_classification_with_llm():
    mock = MockLLMClient(response='{"classification": "medical", "confidence": 0.85}')
    # inject mock into the code under test
    result = await classify_with_llm(doc, llm_client=mock)
    assert result.classification == "medical"
    assert len(mock.calls) == 1  # verify LLM was called exactly once
```

### Conventions

- All async tests run automatically (pytest asyncio_mode = "auto").
- Session loop scope is set to "session" (`asyncio_default_fixture_loop_scope`).
- Test paths are restricted to `tests/` via pyproject.toml.
- Use `pytest.approx()` for floating-point comparisons.
- Use `unittest.mock.patch` / `AsyncMock` for external services (see `test_push_notification.py`).

## 5. CI Pipeline

Defined in `.github/workflows/ci.yml`. Runs on push to `main` and `feature/**` branches, and on PRs to `main`.

### Jobs

| Job | What it does |
|-----|-------------|
| `lint` | Runs `ruff check .` on the backend (Python 3.13) |
| `test-backend` | Spins up Postgres 16 + Redis 7 as service containers, installs deps, runs migrations, runs `pytest -v` |
| `lint-web` | Runs `npm run lint` on the web frontend (if `web/package.json` exists) |
| `terraform-validate` | Runs `terraform fmt -check` and `terraform validate` on infrastructure |

### Backend test environment in CI

The CI job sets these environment variables:
- `COMPANION_DATABASE_URL` = `postgresql+asyncpg://companion:test@localhost:5432/companion_test`
- `COMPANION_REDIS_URL` = `redis://localhost:6379/0`
- `COMPANION_ENVIRONMENT` = `test`
- `COMPANION_DEV_AUTH_BYPASS` = `true`

### Debugging CI failures

1. Check the GitHub Actions log for the failing job.
2. The `test-backend` job uses the same `pytest -v` command as local runs. Reproduce locally by matching the environment variables above.
3. The database is created fresh each run (DROP + CREATE + `alembic upgrade head`), so migration issues will surface here.
4. If Postgres health checks fail, look for port conflicts or image pull issues.

## 6. Coverage

### Measuring coverage locally

```bash
cd backend
pytest --cov=app --cov-report=term-missing -v
```

For an HTML report:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

The `pytest-cov` package is included in the `[dev]` dependencies.

### Current state

CI does not enforce a coverage threshold. Coverage runs are manual. Key areas with test coverage:

- Conversation layer: prompt builder, tool executor (7 tool handlers tested)
- Pipeline: Tier 1 rule-based classification (bill, medical, junk, legal, fallthrough)
- Services: todo create/complete with bill side-effects, push notifications
- API: auth middleware (dev bypass, pipeline key validation)
- Integration: all major endpoints (health, user, medications, bills, appointments, todos, sections, documents, notifications, conversation lifecycle, contacts, integrations)

Areas without dedicated tests include the full Tier 2 LLM classification path, email/Plaid integrations, and worker/scheduler processes.

## 7. Guidelines Scenario Matrix

Section 14 of `docs/dd-assistant-guidelines.md` defines a 25-scenario test matrix that must pass before any prompt or guidelines changes go live. These are behavioral validation scenarios, not automated unit tests. Key categories:

| Category | Scenarios | Examples |
|----------|-----------|---------|
| Tool use | 1, 7, 11 | Calls list_medications; handles empty state; graceful tool failures |
| Safety boundaries | 2, 9, 10, 16 | Defers to doctor; escalates "I feel unsafe"; refuses role override; triggers exploitation protocol |
| Prompt injection | 3, 15 | Ignores instruction override; treats adversarial OCR text as document data |
| Privacy | 4, 12, 24 | Refuses cross-member queries; respects member preferences; denies excess caregiver access |
| Confidence thresholds | 5, 6 | Low confidence asks for retake; mid-confidence uses soft confirmation |
| Behavioral | 8, 13, 14, 17, 20, 22 | Overdue bill handling; late med confirmation; emotional acknowledgment; simplification |
| UX patterns | 18, 19, 21, 23, 25 | Batching pending items; priority ordering; loading indicators; teach-back confirmation; memory display |

Section 14 also specifies quarterly red team testing (prompt injection, data security, behavioral boundary violations) and automated monitoring (response reading level, tool call success rate, exploitation flags, etc.).

When modifying the D.D. persona or conversation prompts, run through all 25 scenarios manually and document results before merging.
