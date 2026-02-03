---
name: git
description: Git workflow for autonomous development. Auto-creates GitHub repo matching project folder name. Use at project start or for git operations.
user-invocable: true
---

# Git Workflow Skill

Manages Git operations for autonomous Claude + Gemini development.

## Project Initialization

When starting a new project, automatically:
1. Initialize git repo
2. Create GitHub repo with same name as project folder
3. Setup .gitignore
4. Initial commit and push

### Auto-Setup Command

```bash
# Get project name from current directory
PROJECT_NAME=$(basename "$(pwd)")

# Get GitHub token from .env
export GH_TOKEN=$(grep GIT_TOKEN .env | cut -d'=' -f2)

# Initialize git if not already
git init

# Create GitHub repo (public, same name as folder)
gh repo create $PROJECT_NAME --public --description "Autonomous development project" --source=. --remote=origin

# Initial commit
git add .
git commit -m "Initial commit: Project setup

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>"

# Push
git push -u origin master
```

## Standard .gitignore

Always include these entries:

```gitignore
# Python
*.pyc
*.pyo
__pycache__/
venv/
.venv/
.env

# IDE
.idea/
.vscode/

# OS
.DS_Store
Thumbs.db

# Credentials
*.key
*.pem
secrets.*
credentials.*

# Claude session (conversation history is local)
.claude/gemini_session.json
```

## Commit Conventions

### Format
```
<type>: <short description>

<optional body>

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>
```

### Types
| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructure |
| `docs` | Documentation |
| `chore` | Maintenance |
| `iter` | Iteration milestone (🛴🚲🏍️🚗✈️) |

### Examples
```bash
# Feature
git commit -m "feat: add user authentication

Co-Authored-By: Claude <noreply@anthropic.com>"

# Iteration complete
git commit -m "iter: 🛴 Koloběžka complete - MVP working

- Basic functionality implemented
- Core features operational

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>"
```

## Workflow Commands

### Before Work
```bash
git pull origin master
```

### After Task Complete
```bash
# Stage changes
git add <specific-files>

# Commit with message
git commit -m "type: description

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push
```

### Iteration Milestone
When completing an iteration (Koloběžka → Kolo, etc.):
```bash
git add .
git commit -m "iter: [emoji] [iteration] complete

Summary of what's working:
- Feature 1
- Feature 2

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Gemini <noreply@google.com>"

git tag -a v0.1-kolob -m "Koloběžka MVP"
git push --tags
```

## Git + Gemini Integration

Before commits, consult Gemini:
```bash
python scripts/gemini_consult.py "Ready to commit: [summary of changes]. Approve?"
```

Gemini responses:
- `APPROVED` → proceed with commit
- `REVISE` → adjust changes first
- `ESCALATE` → ask human (e.g., breaking changes)

## Branching (Optional)

For larger iterations:
```bash
# Create iteration branch
git checkout -b iter/kolo

# Work on iteration...

# Merge when complete
git checkout master
git merge iter/kolo
git push
```

## Emergency Commands

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard all local changes
git checkout .

# Force sync with remote
git fetch origin
git reset --hard origin/master
```

## GitHub Token

Token is stored in `.env`:
```
GIT_TOKEN=ghp_xxxxxxxxxxxxx
```

Required scopes: `repo`, `workflow`

Get token: https://github.com/settings/tokens
