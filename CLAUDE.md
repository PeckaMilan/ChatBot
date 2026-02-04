# ChatBot - Claude Code Workflow

## Project Purpose
This project uses the autonomous Claude + Gemini development workflow.

## Environment
- Platform: Windows 11
- Shell: CMD
- Workflow: Claude_Max template

---

## ⚠️ FIRST: Gemini Session Continuity

**Gemini conversation is PERSISTENT across Claude sessions!**

### At EVERY Session Start - DO THIS FIRST:
```bash
# 1. Check existing Gemini conversation
python scripts/gemini_consult.py --history

# 2. Resume with context acknowledgment
python scripts/gemini_consult.py "Resuming session. [Summary of last state]. Continuing with [next task]. Acknowledge?"
```

### Why This Matters:
- Gemini **remembers ALL previous consultations** in `.claude/gemini_session.json`
- Claude sessions are **ephemeral** - you start fresh each time
- **Always read --history first** and acknowledge previous context

---

## CRITICAL: Gemini Consultation Rules

**Claude MUST consult Gemini via `python scripts/gemini_consult.py` in these situations:**

### BEFORE Starting Work
```bash
python scripts/gemini_consult.py "Starting [task]. Plan: [brief description]. Approve?"
```

### BEFORE Each Major Change
- Creating new files
- Modifying architecture
- Adding dependencies
- Changing API endpoints
- Database schema changes

### AFTER Completing Each Task
```bash
python scripts/gemini_consult.py "Completed [task]. Summary: [what was done]. Review?"
```

### When Encountering Problems
```bash
python scripts/gemini_consult.py "Problem: [issue]. Proposed solution: [approach]. Approve?"
```

### Consultation Frequency
| Situation | Consult? |
|-----------|----------|
| Before starting any task | ✅ YES |
| After completing any task | ✅ YES |
| Before creating new file | ✅ YES |
| Before modifying existing code | ✅ YES |
| When stuck or uncertain | ✅ YES |
| Simple typo fix | ❌ No |

### Response Handling
| Response | Action |
|----------|--------|
| `APPROVED` | Proceed with implementation |
| `REVISE` | Adjust approach, consult again |
| `ESCALATE` | **STOP IMMEDIATELY**, ask human |

---

## Commands Available
- `/init` - Initialize Git + Business Discovery
- `/plan` - Technical planning
- `/start` - Start autonomous development
- `/finish` - End session
- `/test` - Run tests
- `/docs` - Update documentation
- `/kb` - Local knowledge base
- `/ckb` - Central knowledge base (Claude_Knowledge)

## Current Iteration
Check `.claude/PLAN.md` for current tasks.

## Knowledge Bases
- **Local KB:** `.claude/knowledge/` - project-specific
- **Central KB:** `C:\Users\mpeck\PycharmProjects\Claude_Knowledge\knowledge\` - shared across projects

## Important Files
- `.claude/BUSINESS.md` - Business requirements
- `.claude/PLAN.md` - Technical plan with tasks
- `.claude/gemini_session.json` - Gemini conversation history
- `scripts/gemini_consult.py` - Gemini API integration
