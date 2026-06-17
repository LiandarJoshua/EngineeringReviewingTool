# Testing Principles — Code Review Reference

## The Testing Pyramid

```
        /\
       /E2E\        (few, slow, expensive)
      /------\
     /Integr. \     (moderate)
    /----------\
   /  Unit Tests \  (many, fast, cheap)
  /--------------\
```

**Code review signals for poor test coverage:**
- No `tests/` directory
- Only unit tests, no integration tests (tests pass but system fails)
- Test file count < 20% of source file count
- All tests are mocked — no real DB or HTTP tests

---

## Unit Tests
**What:** Test a single function in isolation. All external deps mocked.
**What to look for:**
```python
def test_calculate_score():
    findings = [Finding(severity="critical"), Finding(severity="low")]
    assert calculate_score(findings) == 45.0
```
**Red flags:**
- Tests that test framework code, not your code
- No assertions (just calls the function)
- Tests coupled to implementation details (testing private methods)

---

## Integration Tests
**What:** Test multiple components working together. Hit a real DB, real Redis.
```python
@pytest.mark.asyncio
async def test_create_review_stores_in_db(test_db):
    review = await create_review(db=test_db, repo_url="http://github.com/x/y")
    stored = await test_db.get(Review, review.id)
    assert stored.status == "pending"
```
**Best practice:** Use a test database, not a mock. Mocking the DB hides real SQL bugs.

---

## Test Coverage
**Target:** 80%+ line coverage for business logic.
**What coverage doesn't catch:** Logic correctness, edge cases not written.
**Code review signals:**
- No `pytest-cov` or coverage config
- Coverage only on models/schemas (easy targets), not on business logic

---

## Test Fixtures and Factories
**Good pattern:** Factory functions that create test objects with sensible defaults.
```python
def make_finding(severity="low", category="style", **kwargs):
    return Finding(severity=severity, category=category, issue="...", **kwargs)
```
**Anti-pattern:** Copy-pasted test setup in every test function.

---

## Testing Async Code
```python
@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
```

---

## What to Flag in Code Review
| Issue | Severity |
|---|---|
| No tests at all | High |
| Critical paths untested (auth, payment, write operations) | High |
| Tests that always pass (no real assertions) | High |
| No integration tests | Medium |
| Coverage < 40% | Medium |
| Tests with `time.sleep()` | Low |
| Hardcoded test data (brittle) | Low |
