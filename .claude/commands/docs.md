# Update Documentation

Update project documentation based on current state.

## Documentation Structure

```
project/
├── README.md           # Project overview, quick start
└── docs/
    ├── ARCHITECTURE.md # System design, decisions
    ├── API.md          # Endpoints, functions
    └── CHANGELOG.md    # Version history
```

## Process

### Step 1: Check What Needs Update

```bash
# List recent changes
git diff --name-only HEAD~5

# Check current docs
ls -la docs/ 2>/dev/null || echo "No docs/ directory yet"
```

### Step 2: Initialize Docs (if needed)

```bash
mkdir -p docs

# Copy templates
TEMPLATE_DIR=".claude/templates"
[ ! -f "README.md" ] && cp "$TEMPLATE_DIR/README.template.md" README.md
[ ! -f "docs/ARCHITECTURE.md" ] && cp "$TEMPLATE_DIR/ARCHITECTURE.template.md" docs/ARCHITECTURE.md
[ ! -f "docs/API.md" ] && cp "$TEMPLATE_DIR/API.template.md" docs/API.md
[ ! -f "docs/CHANGELOG.md" ] && cp "$TEMPLATE_DIR/CHANGELOG.template.md" docs/CHANGELOG.md
```

### Step 3: Update Based on Trigger

| Trigger | Update |
|---------|--------|
| Iteration complete | All docs + CHANGELOG |
| New feature | README, API, CHANGELOG |
| Architecture change | ARCHITECTURE, CHANGELOG |
| Bug fix | CHANGELOG only |
| API change | API, CHANGELOG |

### Step 4: Gemini Validation

After updating, validate with Gemini:

```bash
python scripts/gemini_consult.py "Documentation updated for [CHANGE]. Docs summary: [KEY POINTS]. Validate accuracy and completeness."
```

### Step 5: Commit Docs

```bash
git add README.md docs/
git commit -m "docs: update for [iteration/feature]

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Iteration Documentation Checklist

### 🛴 Koloběžka (MVP)
- [ ] README: Basic description, quick start
- [ ] ARCHITECTURE: Initial design
- [ ] CHANGELOG: v0.1.0

### 🚲 Kolo
- [ ] README: Add features section
- [ ] ARCHITECTURE: Update components
- [ ] API: Document endpoints
- [ ] CHANGELOG: v0.2.0

### 🏍️ Motorka
- [ ] README: Performance notes
- [ ] ARCHITECTURE: Optimization decisions
- [ ] CHANGELOG: v0.3.0

### 🚗 Auto
- [ ] README: Production setup
- [ ] ARCHITECTURE: Security, deployment
- [ ] API: Full documentation
- [ ] CHANGELOG: v1.0.0

### ✈️ Letadlo
- [ ] README: Scale documentation
- [ ] ARCHITECTURE: Enterprise patterns
- [ ] CHANGELOG: v2.0.0

## Quick Reference

| What changed | Command |
|--------------|---------|
| Everything | `/docs` |
| Just changelog | Update docs/CHANGELOG.md |
| API only | Update docs/API.md |
