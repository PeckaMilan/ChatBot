# Documentation Skill

## Purpose

Maintain accurate, comprehensive documentation throughout autonomous development cycles. Documentation serves as the source of truth for project state, architecture decisions, and API contracts.

---

## Documentation Structure

### Required Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `README.md` | Project overview, setup, quick start | Each iteration |
| `docs/ARCHITECTURE.md` | System design, component relationships, decisions | Architecture changes |
| `docs/API.md` | Endpoints, functions, parameters, responses | API changes |
| `docs/CHANGELOG.md` | Version history, breaking changes | Each release |

### File Templates

#### README.md Structure

```markdown
# Project Name

Brief description (1-2 sentences).

## Status

Current iteration: [Koloběžka/Kolo/Motorka/Auto/Formule]
Version: X.Y.Z

## Quick Start

\`\`\`bash
# Installation
# Running
# Testing
\`\`\`

## Features

- Feature 1
- Feature 2

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Changelog](docs/CHANGELOG.md)
```

#### docs/ARCHITECTURE.md Structure

```markdown
# Architecture

## Overview

Brief system description with high-level diagram.

## Components

### Component Name

**Purpose**: What it does
**Location**: `path/to/component`
**Dependencies**: What it requires

## Data Flow

\`\`\`mermaid
flowchart LR
    A[Input] --> B[Process]
    B --> C[Output]
\`\`\`

## Design Decisions

### Decision Title

**Context**: Why the decision was needed
**Decision**: What was decided
**Consequences**: Impact of the decision
```

#### docs/API.md Structure

```markdown
# API Reference

## Endpoints / Functions

### `endpoint_or_function_name`

**Description**: What it does

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| param1 | string | Yes | Description |

**Returns**: Description of return value

**Example**:
\`\`\`python
# Usage example
result = function_name(param1="value")
\`\`\`

**Errors**:
| Code | Description |
|------|-------------|
| 400 | Invalid input |
```

#### docs/CHANGELOG.md Structure

```markdown
# Changelog

All notable changes documented here. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
### Changed
### Fixed
### Removed

## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description
```

---

## When to Update Documentation

### Iteration Transitions

| From | To | Documentation Actions |
|------|----|-----------------------|
| Start | Koloběžka | Create all doc files, document initial architecture |
| Koloběžka | Kolo | Update features, document expanded functionality |
| Kolo | Motorka | Document production patterns, deployment |
| Motorka | Auto | Document scaling, integrations |
| Auto | Formule | Document optimizations, advanced features |

### Trigger Events

Update documentation when:

1. **Architecture Changes**
   - New component added
   - Component removed or replaced
   - Data flow modified
   - External dependency added/removed

2. **API Changes**
   - New endpoint/function added
   - Parameters modified
   - Return type changed
   - Deprecation introduced

3. **Feature Completion**
   - New capability working
   - Behavior changed
   - Bug fixed that affects usage

4. **Configuration Changes**
   - Environment variables added
   - Config file format changed
   - Default values modified

---

## Documentation Conventions

### Mermaid Diagrams

Use Mermaid for all visual documentation:

```markdown
## System Overview

\`\`\`mermaid
flowchart TB
    subgraph Frontend
        UI[User Interface]
    end

    subgraph Backend
        API[API Layer]
        SVC[Services]
        DB[(Database)]
    end

    UI --> API
    API --> SVC
    SVC --> DB
\`\`\`
```

**Diagram Types**:
- `flowchart` - System architecture, data flow
- `sequenceDiagram` - API interactions, process flows
- `classDiagram` - Object relationships
- `erDiagram` - Database schema
- `stateDiagram-v2` - State machines

### Writing Style

1. **Be Concise**
   - One idea per paragraph
   - Use bullet points for lists
   - Avoid redundant explanations

2. **Include Examples**
   - Every API endpoint needs a usage example
   - Show both success and error cases
   - Use realistic data in examples

3. **Use Tables**
   - Parameters, configuration options
   - Error codes and meanings
   - Feature comparisons

4. **Link Related Content**
   - Cross-reference between docs
   - Link to source code when helpful
   - Reference external documentation

### Code Examples

Always include runnable examples:

```python
# Good - Complete, runnable example
from myproject import Client

client = Client(api_key="your-key")
result = client.process(data={"input": "value"})
print(result.output)  # Expected: "processed_value"
```

```python
# Bad - Incomplete, unclear
client.process(data)
```

---

## Gemini Integration for Validation

### Validation Workflow

Use Gemini to validate documentation accuracy:

```
1. After code changes, extract:
   - Modified functions/classes
   - Changed parameters
   - New/removed features

2. Send to Gemini for validation:
   - Compare code signatures with API.md
   - Check architecture diagrams match code structure
   - Verify examples still work

3. Generate discrepancy report:
   - Missing documentation
   - Outdated information
   - Incorrect examples
```

### Validation Prompt Template

```
Review the following code and documentation for accuracy:

## Code
{current_code}

## Documentation
{current_docs}

Check for:
1. Function signatures match documentation
2. All parameters documented
3. Return types accurate
4. Examples are valid
5. Architecture diagrams reflect actual structure

Report any discrepancies in format:
- [FILE]: [ISSUE]: [SUGGESTED FIX]
```

### Automated Checks

Before committing documentation:

1. **Syntax Validation**
   - Markdown renders correctly
   - Mermaid diagrams parse
   - Code blocks have language tags

2. **Link Validation**
   - Internal links resolve
   - External links accessible
   - File paths exist

3. **Content Validation**
   - API docs match code signatures
   - Examples execute without errors
   - Changelog has unreleased section

---

## Documentation Workflow

### During Development

```
1. Start task
2. Check existing documentation relevance
3. Make code changes
4. Update documentation inline:
   - API.md if signatures change
   - ARCHITECTURE.md if structure changes
5. Add CHANGELOG entry
6. Validate with Gemini
7. Commit code + docs together
```

### End of Iteration

```
1. Review all documentation files
2. Update README.md status
3. Move CHANGELOG [Unreleased] to version
4. Generate architecture diagram updates
5. Validate entire doc set with Gemini
6. Create iteration summary
```

### Documentation Commands

```bash
# Check markdown syntax
npx markdownlint docs/**/*.md

# Validate links
npx markdown-link-check docs/**/*.md

# Preview mermaid diagrams
npx @mermaid-js/mermaid-cli -i docs/ARCHITECTURE.md -o preview.html
```

---

## Quick Reference

### Documentation Checklist

- [ ] README.md reflects current state
- [ ] ARCHITECTURE.md diagrams are current
- [ ] API.md covers all public interfaces
- [ ] CHANGELOG.md has all changes
- [ ] Examples are tested and working
- [ ] Mermaid diagrams render correctly
- [ ] Cross-references are valid
- [ ] Gemini validation passed

### Common Patterns

**Adding a new feature**:
1. Add to CHANGELOG under [Unreleased] > Added
2. Document API in API.md
3. Update ARCHITECTURE.md if new component
4. Update README.md features list

**Fixing a bug**:
1. Add to CHANGELOG under [Unreleased] > Fixed
2. Update API.md if behavior changed
3. Add example showing correct behavior

**Breaking change**:
1. Add to CHANGELOG under [Unreleased] > Changed (mark BREAKING)
2. Update API.md with migration guide
3. Update all affected examples
4. Consider ARCHITECTURE.md update
