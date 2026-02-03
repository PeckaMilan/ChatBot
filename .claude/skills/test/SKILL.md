# Testing Skill

## Overview

This skill provides autonomous testing capabilities for any project. Claude will automatically detect the project stack, run appropriate tests, and ensure code quality before commits.

## Trigger Conditions

**ALWAYS run tests when:**
- User says "test", "run tests", or "/test"
- Before any commit (mandatory - block commit if tests fail)
- After implementing a new feature or fixing a bug
- After refactoring existing code
- When user asks to verify functionality
- Before creating a pull request

**Run tests proactively when:**
- Modifying functions that have existing tests
- Changing shared utilities or core modules
- Updating configuration that affects behavior

## Stack Auto-Detection

Detect the project stack by checking for these files in order:

### Python Projects
```
Priority check:
1. pyproject.toml → look for [tool.pytest] or pytest in dependencies
2. pytest.ini → pytest configuration
3. setup.cfg → [tool:pytest] section
4. conftest.py → pytest fixtures
5. requirements.txt → check for pytest
6. tox.ini → testing environments
```

**Test command:** `pytest` or `python -m pytest`
**Test file pattern:** `test_*.py` or `*_test.py`
**Test directory:** `tests/`, `test/`, or alongside source files

### JavaScript/TypeScript Projects
```
Priority check:
1. package.json → check "scripts.test" for runner
2. jest.config.js / jest.config.ts → Jest
3. vitest.config.js / vitest.config.ts → Vitest
4. .mocharc.* → Mocha
5. cypress.config.* → Cypress (E2E)
6. playwright.config.* → Playwright (E2E)
```

**Test commands:**
- Jest: `npm test` or `npx jest`
- Vitest: `npm test` or `npx vitest`
- Mocha: `npm test` or `npx mocha`

**Test file pattern:** `*.test.js`, `*.spec.js`, `*.test.ts`, `*.spec.ts`
**Test directory:** `__tests__/`, `tests/`, `test/`, or alongside source files

### Go Projects
```
Check for: go.mod, *_test.go files
```

**Test command:** `go test ./...`
**Test file pattern:** `*_test.go`

### Rust Projects
```
Check for: Cargo.toml, tests/ directory
```

**Test command:** `cargo test`
**Test location:** Inline `#[cfg(test)]` modules or `tests/` directory

### Ruby Projects
```
Check for: Gemfile with rspec/minitest, spec/ or test/ directories
```

**Test commands:**
- RSpec: `bundle exec rspec`
- Minitest: `bundle exec rake test`

### Java/Kotlin Projects
```
Check for: pom.xml (Maven), build.gradle (Gradle)
```

**Test commands:**
- Maven: `mvn test`
- Gradle: `./gradlew test`

## Execution Protocol

### Step 1: Detect Stack
```bash
# Run these checks to determine the stack
ls -la  # Check for config files
cat package.json 2>/dev/null | grep -A5 '"scripts"'
cat pyproject.toml 2>/dev/null | head -50
```

### Step 2: Run Tests
Run the appropriate test command based on detection. Always capture output.

```bash
# Python example
pytest -v --tb=short 2>&1

# JavaScript example
npm test 2>&1

# With coverage (when requested or before commits)
pytest --cov=src --cov-report=term-missing
npm test -- --coverage
```

### Step 3: Parse Results
Extract from output:
- Total tests run
- Tests passed/failed/skipped
- Coverage percentage (if available)
- Failing test names and error messages

### Step 4: Report to User
Format results clearly:
```
## Test Results

**Status:** PASSED / FAILED
**Tests:** 45 passed, 0 failed, 2 skipped
**Coverage:** 87% (target: 80%)

### Failed Tests (if any):
- test_user_login: AssertionError - expected 200, got 401
- test_api_response: TimeoutError - request exceeded 5s
```

## Test Coverage Expectations

### Minimum Coverage by Project Type

| Project Type | Minimum | Target | Critical Paths |
|-------------|---------|--------|----------------|
| Production API | 80% | 90% | 95% |
| Library/Package | 85% | 95% | 100% |
| CLI Tool | 70% | 85% | 90% |
| Internal Tool | 60% | 75% | 85% |
| Prototype | 40% | 60% | 70% |

### Coverage Commands by Stack

**Python:**
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

**JavaScript:**
```bash
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
# or for Jest specifically
npx jest --coverage --coverageThreshold='{"global":{"lines":80}}'
```

**Go:**
```bash
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

### What Must Be Covered

**Always test:**
- Public API endpoints
- Core business logic
- Data validation and sanitization
- Error handling paths
- Authentication/authorization
- Database operations (CRUD)

**Can skip:**
- Generated code
- Simple getters/setters
- Framework boilerplate
- Development-only utilities

## Test Structure Conventions

### Directory Layout

```
project/
├── src/                    # Source code
│   ├── auth/
│   │   └── login.py
│   └── api/
│       └── users.py
├── tests/                  # Test files mirror src structure
│   ├── conftest.py         # Shared fixtures (Python)
│   ├── auth/
│   │   └── test_login.py
│   └── api/
│       └── test_users.py
├── tests/integration/      # Integration tests (separate)
└── tests/e2e/             # End-to-end tests (separate)
```

### Test File Naming

| Language | Unit Tests | Integration | E2E |
|----------|-----------|-------------|-----|
| Python | `test_*.py` | `test_*_integration.py` | `test_*_e2e.py` |
| JS/TS | `*.test.ts` | `*.integration.test.ts` | `*.e2e.test.ts` |
| Go | `*_test.go` | `*_integration_test.go` | `*_e2e_test.go` |

### Test Function Naming

Use descriptive names that explain what is being tested:

```python
# Python - use test_ prefix with descriptive name
def test_login_with_valid_credentials_returns_token():
    pass

def test_login_with_invalid_password_returns_401():
    pass

def test_login_rate_limits_after_5_failed_attempts():
    pass
```

```javascript
// JavaScript - use describe/it blocks
describe('UserService', () => {
  describe('login', () => {
    it('should return token for valid credentials', () => {});
    it('should return 401 for invalid password', () => {});
    it('should rate limit after 5 failed attempts', () => {});
  });
});
```

### Test Structure (AAA Pattern)

Always follow Arrange-Act-Assert:

```python
def test_calculate_discount_for_premium_user():
    # Arrange - set up test data and dependencies
    user = User(membership="premium")
    cart = Cart(total=100.00)

    # Act - execute the code under test
    discount = calculate_discount(user, cart)

    # Assert - verify the results
    assert discount == 20.00  # 20% for premium
```

## Gemini Integration for Test Review

### When to Request Gemini Review

**Automatically send to Gemini when:**
- Tests fail with unclear errors
- Coverage drops below threshold
- New test files are created
- Complex test logic is written

### Gemini Review Protocol

After running tests, if review is needed, call the Gemini skill:

```
/gemini review-tests

Context:
- Test file: {path_to_test_file}
- Test output: {captured_test_output}
- Coverage report: {coverage_data}

Questions:
1. Are the test cases comprehensive?
2. Are there edge cases missing?
3. Is the test structure following best practices?
4. Are there any anti-patterns in the tests?
```

### Gemini Review Triggers

| Condition | Action |
|-----------|--------|
| New test file created | Request structure review |
| Test coverage < 70% | Request coverage improvement suggestions |
| Flaky test detected | Request stability analysis |
| Complex mocking | Request mock strategy review |
| Test takes > 5s | Request performance optimization |

### Interpreting Gemini Feedback

Apply Gemini suggestions when they:
- Identify missing edge cases
- Suggest better assertions
- Recommend cleaner test structure
- Point out potential flaky patterns

Question Gemini suggestions when they:
- Add tests for trivial code
- Over-complicate simple tests
- Conflict with project conventions

## Pre-Commit Testing Protocol

### Mandatory Pre-Commit Checks

Before ANY commit, run:

```bash
# 1. Run full test suite
pytest -v  # or npm test

# 2. Check coverage meets threshold
pytest --cov=src --cov-fail-under=80

# 3. Run linting (if configured)
ruff check .  # Python
npm run lint  # JavaScript
```

### Commit Blocking Rules

**BLOCK the commit if:**
- Any test fails
- Coverage drops below project minimum
- New code has no associated tests
- Linting errors exist (warnings OK)

**WARN but allow commit if:**
- Coverage is below target but above minimum
- Skipped tests increase
- Test execution time increases significantly

### Commit Message Test Tags

When tests affect the commit, include in message:
```
feat: add user authentication

- Tests: 12 new, 45 total, all passing
- Coverage: 87% (+3%)
```

## Running Specific Tests

### By File
```bash
# Python
pytest tests/test_auth.py -v

# JavaScript
npm test -- tests/auth.test.js
npx jest auth.test.js
```

### By Test Name
```bash
# Python - match test name
pytest -k "test_login" -v

# JavaScript - match describe/it
npm test -- --testNamePattern="login"
```

### By Marker/Tag
```bash
# Python - run only unit tests
pytest -m "unit" -v

# Python - skip slow tests
pytest -m "not slow" -v

# JavaScript - run only specific suite
npm test -- --testPathPattern="unit"
```

### Failed Tests Only
```bash
# Python - rerun failures
pytest --lf -v

# JavaScript - run failed
npm test -- --onlyFailures
```

## Handling Test Failures

### Diagnosis Steps

1. **Read the error message carefully**
   - What assertion failed?
   - What was expected vs actual?
   - What line caused the failure?

2. **Check test isolation**
   - Does the test pass when run alone?
   - Is there shared state pollution?

3. **Verify test data**
   - Are fixtures correct?
   - Is mock data valid?

4. **Check recent changes**
   - What code changed since tests last passed?
   - Did dependencies update?

### Common Failure Patterns

| Pattern | Cause | Fix |
|---------|-------|-----|
| Works alone, fails in suite | Shared state | Add proper setup/teardown |
| Flaky (random pass/fail) | Race condition or time dependency | Add waits or mock time |
| Timeout | Slow operation or deadlock | Mock external calls |
| Import error | Missing dependency | Check test environment |
| Assertion error | Logic bug or outdated test | Debug and fix |

### Auto-Fix Attempts

Before asking for help, Claude should try:

1. **Re-run the failing test** - Could be transient
2. **Check for obvious fixes** - Typos, wrong imports
3. **Update assertions** - If behavior intentionally changed
4. **Fix test data** - If fixtures are stale

## Test Generation Guidelines

When asked to write tests or when tests are needed:

### Unit Test Template (Python)
```python
import pytest
from src.module import function_to_test

class TestFunctionToTest:
    """Tests for function_to_test"""

    def test_happy_path(self):
        """Test normal expected behavior"""
        result = function_to_test(valid_input)
        assert result == expected_output

    def test_edge_case_empty_input(self):
        """Test behavior with empty input"""
        result = function_to_test("")
        assert result is None

    def test_edge_case_boundary_values(self):
        """Test boundary conditions"""
        result = function_to_test(MAX_VALUE)
        assert result == expected_boundary_output

    def test_error_handling_invalid_input(self):
        """Test proper error handling"""
        with pytest.raises(ValueError, match="Invalid input"):
            function_to_test(invalid_input)

    @pytest.fixture
    def sample_data(self):
        """Fixture for commonly used test data"""
        return {"key": "value"}
```

### Unit Test Template (JavaScript)
```javascript
import { functionToTest } from '../src/module';

describe('functionToTest', () => {
  describe('happy path', () => {
    it('should return expected output for valid input', () => {
      const result = functionToTest(validInput);
      expect(result).toEqual(expectedOutput);
    });
  });

  describe('edge cases', () => {
    it('should handle empty input', () => {
      const result = functionToTest('');
      expect(result).toBeNull();
    });

    it('should handle boundary values', () => {
      const result = functionToTest(MAX_VALUE);
      expect(result).toEqual(expectedBoundaryOutput);
    });
  });

  describe('error handling', () => {
    it('should throw for invalid input', () => {
      expect(() => functionToTest(invalidInput))
        .toThrow('Invalid input');
    });
  });
});
```

## Quick Reference Commands

### Python/pytest
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest -x                       # Stop on first failure
pytest --lf                     # Run last failed
pytest -k "pattern"             # Run matching tests
pytest --cov=src                # With coverage
pytest --cov-report=html        # HTML coverage report
pytest -n auto                  # Parallel execution (pytest-xdist)
```

### JavaScript/Jest
```bash
npm test                        # Run all tests
npm test -- --verbose           # Verbose output
npm test -- --bail              # Stop on first failure
npm test -- --onlyFailures      # Run last failed
npm test -- --testNamePattern   # Run matching tests
npm test -- --coverage          # With coverage
npm test -- --watch             # Watch mode
```

### Go
```bash
go test ./...                   # Run all tests
go test -v ./...                # Verbose output
go test -run TestName           # Run specific test
go test -cover ./...            # With coverage
go test -race ./...             # Race detection
```

## Summary Checklist

Before considering testing complete:

- [ ] Stack detected correctly
- [ ] All tests pass
- [ ] Coverage meets project threshold
- [ ] New code has corresponding tests
- [ ] Edge cases covered
- [ ] Error handling tested
- [ ] No flaky tests introduced
- [ ] Test execution time reasonable
- [ ] Gemini review completed (if applicable)
- [ ] Results reported to user
