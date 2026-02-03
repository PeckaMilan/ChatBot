---
name: learn
description: Continuous learning system for Claude. Automatically extracts patterns from sessions, creates new skills, and improves over time. Integrates with Gemini for validation.
user-invocable: true
---

# Continuous Learning System

Claude learns from sessions and creates reusable skills automatically.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LEARNING PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Session Activity                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                           │
│  │  Observe    │  ← Hooks capture tool use, errors, fixes  │
│  └─────────────┘                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                           │
│  │  Extract    │  ← Identify repeating patterns            │
│  └─────────────┘                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                           │
│  │  Validate   │  ← Gemini reviews pattern quality         │
│  └─────────────┘                                           │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────┐                                           │
│  │  Create     │  ← Generate SKILL.md or instinct          │
│  └─────────────┘                                           │
│       │                                                     │
│       ▼                                                     │
│  ~/.claude/skills/learned/                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## What Gets Learned

### Automatic Detection

| Pattern Type | Example | Storage |
|--------------|---------|---------|
| Error Resolution | "ModuleNotFoundError → pip install X" | Instinct |
| User Corrections | "Don't use semicolons in Python" | Instinct |
| Code Style | "Always use f-strings" | Instinct |
| Workflow | "After edit, always run tests" | Skill |
| Project Conventions | "API files go in src/api/" | Skill |
| Tool Preferences | "Use Glob before Grep" | Instinct |

### Pattern Confidence

```
0.3 ─────────────────────────────────── 0.9
 │                                        │
 Low confidence                    High confidence
 (observed 1-2x)                   (observed 5+x)

Confidence increases:
  ✓ Pattern observed repeatedly
  ✓ User doesn't correct it
  ✓ Gemini approves

Confidence decreases:
  ✗ User explicitly corrects
  ✗ Pattern causes errors
  ✗ Contradicting evidence
```

## Integration with Gemini

Before creating a new skill, validate with Gemini:

```bash
python scripts/gemini_consult.py --no-plan "Learning: I observed pattern [X] repeated [N] times. Should I create a skill for this? Context: [examples]"
```

Gemini responses:
- `APPROVED` → Create skill/instinct
- `REVISE` → Adjust pattern definition
- `ESCALATE` → Ask human (major workflow change)

## Storage Locations

### Instincts (Atomic Patterns)

```
~/.claude/homunculus/instincts/personal/
├── error-resolution-001.md
├── code-style-002.md
└── workflow-003.md
```

### Learned Skills (Complex Patterns)

```
~/.claude/skills/learned/
├── api-patterns/SKILL.md
├── test-workflow/SKILL.md
└── error-handling/SKILL.md
```

### Project-Specific Learning

```
.claude/learned/
├── project-conventions.md
└── common-fixes.md
```

## Instinct Format

```yaml
---
id: unique-identifier
trigger: "when [condition]"
action: "do [action]"
confidence: 0.7
domain: code-style|testing|git|debugging|workflow
evidence:
  - "Observed in session X"
  - "User confirmed in session Y"
created: 2025-02-01
updated: 2025-02-03
---

# Pattern Description

[Detailed explanation of when and how to apply this pattern]

## Examples

[Code examples showing the pattern]
```

## Skill Format

```yaml
---
name: learned-pattern-name
description: Auto-generated skill from observed patterns
confidence: 0.8
source: continuous-learning
created: 2025-02-01
---

# Learned Pattern: [Name]

## When to Apply

[Conditions that trigger this skill]

## Pattern

[The actual pattern/workflow]

## Evidence

- Observed [N] times in sessions
- Validated by Gemini on [date]
- Confidence: [score]
```

## Manual Learning Commands

### Extract from Current Session

```bash
/learn extract
```
Analyzes current session for patterns.

### Extract from Git History

```bash
/learn git
```
Analyzes commit history for conventions.

### Review Learned Patterns

```bash
/learn review
```
Shows all learned patterns with confidence scores.

### Promote Instinct to Skill

```bash
/learn promote [instinct-id]
```
Converts high-confidence instinct to full skill.

## Automatic Triggers

### Session End Hook

At end of each session:
1. Check if session had 10+ meaningful interactions
2. Extract potential patterns
3. Consult Gemini for validation
4. Save approved patterns

### Error Resolution Hook

When an error is fixed:
1. Capture error → solution pair
2. Check if similar error seen before
3. If new, create instinct with low confidence
4. If repeated, increase confidence

### User Correction Hook

When user corrects Claude:
1. Capture the correction
2. Create "don't do X" instinct
3. High initial confidence (user explicit)

## Best Practices

### For Claude

1. **Observe actively** - Note when patterns repeat
2. **Ask before creating** - Consult Gemini for non-obvious patterns
3. **Start with instincts** - Promote to skills after validation
4. **Update confidence** - Adjust based on feedback

### For Human

1. **Correct explicitly** - "Don't do X, do Y instead"
2. **Confirm good patterns** - "Yes, always do it this way"
3. **Review periodically** - `/learn review` to prune bad patterns

## Integration with Workflow

```
/start
   │
   ├─► Load learned patterns
   │
   ├─► Apply relevant skills/instincts
   │
   ├─► Work (observe new patterns)
   │
   └─► /finish
          │
          └─► Extract and save new patterns
```
