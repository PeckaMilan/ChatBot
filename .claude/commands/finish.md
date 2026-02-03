# End Development Session

Properly close session with tests, docs, and summary.

## Pre-Finish Checklist

Before ending, ensure:

| Check | Status |
|-------|--------|
| All tests pass | `/test` |
| Docs updated | `/docs` |
| Changes committed | `git status` |
| PLAN.md updated | checkboxes |

## Process

### Step 1: Final Test Run

```bash
# Full test suite with coverage
/test

# If any failures → fix before finishing
```

### Step 2: Update Documentation

```bash
# Update docs for any changes made
/docs
```

### Step 3: Commit Any Remaining Changes

```bash
git status

# If uncommitted changes:
git add .
git commit -m "chore: session end - [summary]

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>"

git push
```

### Step 4: Update PLAN.md

Mark completed tasks, note in-progress items:

```markdown
### Completed This Session
- [x] Task 1
- [x] Task 2

### In Progress
- [ ] Task 3 - [status notes]

### Blockers
- [issue] - [reason]
```

### Step 5: Notify Gemini

```bash
python scripts/gemini_consult.py "Ending session. Completed: [list]. In progress: [list]. Blockers: [list]. Tests: [status]. Docs: [status]. Acknowledge?"
```

### Step 6: Session Summary

Provide summary to human:

```
════════════════════════════════════════════════════════════
SESSION SUMMARY
════════════════════════════════════════════════════════════

📅 Session End
🎯 Iteration: [Koloběžka/Kolo/etc]

✅ COMPLETED
   • [task 1]
   • [task 2]

🔄 IN PROGRESS
   • [task 3] - [status]

🚫 BLOCKED
   • [issue] - [reason]

📊 METRICS
   • Tests: [X passed / Y total]
   • Coverage: [Z%]
   • Commits: [N]

📝 DOCS UPDATED
   • [list of updated docs]

📋 NEXT SESSION
   • [what to work on next]

════════════════════════════════════════════════════════════
```

## Quick Finish (Everything Green)

If all tests pass and docs are updated:

```bash
# One-liner finish
git add -A && git status && python scripts/gemini_consult.py "Session complete. All tests pass. Docs updated. Acknowledge?" && git push
```

## Iteration Milestone Finish

When completing an iteration (not just a session):

```bash
# Tag the iteration
git tag -a v0.X.0-[iteration] -m "[Emoji] [Iteration] complete

Features:
- [feature 1]
- [feature 2]

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>"

git push --tags

# Update CHANGELOG
/docs
```

## Resume Next Time

To continue:
1. Run `/start`
2. All context is preserved in:
   - `PLAN.md` - task status
   - `gemini_session.json` - conversation history
   - Git history - what was done
