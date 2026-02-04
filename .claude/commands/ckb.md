# Central Knowledge Base Commands

Interact with the shared Claude_Knowledge repository.

## Location

```
C:\Users\mpeck\PycharmProjects\Claude_Knowledge\knowledge\
```

## Search

```bash
# Search all
grep -r "[query]" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/ --include="*.md"

# Search errors only
grep -r "[query]" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/errors/

# Search technologies
grep -r "[query]" /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/technologies/

# List all entries
find /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge -name "*.md" | grep -v index
```

## Read

```bash
cat /c/Users/mpeck/PycharmProjects/Claude_Knowledge/knowledge/[category]/[file].md
```

## Add Entry

```bash
# 1. Go to repo
cd /c/Users/mpeck/PycharmProjects/Claude_Knowledge

# 2. Create file
cat > knowledge/[category]/[name].md << 'EOF'
# [Title]

**Category:** [category]
**Tags:** [tags]
**Source:** [project]
**Created:** [date]

## Summary
[summary]

## Details
[details]

## Example
```
[code]
```
EOF

# 3. Commit
git add knowledge/ && git commit -m "knowledge: [category] - [title]" && git push
```

## Categories

| Short | Full Path | Use For |
|-------|-----------|---------|
| `err` | errors/ | Error solutions |
| `tech` | technologies/ | Tech stack |
| `pat` | patterns/ | Code patterns |
| `api` | apis/ | External APIs |
| `dom` | domains/ | Business knowledge |
| `arch` | architecture/ | ADRs |
| `proj` | projects/ | Project specifics |

## Quick Add Templates

### Error
```bash
/ckb add error [name]
```

### Technology
```bash
/ckb add tech [name]
```

### Pattern
```bash
/ckb add pattern [name]
```

### API
```bash
/ckb add api [name]
```
