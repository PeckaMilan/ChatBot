---
name: central-kb
description: Central Knowledge Base integration. Read and write knowledge from/to the shared Claude_Knowledge repository. Use when discovering reusable knowledge or searching for existing solutions.
user-invocable: true
---

# Central Knowledge Base

Shared knowledge repository at `C:\Users\mpeck\PycharmProjects\Claude_Knowledge`.

## Repository Location

```
KNOWLEDGE_REPO="C:/Users/mpeck/PycharmProjects/Claude_Knowledge"
KNOWLEDGE_DIR="$KNOWLEDGE_REPO/knowledge"
```

## Categories

| Category | Path | Content |
|----------|------|---------|
| domains | `knowledge/domains/` | Business terminology, rules |
| technologies | `knowledge/technologies/` | Languages, frameworks, tools |
| patterns | `knowledge/patterns/` | Code patterns, architectures |
| errors | `knowledge/errors/` | Error → Solution pairs |
| apis | `knowledge/apis/` | External API docs |
| architecture | `knowledge/architecture/` | ADRs, decisions |
| projects | `knowledge/projects/` | Project learnings |

## Reading Knowledge

### Search All Knowledge

```bash
grep -r "search term" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/ --include="*.md"
```

### Search Specific Category

```bash
# Search errors
grep -r "ModuleNotFoundError" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/errors/

# Search technologies
grep -r "FastAPI" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/technologies/

# Search patterns
grep -r "singleton" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/patterns/
```

### List All Entries

```bash
find /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge -name "*.md" -type f | grep -v index.md
```

### Read Specific Entry

```bash
cat /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/[category]/[filename].md
```

## Writing Knowledge

### When to Write

Write to central KB when you discover:
- **Error solution** that might recur
- **API gotcha** (rate limits, encoding, auth)
- **Code pattern** that's reusable
- **Technology insight** (config, best practice)
- **Domain knowledge** (business rules)

### Entry Format

```markdown
# [Title]

**Category:** [category]
**Tags:** [tag1, tag2, tag3]
**Source:** [project-name]
**Created:** YYYY-MM-DD
**Confidence:** high | medium | low

## Summary
[1-2 sentence summary]

## Problem
[What was the issue - for errors]

## Solution
[How to fix/implement]

## Code Example
```[language]
[code]
```

## Gotchas
[Things to watch out for]

## Related
- [Links to related entries]

## References
- [External links]
```

### Writing Process

```bash
# 1. Navigate to knowledge repo
cd /c/Users/mpeck/PycharmProjects/Claude_Knowledge

# 2. Pull latest
git pull

# 3. Create entry file
cat > knowledge/[category]/[filename].md << 'EOF'
[content]
EOF

# 4. Commit and push
git add knowledge/
git commit -m "knowledge: [category] - [title]

Source: [project-name]
Tags: [tag1, tag2]"
git push
```

## Integration with Workflow

### At Session Start

```bash
# Check for relevant knowledge before starting work
echo "Searching central KB for relevant knowledge..."
grep -r "[project topic]" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/ --include="*.md" -l
```

### During Development

When encountering an error:
```bash
# 1. Search KB first
grep -r "[error message]" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/errors/

# 2. If found, apply solution
# 3. If not found, solve it, then add to KB
```

### At Session End

```bash
# Review what was learned this session
# If anything is reusable, add to central KB
```

## Gemini Integration

Before adding to central KB, optionally validate:

```bash
python scripts/gemini_consult.py "I want to add to central knowledge base:
Category: [X]
Title: [Y]
Content summary: [Z]

Is this worth preserving centrally? Any improvements?"
```

## Quick Commands

### Search
```bash
# Quick search alias
alias kbs='grep -r "$1" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/ --include="*.md"'

# Usage: kbs "FastAPI"
```

### Add Error
```bash
# Add new error entry
cat > /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/errors/[name].md << 'EOF'
# [Error Name]

**Category:** errors
**Source:** [project]
**Created:** [date]

## Error
```
[error message]
```

## Solution
[solution]

## Prevention
[how to avoid]
EOF
```

### Add Technology
```bash
cat > /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/technologies/[name].md << 'EOF'
# [Technology Name]

**Category:** technologies
**Source:** [project]
**Created:** [date]

## Overview
[what it is]

## Setup
```bash
[installation]
```

## Usage
```[language]
[code example]
```

## Gotchas
[common issues]
EOF
```

## Best Practices

1. **Search before adding** - avoid duplicates
2. **Be specific** - "FastAPI CORS setup" not "CORS"
3. **Include examples** - code speaks louder
4. **Tag properly** - helps with search
5. **Note the source** - which project discovered it
6. **Update existing** - if entry exists, enhance it
7. **Cross-reference** - link related entries

## GitHub Repository

The central KB should be a GitHub repo for:
- Version control
- Backup
- Access from anywhere
- Collaboration

```bash
# Initialize if not done
cd /c/Users/mpeck/PycharmProjects/Claude_Knowledge
git init
gh repo create Claude_Knowledge --public --source=. --remote=origin
git add .
git commit -m "Initial knowledge base setup"
git push -u origin master
```
