---
name: consult
description: Consult with Gemini (human proxy) for autonomous development. Use BEFORE implementing changes and AFTER completing work for review. Gemini approves work aligned with PLAN.md, escalates only for deviations.
user-invocable: true
---

# Autonomous Development with Gemini

Gemini acts as the human's proxy. Consult Gemini instead of asking the human.

## When to Consult

**BEFORE implementation:**
- "I plan to implement X by doing Y. Approve?"
- "I found two approaches: A or B. Which fits the plan better?"

**AFTER implementation:**
- "I completed X. Here's what I did: [summary]. Review?"

**When stuck:**
- "I encountered [problem]. My proposed solution is [X]. Approve?"

## How to Consult

```bash
python scripts/gemini_consult.py "Your question or status update"
```

## Gemini's Responses

| Response | Meaning | Action |
|----------|---------|--------|
| `APPROVED` | Aligned with plan | Proceed |
| `REVISE` | Minor changes needed | Adjust and retry |
| `ESCALATE` | Plan deviation | **Stop and ask human** |

## Workflow

```
┌─────────────────────────────────────────┐
│  1. Read PLAN.md                        │
│  2. Consult Gemini with proposal        │
│  3. If APPROVED → implement             │
│  4. If REVISE → adjust, goto 2          │
│  5. If ESCALATE → STOP, notify human    │
│  6. After implementation → review       │
│  7. Repeat until plan complete          │
└─────────────────────────────────────────┘
```

## Important

- **Always check PLAN.md first** - know what's in scope
- **Never skip consultation** - Gemini is your approver
- **ESCALATE = STOP** - Don't proceed, wait for human
- **Keep Gemini updated** - Share progress regularly

## Session Commands

```bash
# View current plan
python scripts/gemini_consult.py --plan

# View conversation history
python scripts/gemini_consult.py --history

# New session (clear history)
python scripts/gemini_consult.py --clear
```
