# Multi-Agent Operations

Orchestrate multiple sub-agents for parallel or specialized tasks.

## Quick Patterns

### Parallel Codebase Exploration

When you need to understand multiple parts of codebase:

```
Spawn in ONE message:

Agent 1 (Explore): "Find and summarize all API routes in src/api/"
Agent 2 (Explore): "Find and summarize all database models in src/models/"
Agent 3 (Explore): "Find and summarize all utility functions in src/utils/"
```

### Parallel Quality Checks

Before commit or at session end:

```
Spawn in ONE message:

Agent 1 (Bash): "Run tests: pytest -v" or "npm test"
Agent 2 (Bash): "Run linter: ruff check ." or "npm run lint"
Agent 3 (Bash): "Run type check: mypy ." or "npm run typecheck"
```

### Research Before Implementation

When planning a feature:

```
Spawn in ONE message:

Agent 1 (Explore): "Find existing implementation patterns for [feature type]"
Agent 2 (Plan): "Analyze architecture impact of adding [feature]"
Agent 3 (general-purpose): "Search web for best practices: [technology] [feature] 2024"
```

### Background Build

For long-running tasks:

```
Spawn with background=true:

Agent (Bash, background): "npm run build"

Continue working on other tasks...

Later: Check with TaskOutput
```

## When to Use

| Situation | Agent Type | Parallel? |
|-----------|------------|-----------|
| Find files/code | Explore | ✅ Yes |
| Run commands | Bash | ✅ Yes |
| Web research | general-purpose | ✅ Yes |
| Architecture analysis | Plan | ✅ Yes |
| Long build/test | Bash (background) | N/A |
| Implementation | Direct (no agent) | N/A |

## Integration with Gemini

After collecting agent results:

```bash
python scripts/gemini_consult.py "Research complete. Findings:
- Agent 1: [summary]
- Agent 2: [summary]
- Agent 3: [summary]

I propose: [approach]. Approve?"
```

## Tips

1. **Always parallel when possible** - spawn all independent agents in ONE message
2. **Be specific in prompts** - agents work better with clear instructions
3. **Don't over-use** - simple tasks don't need agents
4. **Collect and synthesize** - combine results before acting
5. **Consult Gemini** - validate findings before implementation
