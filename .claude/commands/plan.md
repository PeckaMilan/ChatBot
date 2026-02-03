# Create Technical Plan

Transform approved business requirements into a technical implementation plan.

## Prerequisites

- `.claude/BUSINESS.md` must be approved (checkbox checked)
- Business requirements must be complete

## Your Role (Claude)

Create a detailed technical plan based on BUSINESS.md. For each iteration, define:
- Specific implementation tasks
- Architecture decisions
- File structure
- Dependencies

## Process

### Step 1: Read Business Requirements
```bash
cat .claude/BUSINESS.md
```
Understand the vision, iterations, and constraints.

### Step 2: Propose Architecture
Consult Gemini:
```bash
python scripts/gemini_consult.py --no-plan "Technical planning for [project]. Given these requirements: [summary]. I propose this architecture: [proposal]. Evaluate critically."
```

### Step 3: Define Current Iteration Tasks
Start with 🛴 Koloběžka. Break it into specific, actionable tasks:
- Each task should be completable in one session
- Tasks should be independent where possible
- Include file paths and specific changes

### Step 4: Document in PLAN.md
Update `.claude/PLAN.md` with:
- Current iteration (Koloběžka)
- Architecture diagram (ASCII)
- Tech stack
- Task list with checkboxes

### Step 5: Get Human Approval
Present the plan to human. Ask:
- "Does this architecture make sense?"
- "Is the MVP scope correct?"
- "Any constraints I missed?"

### Step 6: Start Development
Once approved, use `/start` to begin autonomous development.
Gemini will approve work within the plan.
Human is only contacted for ESCALATE situations.

## Output

A complete PLAN.md ready for autonomous execution.
