# Start Autonomous Development Session

Begin working on the current iteration with Gemini as supervisor.

## Prerequisites

- `.claude/PLAN.md` has approved tasks
- `.claude/BUSINESS.md` is approved
- Current iteration defined

## Session Start

### 1. Load Context

```bash
# Show current plan
python scripts/gemini_consult.py --plan

# Check git status
git status
```

### 2. Announce to Gemini

```bash
python scripts/gemini_consult.py "Starting session. Iteration: [X]. Tasks: [list]. Acknowledge?"
```

### 3. Verify Tests Pass

```bash
# Run existing tests before making changes
/test
```

## Development Loop

```
┌─────────────────────────────────────────────────────────────┐
│  FOR EACH TASK:                                             │
│                                                             │
│  1. Consult: "I'll implement [X] by [Y]. Approve?"          │
│     └─► APPROVED → continue                                 │
│     └─► REVISE → adjust approach                            │
│     └─► ESCALATE → STOP, ask human                          │
│                                                             │
│  2. Implement the change                                    │
│                                                             │
│  3. Write/update tests                                      │
│     └─► Run: /test                                          │
│     └─► Tests MUST pass before proceeding                   │
│                                                             │
│  4. Consult: "Done [X]. Tests pass. Review?"                │
│     └─► APPROVED → mark task complete                       │
│     └─► REVISE → fix issues                                 │
│                                                             │
│  5. Update PLAN.md checkbox                                 │
│                                                             │
│  6. Commit changes                                          │
│     git add [files]                                         │
│     git commit -m "feat: [description]                      │
│                                                             │
│     Co-Authored-By: Claude <noreply@anthropic.com>"         │
│                                                             │
│  7. Next task                                               │
└─────────────────────────────────────────────────────────────┘
```

## Quality Gates

Before marking ANY task complete:

| Check | Command | Must Pass |
|-------|---------|-----------|
| Tests | `/test` | ✅ All green |
| Gemini review | `consult` | ✅ APPROVED |
| No lint errors | stack-specific | ✅ Clean |

## Iteration Complete

When all tasks for iteration done:

### 1. Full Test Suite
```bash
/test  # With coverage
```

### 2. Update Documentation
```bash
/docs  # Update all docs for this iteration
```

### 3. Gemini Final Review
```bash
python scripts/gemini_consult.py "Iteration [X] complete. Summary: [changes]. Tests: [status]. Docs: [updated]. Final review?"
```

### 4. Tag Release
```bash
git tag -a v0.X.0-[iteration] -m "[Iteration] complete"
git push --tags
```

### 5. Notify Human
"Iteration [X] complete! Ready for next iteration or human review."

## Rules

- **Never skip tests** - no commit without green tests
- **Never skip Gemini** - always consult before/after
- **ESCALATE = STOP** - wait for human
- **Document as you go** - not at the end
- **Commit often** - small, focused commits
