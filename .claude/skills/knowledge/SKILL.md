---
name: knowledge
description: Build and maintain a knowledge base about the project domain. Automatically captures learnings, technical decisions, domain concepts, and gotchas. Use when working on complex domains to preserve context across sessions.
user-invocable: true
---

# Knowledge Base System

Automatically build domain knowledge while working on projects.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE BASE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  .claude/knowledge/                                         │
│  ├── domain/           # Domain concepts & terminology      │
│  ├── technical/        # Technical decisions & patterns     │
│  ├── gotchas/          # Pitfalls & solutions              │
│  ├── apis/             # External APIs & integrations      │
│  ├── architecture/     # System design knowledge           │
│  └── index.md          # Quick reference index             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## What Gets Captured

### Domain Knowledge
- Business terminology and definitions
- Domain rules and constraints
- Industry-specific concepts
- Stakeholder requirements

### Technical Knowledge
- Architecture decisions (ADRs)
- Technology choices and rationale
- Integration patterns
- Performance characteristics

### Gotchas & Solutions
- Common errors and fixes
- Workarounds for known issues
- Edge cases discovered
- Debugging techniques

### API Knowledge
- External API endpoints
- Authentication methods
- Rate limits and quotas
- Response formats

## Knowledge Entry Format

```markdown
# [Topic Title]

**Category:** domain | technical | gotcha | api | architecture
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD
**Confidence:** high | medium | low
**Source:** discovered | documented | external

## Summary
[1-2 sentence summary]

## Details
[Full explanation]

## Examples
[Code or usage examples]

## Related
- [Link to related knowledge]

## References
- [External links or sources]
```

## Automatic Capture Triggers

### When to Capture

| Trigger | What to Capture | Category |
|---------|-----------------|----------|
| New domain term explained | Term + definition | domain |
| Architecture decision made | Decision + rationale | architecture |
| External API integrated | Endpoint + auth + format | api |
| Bug fixed after research | Problem + solution | gotcha |
| Performance issue solved | Issue + optimization | technical |
| User explains business rule | Rule + constraints | domain |

### Capture Process

1. **Detect** knowledge-worthy information
2. **Extract** key details
3. **Validate** with Gemini (optional)
4. **Store** in appropriate category
5. **Index** for quick retrieval

## Integration with Workflow

### During /start

```bash
# Load relevant knowledge
echo "Loading knowledge base..."
ls .claude/knowledge/

# Show recent additions
echo "Recent knowledge:"
find .claude/knowledge -name "*.md" -mtime -7
```

### During Work

When encountering new knowledge:

```bash
# Consult Gemini about capturing
python scripts/gemini_consult.py "I learned: [TOPIC]. Should I add this to knowledge base? Category suggestion?"
```

### During /finish

```bash
# Review knowledge added this session
echo "Knowledge captured this session:"
git diff --name-only .claude/knowledge/
```

## Commands

### Add Knowledge Entry

```bash
/kb add [category] [title]
```

Creates new knowledge entry in appropriate category.

### Search Knowledge

```bash
/kb search [query]
```

Searches across all knowledge entries.

### List Knowledge

```bash
/kb list [category]
```

Lists all entries, optionally filtered by category.

### Update Index

```bash
/kb index
```

Regenerates the quick reference index.

## Storage Structure

```
.claude/knowledge/
├── index.md                    # Quick reference index
│
├── domain/
│   ├── terminology.md          # Business terms
│   ├── business-rules.md       # Domain rules
│   └── [topic].md
│
├── technical/
│   ├── stack.md               # Technology stack
│   ├── patterns.md            # Code patterns used
│   └── [topic].md
│
├── gotchas/
│   ├── common-errors.md       # Error → solution map
│   ├── workarounds.md         # Known workarounds
│   └── [topic].md
│
├── apis/
│   ├── [api-name].md          # Per-API documentation
│   └── integrations.md        # Integration overview
│
└── architecture/
    ├── decisions/
    │   └── ADR-001-[title].md # Architecture Decision Records
    ├── diagrams.md            # System diagrams
    └── components.md          # Component overview
```

## Index Format

```markdown
# Knowledge Base Index

**Project:** [Project Name]
**Last Updated:** YYYY-MM-DD
**Total Entries:** N

## Quick Links

### Domain (N entries)
- [Term 1](domain/term1.md) - Brief description
- [Term 2](domain/term2.md) - Brief description

### Technical (N entries)
- [Pattern 1](technical/pattern1.md) - Brief description

### Gotchas (N entries)
- [Error X](gotchas/error-x.md) - Solution summary

### APIs (N entries)
- [API Name](apis/api-name.md) - What it does

### Architecture (N entries)
- [ADR-001](architecture/decisions/ADR-001.md) - Decision title

## Recently Added
1. [Entry] - Date
2. [Entry] - Date

## Most Referenced
1. [Entry] - N references
2. [Entry] - N references
```

## Gemini Integration

### Validate New Knowledge

```bash
python scripts/gemini_consult.py "Adding to knowledge base:
Category: [X]
Title: [Y]
Content: [Z]

Is this worth preserving? Any corrections?"
```

### Query Knowledge via Gemini

```bash
python scripts/gemini_consult.py "Based on our knowledge base, what do we know about [TOPIC]? Check .claude/knowledge/"
```

## Best Practices

### For Claude

1. **Capture proactively** - Don't wait to be asked
2. **Be concise** - Summaries, not essays
3. **Link related** - Connect knowledge entries
4. **Update confidence** - Mark uncertain knowledge
5. **Cite sources** - Note where info came from

### For Human

1. **Explain domain terms** - Claude will capture them
2. **State decisions explicitly** - "We decided X because Y"
3. **Share gotchas** - "Watch out for X"
4. **Review periodically** - `/kb list` to prune outdated

## Example Entries

### Domain Example

```markdown
# MEV (Maximal Extractable Value)

**Category:** domain
**Confidence:** high
**Source:** discovered

## Summary
Profit extracted by reordering, inserting, or censoring transactions.

## Details
MEV refers to the maximum value that can be extracted from block
production beyond standard block rewards and gas fees.

Types:
- Arbitrage
- Liquidations
- Sandwich attacks

## Related
- [Flashloans](flashloans.md)
- [DEX Integration](../apis/uniswap.md)
```

### Gotcha Example

```markdown
# Windows-1250 Encoding on Czech Government Sites

**Category:** gotcha
**Confidence:** high
**Source:** discovered (PSP.cz scraping)

## Summary
Czech government sites return Windows-1250, not UTF-8.

## Solution
```javascript
const decoder = new TextDecoder('windows-1250');
const text = decoder.decode(buffer);
```

## Affected APIs
- PSP.cz (Parliament)
- vlada.gov.cz
- Most Czech government portals
```

## Session Integration

Knowledge base is automatically:
- **Loaded** at session start (recent entries shown)
- **Updated** during work (when new knowledge discovered)
- **Indexed** at session end (index regenerated)
- **Committed** with other changes (versioned in git)
