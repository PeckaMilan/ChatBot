# Knowledge Base Commands

Manage project knowledge base.

## Initialize Knowledge Base

```bash
mkdir -p .claude/knowledge/{domain,technical,gotchas,apis,architecture/decisions}

# Create index
cat > .claude/knowledge/index.md << 'EOF'
# Knowledge Base Index

**Project:** [Project Name]
**Last Updated:** [Date]
**Total Entries:** 0

## Quick Links

### Domain
_No entries yet_

### Technical
_No entries yet_

### Gotchas
_No entries yet_

### APIs
_No entries yet_

### Architecture
_No entries yet_

## Recently Added
_No entries yet_
EOF

echo "Knowledge base initialized"
```

## Add Entry

### Domain Knowledge

```bash
cat > .claude/knowledge/domain/[topic].md << 'EOF'
# [Topic Title]

**Category:** domain
**Created:** [Date]
**Confidence:** medium
**Source:** discovered

## Summary
[1-2 sentences]

## Details
[Full explanation]

## Examples
[Examples if applicable]

## Related
- [Links to related entries]
EOF
```

### Technical Knowledge

```bash
cat > .claude/knowledge/technical/[topic].md << 'EOF'
# [Topic Title]

**Category:** technical
**Created:** [Date]
**Confidence:** medium

## Summary
[1-2 sentences]

## Details
[Technical explanation]

## Code Example
```[language]
[code]
```

## Related
- [Links]
EOF
```

### Gotcha Entry

```bash
cat > .claude/knowledge/gotchas/[topic].md << 'EOF'
# [Problem Title]

**Category:** gotcha
**Created:** [Date]
**Confidence:** high

## Problem
[What goes wrong]

## Symptoms
- [Symptom 1]
- [Symptom 2]

## Solution
```[language]
[fix code]
```

## Prevention
[How to avoid in future]
EOF
```

### API Documentation

```bash
cat > .claude/knowledge/apis/[api-name].md << 'EOF'
# [API Name]

**Category:** api
**Created:** [Date]
**Base URL:** [URL]

## Authentication
[Auth method and setup]

## Endpoints

### [Endpoint 1]
- **Method:** GET/POST
- **Path:** /path
- **Parameters:** [params]
- **Response:** [format]

## Rate Limits
[Limits if any]

## Gotchas
[Known issues]
EOF
```

### Architecture Decision Record (ADR)

```bash
# Get next ADR number
NEXT_NUM=$(ls .claude/knowledge/architecture/decisions/ADR-*.md 2>/dev/null | wc -l)
NEXT_NUM=$((NEXT_NUM + 1))
NUM=$(printf "%03d" $NEXT_NUM)

cat > .claude/knowledge/architecture/decisions/ADR-${NUM}-[title].md << 'EOF'
# ADR-[NUM]: [Decision Title]

**Status:** proposed | accepted | deprecated | superseded
**Date:** [Date]
**Deciders:** [Who decided]

## Context
[Why this decision was needed]

## Decision
[What was decided]

## Consequences

### Positive
- [Pro 1]
- [Pro 2]

### Negative
- [Con 1]
- [Con 2]

## Alternatives Considered
1. [Alternative 1] - [Why rejected]
2. [Alternative 2] - [Why rejected]
EOF
```

## Search Knowledge

```bash
# Search all knowledge
grep -r "[query]" .claude/knowledge/ --include="*.md"

# Search specific category
grep -r "[query]" .claude/knowledge/domain/ --include="*.md"

# List all entries
find .claude/knowledge -name "*.md" -type f | grep -v index.md
```

## Update Index

```bash
# Count entries per category
echo "# Knowledge Base Index" > .claude/knowledge/index.md
echo "" >> .claude/knowledge/index.md
echo "**Last Updated:** $(date +%Y-%m-%d)" >> .claude/knowledge/index.md
echo "" >> .claude/knowledge/index.md

for category in domain technical gotchas apis architecture; do
    count=$(find .claude/knowledge/$category -name "*.md" 2>/dev/null | wc -l)
    echo "### $category ($count entries)" >> .claude/knowledge/index.md

    for file in .claude/knowledge/$category/*.md; do
        if [ -f "$file" ]; then
            title=$(head -1 "$file" | sed 's/# //')
            echo "- [$title]($category/$(basename $file))" >> .claude/knowledge/index.md
        fi
    done
    echo "" >> .claude/knowledge/index.md
done

echo "Index updated"
```

## Gemini Integration

### Validate Before Adding

```bash
python scripts/gemini_consult.py "I want to add to knowledge base:
Category: [category]
Title: [title]
Content: [brief content]

Worth preserving? Corrections needed?"
```

### Query Knowledge

```bash
python scripts/gemini_consult.py "What do we know about [TOPIC]? Check .claude/knowledge/ for context."
```

## Quick Reference

| Action | Command |
|--------|---------|
| Init KB | `/kb init` |
| Add domain | `/kb add domain [title]` |
| Add technical | `/kb add tech [title]` |
| Add gotcha | `/kb add gotcha [title]` |
| Add API | `/kb add api [name]` |
| Add ADR | `/kb add adr [title]` |
| Search | `/kb search [query]` |
| List all | `/kb list` |
| Update index | `/kb index` |
