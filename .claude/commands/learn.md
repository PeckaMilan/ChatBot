# Learning Commands

Manage continuous learning and pattern extraction.

## Commands

### Extract Patterns from Session

Analyze current session for reusable patterns:

```bash
# Check what could be learned
echo "Analyzing session for patterns..."

# Look for:
# 1. Repeated tool sequences
# 2. Error → fix pairs
# 3. User corrections
# 4. Code style patterns
```

Then consult Gemini:
```bash
python scripts/gemini_consult.py --no-plan "Session analysis: I observed these patterns: [LIST]. Which are worth saving as skills/instincts?"
```

### Extract from Git History

Analyze commit history for project conventions:

```bash
# Get commit message patterns
git log --oneline -50 | head -20

# Get frequently changed files
git log --name-only --pretty=format: | sort | uniq -c | sort -rn | head -10

# Get file co-changes
git log --name-only --pretty=format: | grep -v '^$' | sort | uniq
```

Then create skill from patterns found.

### Review Learned Patterns

List all learned skills and instincts:

```bash
# Global learned skills
ls -la ~/.claude/skills/learned/ 2>/dev/null || echo "No learned skills yet"

# Global instincts
ls -la ~/.claude/homunculus/instincts/personal/ 2>/dev/null || echo "No instincts yet"

# Project-specific
ls -la .claude/learned/ 2>/dev/null || echo "No project learning yet"
```

### Create New Instinct

Template for manual instinct creation:

```markdown
---
id: [unique-id]
trigger: "when [condition]"
action: "do [action]"
confidence: 0.5
domain: [code-style|testing|git|debugging|workflow]
created: [date]
---

# [Pattern Name]

[Description of the pattern]

## When to Apply
[Conditions]

## Example
[Code example]
```

Save to: `~/.claude/homunculus/instincts/personal/[id].md`

### Promote to Skill

When instinct has high confidence (0.7+), promote to full skill:

```bash
# 1. Read instinct
cat ~/.claude/homunculus/instincts/personal/[id].md

# 2. Create skill directory
mkdir -p ~/.claude/skills/learned/[skill-name]

# 3. Write SKILL.md with expanded content
```

## Pattern Types to Look For

### Error Resolutions
```
Pattern: "ImportError: No module named X"
Fix: "pip install X"
→ Create instinct: "When ImportError, suggest pip install"
```

### Code Style
```
Pattern: User always uses f-strings
→ Create instinct: "Prefer f-strings over .format()"
```

### Workflow
```
Pattern: After editing tests, always run pytest
→ Create instinct: "Run tests after test file changes"
```

### Project Conventions
```
Pattern: API endpoints always in src/api/
→ Create skill: "API file structure conventions"
```

## Gemini Integration

Always validate before creating skills:

```bash
python scripts/gemini_consult.py --no-plan "I want to create a skill for: [PATTERN]. Evidence: [EXAMPLES]. Is this a good reusable pattern?"
```

Gemini will:
- `APPROVED` → Create the skill
- `REVISE` → Suggest improvements
- `ESCALATE` → Pattern too project-specific, ask human

## Quick Workflow

```
1. Notice repeating pattern
2. Consult Gemini: "Is this worth learning?"
3. If APPROVED:
   - Low confidence → Create instinct
   - High confidence → Create skill
4. Save to appropriate location
5. Pattern now available for future sessions
```

## Storage Summary

| Type | Location | When |
|------|----------|------|
| Instinct | `~/.claude/homunculus/instincts/personal/` | Atomic patterns |
| Skill | `~/.claude/skills/learned/` | Complex workflows |
| Project | `.claude/learned/` | Project-specific |
