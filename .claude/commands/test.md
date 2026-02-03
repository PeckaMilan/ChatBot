# Run Tests

Execute tests for the current project with Gemini review.

## Process

### Step 1: Detect Stack

```bash
# Auto-detect and run appropriate tests
if [ -f "pyproject.toml" ] || [ -f "pytest.ini" ] || [ -f "setup.py" ]; then
    echo "🐍 Python detected"
    pytest -v --tb=short
elif [ -f "package.json" ]; then
    echo "📦 JavaScript/TypeScript detected"
    npm test
elif [ -f "go.mod" ]; then
    echo "🔷 Go detected"
    go test ./...
elif [ -f "Cargo.toml" ]; then
    echo "🦀 Rust detected"
    cargo test
else
    echo "❓ Unknown stack - check manually"
fi
```

### Step 2: Coverage Report

```bash
# Python
pytest --cov=. --cov-report=term-missing

# JavaScript
npm test -- --coverage

# Go
go test -cover ./...
```

### Step 3: Gemini Review (if failures or low coverage)

If tests fail or coverage < 70%:

```bash
python scripts/gemini_consult.py "Test results: [PASTE RESULTS]. Issues found. Review and suggest fixes."
```

### Step 4: Report

After tests complete, summarize:
- ✅ Passed: X
- ❌ Failed: Y
- 📊 Coverage: Z%

If all pass → ready for commit.
If failures → fix before proceeding.

## Quick Commands

| Stack | Test | Coverage |
|-------|------|----------|
| Python | `pytest -v` | `pytest --cov=.` |
| JS/TS | `npm test` | `npm test -- --coverage` |
| Go | `go test ./...` | `go test -cover ./...` |
| Rust | `cargo test` | `cargo tarpaulin` |

## Integration with Workflow

- **Before commit:** Tests MUST pass
- **After implementation:** Run tests
- **Before iteration complete:** Full test suite + coverage
