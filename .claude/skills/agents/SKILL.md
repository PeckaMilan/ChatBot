---
name: agents
description: Multi-agent orchestration for autonomous development. Use when tasks can be parallelized, require specialized expertise, or need isolated execution. Defines when and how to spawn sub-agents.
user-invocable: false
---

# Sub-Agent Orchestration

Guidelines for using multiple agents in autonomous development.

## Available Agent Types

| Type | Purpose | Tools | Best For |
|------|---------|-------|----------|
| `Explore` | Codebase search & analysis | Read, Glob, Grep | Finding files, understanding code |
| `Plan` | Architecture & planning | Read, Glob, Grep | Designing solutions |
| `Bash` | Command execution | Bash only | Git, npm, builds, tests |
| `general-purpose` | Complex multi-step tasks | All tools | Research, implementation |

## When to Use Sub-Agents

### ✅ USE Agents For:

**1. Parallel Independent Tasks**
```
Example: Need to understand 3 different modules
→ Spawn 3 Explore agents in parallel
→ Each investigates one module
→ Collect results
```

**2. Isolated Execution**
```
Example: Run risky command that might fail
→ Spawn Bash agent
→ If fails, main context not polluted
```

**3. Specialized Research**
```
Example: Need architecture analysis + code search + web research
→ Spawn Plan agent for architecture
→ Spawn Explore agent for code
→ Spawn general-purpose for web
→ All run in parallel
```

**4. Long-Running Tasks**
```
Example: Build and test takes 5 minutes
→ Spawn Bash agent with run_in_background=true
→ Continue other work
→ Check results later
```

### ❌ DON'T USE Agents For:

- Simple file reads (use Read directly)
- Single grep/glob (use tools directly)
- Tasks requiring conversation context
- Sequential dependent operations

## Parallel Execution Pattern

When tasks are independent, spawn ALL agents in ONE message:

```
┌─────────────────────────────────────────────────────────┐
│ GOOD: Single message, multiple agents                   │
│                                                         │
│ Task 1: Explore ──┐                                     │
│ Task 2: Explore ──┼──► All spawn simultaneously         │
│ Task 3: Bash    ──┘                                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ BAD: Sequential messages                                │
│                                                         │
│ Message 1: Task 1 → wait → result                       │
│ Message 2: Task 2 → wait → result                       │
│ Message 3: Task 3 → wait → result                       │
│                                                         │
│ (3x slower!)                                            │
└─────────────────────────────────────────────────────────┘
```

## Agent Patterns

### Pattern 1: Parallel Research

Use when exploring unfamiliar codebase:

```python
# Spawn 3 agents in parallel:
Agent 1 (Explore): "Find all API endpoints in this codebase"
Agent 2 (Explore): "Find database models and schemas"
Agent 3 (Explore): "Find configuration and environment handling"
```

### Pattern 2: Scout Before Implement

Use before major changes:

```python
# First: Scout with Explore agent
Agent (Explore): "Find all files that import UserService"

# Then: Based on results, implement changes
# (Don't spawn agent for implementation - do it directly)
```

### Pattern 3: Parallel Build & Test

Use for CI-like workflows:

```python
# Spawn in parallel:
Agent 1 (Bash): "npm run lint"
Agent 2 (Bash): "npm run typecheck"
Agent 3 (Bash): "npm run test"

# All run simultaneously, collect all results
```

### Pattern 4: Background Long Task

Use for slow operations:

```python
# Start in background:
Agent (Bash, background=true): "npm run build"

# Continue other work...
# Later, check results with TaskOutput
```

### Pattern 5: Research + Validate

Use with Gemini integration:

```python
# Step 1: Parallel research
Agent 1 (Explore): "Find authentication implementation"
Agent 2 (general-purpose): "Search web for OAuth2 best practices 2024"

# Step 2: Validate with Gemini
python scripts/gemini_consult.py "Based on research: [results]. I propose [solution]. Validate."
```

## Agent Communication

### Prompt Guidelines

**Be Specific:**
```
❌ "Look at the code"
✅ "Find all files in src/ that contain 'async function' and list their exports"
```

**Include Context:**
```
❌ "Fix the bug"
✅ "In src/api/users.ts, the getUserById function throws on null. Find similar patterns and suggest fix."
```

**Define Output:**
```
❌ "Research authentication"
✅ "Research JWT vs session auth. Return: pros/cons table, recommendation, implementation steps."
```

### Collecting Results

After parallel agents complete:
1. Read each agent's output
2. Synthesize findings
3. Consult Gemini if needed
4. Proceed with implementation

## Integration with Workflow

### During /start

```python
# Parallel context gathering:
Agent 1 (Explore): "Summarize recent changes in git log"
Agent 2 (Explore): "Find TODO comments in codebase"
Agent 3 (Bash): "Run tests to verify baseline"
```

### During Implementation

```python
# Before changing shared code:
Agent (Explore): "Find all usages of [function] I'm about to modify"

# Parallel implementation (if truly independent):
Agent 1 (general-purpose): "Implement feature A in module X"
Agent 2 (general-purpose): "Implement feature B in module Y"
```

### During /finish

```python
# Parallel checks:
Agent 1 (Bash): "Run full test suite"
Agent 2 (Bash): "Run linter"
Agent 3 (Explore): "Check for TODO/FIXME added this session"
```

## Gemini + Agents

Combine sub-agents with Gemini consultation:

```
┌─────────────────────────────────────────────────────────┐
│  1. Spawn research agents (parallel)                    │
│     └─► Explore: codebase analysis                      │
│     └─► general-purpose: web research                   │
│                                                         │
│  2. Collect results                                     │
│                                                         │
│  3. Consult Gemini                                      │
│     "Research found [X]. I propose [Y]. Approve?"       │
│     └─► APPROVED → implement                            │
│     └─► REVISE → adjust                                 │
│     └─► ESCALATE → ask human                            │
│                                                         │
│  4. Implement (directly, not via agent)                 │
└─────────────────────────────────────────────────────────┘
```

## Limits & Constraints

| Constraint | Value |
|------------|-------|
| Max concurrent agents | 10 |
| Agent token overhead | ~20k tokens |
| Agent cannot spawn agents | ❌ No nesting |
| Agent context | Isolated (200k tokens) |

## Quick Reference

### Spawn Parallel Agents
```
Use Task tool multiple times in ONE response
Each with different subagent_type
```

### Background Agent
```
Task tool with run_in_background=true
Check with TaskOutput later
```

### Resume Agent
```
Task tool with resume=[agent_id]
Continues previous context
```

## Decision Tree

```
Need to do something?
│
├─► Simple read/search?
│   └─► Use Read/Glob/Grep directly
│
├─► Multiple independent tasks?
│   └─► Spawn parallel agents
│
├─► Long-running command?
│   └─► Background Bash agent
│
├─► Need codebase understanding?
│   └─► Explore agent
│
├─► Need architecture decision?
│   └─► Plan agent + Gemini consult
│
└─► Complex multi-step?
    └─► general-purpose agent
```
