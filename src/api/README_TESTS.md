# API Tests Documentation

## Overview

This directory contains comprehensive tests for the Python API wrapper modules, targeting 80%+ coverage of critical paths.

## Test Structure

```
src/api/
├── test_models.py           # 45 tests for Pydantic models
├── test_supabase_client.py  # 22 tests for Supabase client
└── conftest.py              # Shared fixtures and configuration
```

## Test Coverage

**Total: 67 tests, 100% passing**

### Models Tests (45 tests)
- `test_models.py` - 100% coverage
  - GenerationRequest validation (4 tests)
  - UserAnswer validation (4 tests)
  - NewsletterContext validation (4 tests)
  - ProgressUpdate validation (6 tests)
  - CoreIssue validation (3 tests)
  - DeepDive validation (3 tests)
  - Source validation (2 tests)
  - NewsletterContent validation (5 tests)
  - Response models validation (7 tests)
  - Edge cases and serialization (7 tests)

### Supabase Client Tests (22 tests)
- `test_supabase_client.py` - 98% coverage
  - Client initialization (4 tests)
  - Topic and answers retrieval (3 tests)
  - Newsletter request creation (2 tests)
  - Request status updates (4 tests)
  - Newsletter saving (2 tests)
  - Newsletter retrieval (4 tests)
  - Singleton pattern (2 tests)
  - Integration flow (1 test)

## Running Tests

### Run All Tests
```bash
uv run pytest src/api/test_*.py -v
```

### Run Specific Test File
```bash
# Models only
uv run pytest src/api/test_models.py -v

# Supabase client only
uv run pytest src/api/test_supabase_client.py -v
```

### Run with Coverage Report
```bash
# Terminal report
uv run pytest src/api/test_*.py --cov=src/api --cov-report=term-missing

# HTML report (outputs to htmlcov/)
uv run pytest src/api/test_*.py --cov=src/api --cov-report=html

# Both
uv run pytest src/api/test_*.py --cov=src/api --cov-report=term-missing --cov-report=html --cov-branch
```

### Run Tests by Marker
```bash
# Unit tests only
uv run pytest src/api -m unit

# Asyncio tests only
uv run pytest src/api -m asyncio

# Exclude slow tests
uv run pytest src/api -m "not slow"
```

### Run with Specific Options
```bash
# Short traceback
uv run pytest src/api/test_*.py --tb=short

# Stop on first failure
uv run pytest src/api/test_*.py -x

# Show local variables in tracebacks
uv run pytest src/api/test_*.py -l

# Verbose output with test durations
uv run pytest src/api/test_*.py -v --durations=10
```

## Test Coverage Summary

| Module | Statements | Coverage |
|--------|-----------|----------|
| models.py | 68 | 100% |
| supabase_client.py | 71 | 98% |
| test_models.py | 229 | 100% |
| test_supabase_client.py | 318 | 99% |

**Overall Coverage: 72%** (excluding newsletter_generator.py which has separate integration tests)

## Testing Patterns

### Mocking External Dependencies

All external dependencies are mocked in tests:
- Supabase client (`create_client`)
- Environment variables (via `monkeypatch`)
- LangSmith integration

### Fixtures

Shared fixtures in `conftest.py`:
- `reset_singleton` - Resets SupabaseClient singleton
- `sample_topic_data` - Sample topic data
- `sample_questions_data` - Sample questions
- `sample_answers_data` - Sample answers
- `sample_newsletter_content` - Complete newsletter content
- `mock_supabase_response_builder` - Factory for mock responses

### Test Organization

Tests are organized into classes by feature:
```python
class TestGenerationRequest:
    def test_valid_generation_request(self): ...
    def test_missing_user_id(self): ...
```

### Async Tests

Async tests use pytest-asyncio:
```python
@pytest.mark.asyncio
async def test_get_topic_and_answers_success(self):
    # Test async method
    result = await client.get_topic_and_answers("topic-id")
```

## Key Test Scenarios

### 1. Validation Tests
- Valid input acceptance
- Invalid input rejection
- Required field validation
- Type validation
- Range validation (e.g., progress 0-100)
- Length constraints (e.g., core_issues 3-5)

### 2. Edge Cases
- Empty strings
- Very long strings (10,000+ chars)
- Unicode characters (Korean, emoji)
- Special characters in URLs
- None vs empty list distinction
- Model serialization/deserialization

### 3. Error Handling
- Missing environment variables
- Database connection failures
- Not found errors
- Invalid data format errors

### 4. Integration Scenarios
- Complete newsletter generation flow
- Multi-step operations
- State transitions (pending → processing → completed)

## Continuous Integration

Tests run automatically in GitHub Actions:
- On push to main/dev branches
- On pull requests
- After changes to `src/api/**` files

See `.github/workflows/ci-python.yml` for CI configuration.

## Extending Tests

When adding new features:

1. **Add model tests** (`test_models.py`):
   - Valid creation
   - Invalid input handling
   - Edge cases

2. **Add client tests** (`test_supabase_client.py`):
   - Mock database responses
   - Test success paths
   - Test error paths
   - Test edge cases

3. **Update fixtures** (`conftest.py`):
   - Add sample data fixtures
   - Add mock builders if needed

4. **Run coverage check**:
   ```bash
   uv run pytest src/api --cov=src/api --cov-report=term-missing
   ```

5. **Aim for 80%+ coverage** on new code

## Dependencies

Test dependencies (in `pyproject.toml`):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]
```

Install with:
```bash
uv sync --all-extras
```

## Known Issues

### Deprecation Warnings

Some deprecation warnings are expected:
- `datetime.utcnow()` → Use `datetime.now(datetime.UTC)` (planned fix)
- Pydantic `min_items/max_items` → Use `min_length/max_length` (planned fix)
- Third-party library warnings (pyiceberg, pyparsing)

These don't affect functionality and are scheduled for cleanup.

## Future Improvements

1. Add integration tests with real Supabase test instance
2. Add performance benchmarks
3. Add mutation testing (mutmut)
4. Increase coverage to 90%+
5. Add property-based testing (hypothesis)
6. Add contract tests for API endpoints

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Pydantic documentation](https://docs.pydantic.dev/)
