# ChatBot - Claude Code Workflow

## Project Purpose
This project uses the autonomous Claude + Gemini development workflow.

## Environment
- Platform: Windows 11
- Shell: CMD
- Workflow: Claude_Max template

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
