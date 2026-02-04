---
name: consult
description: Consult with Gemini (human proxy) for autonomous development. Use BEFORE implementing changes and AFTER completing work for review. Gemini approves work aligned with PLAN.md, escalates only for deviations.
user-invocable: true
---

# Autonomous Development with Gemini

Gemini acts as the human's proxy. **ALWAYS consult Gemini** instead of asking the human.

## ⚠️ CRITICAL: Session Continuity

**Gemini conversation is PERSISTENT across Claude sessions!**

### At Every Session Start - DO THIS FIRST:
```bash
# 1. Check existing Gemini conversation
python scripts/gemini_consult.py --history

# 2. Resume the conversation with context
python scripts/gemini_consult.py "Resuming session. [Summarize last known state]. Continuing with [next task]. Acknowledge?"
```

### Why This Matters:
- Gemini **remembers ALL previous consultations** in `.claude/gemini_session.json`
- Claude sessions are **ephemeral** - you start fresh each time
- Gemini has the **full project context** - use it!
- **Never ignore previous Gemini conversation** - always acknowledge and continue

### Session File:
```
.claude/gemini_session.json  →  Persistent conversation history
```

### Resuming Examples:
```bash
# After reading --history, acknowledge context:
python scripts/gemini_consult.py "Resuming. Last session we completed Phase 1 setup. Now starting Phase 2: API implementation. Continue?"

# If picking up mid-task:
python scripts/gemini_consult.py "Resuming task T2.3 (user auth). Previously approved Firebase approach. Implementing now. Confirm?"
```

---

## MANDATORY Consultation Points

### 1. BEFORE Starting ANY Task
```bash
python scripts/gemini_consult.py "Starting task [X]. Approach: [brief]. Approve?"
```

### 2. BEFORE Creating ANY New File
```bash
python scripts/gemini_consult.py "Creating [filename] for [purpose]. Structure: [brief]. Approve?"
```

### 3. BEFORE Modifying Existing Code
```bash
python scripts/gemini_consult.py "Modifying [file] to [change]. Reason: [why]. Approve?"
```

### 4. AFTER Completing ANY Task
```bash
python scripts/gemini_consult.py "Completed [task]. Changes: [summary]. Files: [list]. Review?"
```

### 5. When Encountering ANY Problem
```bash
python scripts/gemini_consult.py "Problem: [issue]. Proposed solution: [approach]. Approve?"
```

### 6. Before Adding Dependencies
```bash
python scripts/gemini_consult.py "Adding dependency [package] for [reason]. Approve?"
```

## Consultation Checklist

| Action | Must Consult? | Example |
|--------|---------------|---------|
| Start task from PLAN.md | ✅ ALWAYS | "Starting T1.2..." |
| Create new file | ✅ ALWAYS | "Creating api/routes.py..." |
| Modify existing file | ✅ ALWAYS | "Modifying main.py to add..." |
| Add package/dependency | ✅ ALWAYS | "Adding fastapi..." |
| Complete task | ✅ ALWAYS | "Completed T1.2. Summary:..." |
| Architecture decision | ✅ ALWAYS | "Choosing between A and B..." |
| Problem/blocker | ✅ ALWAYS | "Error encountered:..." |
| Fix typo | ❌ Skip | Simple correction |
| Format code | ❌ Skip | Just formatting |

## Gemini's Responses

| Response | Meaning | Your Action |
|----------|---------|-------------|
| `APPROVED` | Go ahead | ✅ Implement now |
| `REVISE` | Adjust needed | 🔄 Modify approach, consult again |
| `ESCALATE` | Plan deviation | 🛑 **STOP! Ask human directly** |

## Workflow Loop

```
┌──────────────────────────────────────────────────────┐
│  FOR EACH TASK in PLAN.md:                           │
│                                                      │
│  1. Read task description                            │
│  2. Consult: "Starting [task]. Approach: X. OK?"     │
│  3. Wait for APPROVED                                │
│  4. FOR EACH file change:                            │
│     a. Consult: "Creating/Modifying [file]. OK?"     │
│     b. Wait for APPROVED                             │
│     c. Make the change                               │
│  5. Consult: "Completed [task]. Summary: X. Review?" │
│  6. Wait for APPROVED                                │
│  7. Move to next task                                │
└──────────────────────────────────────────────────────┘
```

## Example Session

```bash
# Starting a task
python scripts/gemini_consult.py "Starting T1.2: Create folder structure. Will create: backend/, frontend/, shared/. Approve?"
# → APPROVED

# Before creating file
python scripts/gemini_consult.py "Creating backend/main.py with FastAPI app setup. Approve?"
# → APPROVED

# After creating file
python scripts/gemini_consult.py "Created backend/main.py with FastAPI, CORS, health endpoint. Review?"
# → APPROVED

# Problem encountered
python scripts/gemini_consult.py "Problem: Firebase SDK requires service account. Solution: Add to .env.example. Approve?"
# → APPROVED
```

## IMPORTANT RULES

1. **Never skip consultation** - Gemini is your tech lead
2. **ESCALATE = FULL STOP** - Don't proceed, ask human directly
3. **When in doubt, consult** - Better to ask than assume
4. **Keep messages concise** - Brief but complete
5. **Include file names** - Always mention which files are affected

## Session Management

```bash
# View conversation history
python scripts/gemini_consult.py --history

# Clear history (new session)
python scripts/gemini_consult.py --clear

# Show current plan context
python scripts/gemini_consult.py --plan
```
