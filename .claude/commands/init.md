# Initialize New Project

Complete project setup from Claude_Max template.

## What This Does

1. ✅ Clone template structure from Claude_Max
2. ✅ Copy secrets from local storage
3. ✅ Create GitHub repo (same name as folder)
4. ✅ Initial commit & push
5. ✅ Start business discovery

## Prerequisites

- Template repo: `C:\Users\mpeck\PycharmProjects\Claude_Max`
- Secrets: `~/.claude/secrets/.env`
- `gh` CLI installed

---

## Phase 1: Project Setup

### Step 1.1: Clone Template Structure

Copy essential files from Claude_Max template:

```bash
TEMPLATE_DIR="/c/Users/mpeck/PycharmProjects/Claude_Max"
PROJECT_NAME=$(basename "$(pwd)")

echo "🚀 Initializing project: $PROJECT_NAME"
echo "📦 Template: Claude_Max"
echo ""

# Copy .claude directory (skills, commands)
if [ ! -d ".claude" ]; then
    cp -r "$TEMPLATE_DIR/.claude" .
    echo "✅ Copied .claude/ (skills, commands)"
fi

# Copy scripts
if [ ! -d "scripts" ]; then
    cp -r "$TEMPLATE_DIR/scripts" .
    echo "✅ Copied scripts/"
fi

# Copy CLAUDE.md template
if [ ! -f "CLAUDE.md" ]; then
    cp "$TEMPLATE_DIR/CLAUDE.md" .
    echo "✅ Copied CLAUDE.md"
fi

# Copy .gitignore
if [ ! -f ".gitignore" ]; then
    cp "$TEMPLATE_DIR/.gitignore" .
    echo "✅ Copied .gitignore"
fi
```

### Step 1.2: Copy Secrets

```bash
SECRETS_DIR="$HOME/.claude/secrets"

# Copy .env if exists
if [ -f "$SECRETS_DIR/.env" ]; then
    cp "$SECRETS_DIR/.env" .env
    echo "✅ Copied .env from $SECRETS_DIR"
else
    echo "⚠️ No secrets found at $SECRETS_DIR/.env"
    echo "   Create manually or copy from another project"
fi
```

### Step 1.3: Update Project Name in CLAUDE.md

```bash
# Update CLAUDE.md with project name
sed -i "s/Claude_Max/$PROJECT_NAME/g" CLAUDE.md 2>/dev/null || true
echo "✅ Updated CLAUDE.md with project name"
```

### Step 1.4: Clean Template State

```bash
# Remove template's gemini session (start fresh)
rm -f .claude/gemini_session.json 2>/dev/null

# Reset BUSINESS.md to template state
cat > .claude/BUSINESS.md << 'EOF'
# Business Requirements

## Status: DISCOVERY

> This document is created collaboratively by Human + Claude + Gemini

---

## Vision
*What are we building and why?*

[To be defined in discovery session]

## Problem Statement
*What problem does this solve?*

[To be defined]

## Target Users
*Who is this for?*

[To be defined]

## Success Criteria
*How do we know it works?*

[To be defined]

## Constraints
*Budget, time, technology limitations?*

[To be defined]

## Out of Scope
*What are we explicitly NOT doing?*

[To be defined]

---

## Iterations (Agile Roadmap)

### 🛴 Koloběžka (MVP)
- [ ] [Core feature 1]
- [ ] [Core feature 2]

### 🚲 Kolo
- [ ] [Enhancement 1]
- [ ] [Enhancement 2]

### 🏍️ Motorka
- [ ] [Optimization 1]
- [ ] [Optimization 2]

### 🚗 Auto
- [ ] [Production feature 1]
- [ ] [Production feature 2]

### ✈️ Letadlo
- [ ] [Scale feature 1]
- [ ] [Scale feature 2]

---

## Sign-off

- [ ] Human approved
- [ ] Ready for technical planning
EOF

# Reset PLAN.md
cat > .claude/PLAN.md << 'EOF'
# Technical Plan

## Status: AWAITING BUSINESS REQUIREMENTS

> Created AFTER business requirements are approved.

---

## Current Iteration: [Not Started]

## Architecture
[To be defined]

## Tech Stack
[To be defined]

## Tasks

### In Progress
- [ ] None

### Completed
- [x] Project initialized

---

## Escalation Log

| Date | Issue | Decision |
|------|-------|----------|
EOF

echo "✅ Reset BUSINESS.md and PLAN.md"
```

---

## Phase 2: Git & GitHub

```bash
PROJECT_NAME=$(basename "$(pwd)")
export GH_TOKEN=$(grep GIT_TOKEN .env | cut -d'=' -f2)

# Initialize git
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git initialized"
fi

# Create GitHub repo
gh repo create $PROJECT_NAME --public --description "Autonomous development project" --source=. --remote=origin 2>/dev/null && echo "✅ GitHub repo created: $PROJECT_NAME" || echo "ℹ️ Repo may already exist"

# Initial commit
git add .
git commit -m "Initial commit: $PROJECT_NAME from Claude_Max template

Includes:
- Autonomous workflow (Claude + Gemini)
- Skills: consult, git
- Commands: init, plan, start, finish

Co-Authored-By: Claude <noreply@anthropic.com>" 2>/dev/null || echo "ℹ️ Nothing new to commit"

# Push
git push -u origin master 2>/dev/null || git push -u origin main 2>/dev/null || echo "ℹ️ Already pushed"

echo ""
echo "📦 Repository ready!"
echo ""
```

---

## Phase 3: Business Discovery

After setup, start collaborative discovery with Human + Claude + Gemini.

### Your Role (Claude)

Facilitate the discovery session:
1. **Ask clarifying questions** about the project
2. **Consult Gemini** for critical evaluation
3. **Document in** `.claude/BUSINESS.md`

### Discovery Questions

**Vision:**
- "What do you want to build?"
- "What problem does it solve?"
- "Who is it for?"

After each answer, consult Gemini:
```bash
python scripts/gemini_consult.py --no-plan "Business discovery: [context]. Evaluate and suggest clarifying questions."
```

### Define Iterations

| Iteration | Question |
|-----------|----------|
| 🛴 Koloběžka | What's the absolute minimum? |
| 🚲 Kolo | What makes it useful? |
| 🏍️ Motorka | What makes it powerful? |
| 🚗 Auto | What's production-ready? |
| ✈️ Letadlo | What's enterprise scale? |

### Finalize

1. Update `.claude/BUSINESS.md`
2. Read back to human for approval
3. Check "Human approved" box
4. Tell human: "Run `/plan` to create technical plan"

---

## Start Now

Run all Phase 1 and Phase 2 commands, then begin:

"Project initialized from Claude_Max template!

**Git:** ✅ Ready
**GitHub:** ✅ https://github.com/[user]/[project]
**Secrets:** ✅ Copied

Now let's define what we're building. I'll facilitate, Gemini will challenge, you decide.

**What do you want to build?**"

---

## Secrets Location

Secrets are stored at: `~/.claude/secrets/.env`

To update secrets for all future projects:
```bash
cp .env ~/.claude/secrets/.env
```

Required keys:
- `GIT_TOKEN` - GitHub personal access token
- `GOOGLE_API_KEY` - Gemini API key
- (optional) `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
