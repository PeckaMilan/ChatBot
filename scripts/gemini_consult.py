"""
Gemini 3.0 Autonomous Development Partner
=========================================
Gemini acts as a human proxy - approving Claude's work when it aligns with the plan,
escalating to the human only when deviating from the plan.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google import genai
from google.genai import types

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
HISTORY_FILE = PROJECT_ROOT / ".claude" / "gemini_session.json"
PLAN_FILE = PROJECT_ROOT / ".claude" / "PLAN.md"
MODEL_NAME = "gemini-2.0-flash"

# System instruction for Gemini as Human Proxy
SYSTEM_INSTRUCTION = """You are the HUMAN PROXY for an autonomous development system.

## Your Role
You represent the human user. Claude Code (the developer) consults you before and after implementations.
The human has delegated 90% of decisions to you. They only want to be contacted for PLAN DEVIATIONS.

## The Current Plan
You will receive the current plan in each message. Your job is to:
1. APPROVE anything that aligns with the plan
2. Give FEEDBACK to improve implementation details
3. ESCALATE only when Claude wants to deviate from the plan

## Response Format

For approvals (most common):
```
APPROVED

[Brief acknowledgment or minor suggestions]
```

For feedback/revisions needed:
```
REVISE

[Specific feedback on what to change]
[Stay within the plan scope]
```

For plan deviations ONLY:
```
ESCALATE

[Explain why this deviates from the plan]
[What decision the human needs to make]
```

## Guidelines
- Be a supportive tech lead, not a blocker
- Minor implementation details = your decision (APPROVE or REVISE)
- Architecture changes not in plan = ESCALATE
- New dependencies not in plan = ESCALATE
- Scope expansion = ESCALATE
- Bug fixes and refactoring within scope = APPROVE
- Performance improvements within scope = APPROVE

## Remember
- You have full conversation history - maintain context
- The human trusts you to make good decisions
- Only ESCALATE for genuine plan deviations
- Keep responses concise and actionable
"""


def load_plan() -> str:
    """Load current plan from PLAN.md"""
    if PLAN_FILE.exists():
        return PLAN_FILE.read_text(encoding="utf-8")
    return "NO PLAN DEFINED - Ask the human to create a plan first."


def load_history() -> list:
    """Load conversation history from file."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("history", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history: list):
    """Save conversation history to file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_updated": datetime.now().isoformat(),
        "model": MODEL_NAME,
        "history": history
    }
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def history_to_contents(history: list) -> list:
    """Convert saved history to Content objects for API."""
    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )
    return contents


def consult(question: str, include_plan: bool = True) -> str:
    """Send a consultation request to Gemini with plan context."""

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "ERROR: GOOGLE_API_KEY not found in environment variables"

    client = genai.Client(api_key=api_key)

    # Load existing history
    history = load_history()

    # Build the message with plan context
    if include_plan:
        plan = load_plan()
        full_message = f"""## CURRENT PLAN
```
{plan}
```

## CLAUDE'S REQUEST
{question}"""
    else:
        full_message = question

    # Build contents with history + new question
    contents = history_to_contents(history)
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=full_message)]
        )
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.4,  # Lower for more consistent decisions
                max_output_tokens=2048
            )
        )

        response_text = response.text

        # Update history (store without plan to save space)
        history.append({"role": "user", "text": question})
        history.append({"role": "model", "text": response_text})
        save_history(history)

        return response_text

    except Exception as e:
        return f"ERROR: Gemini API call failed: {str(e)}"


def clear_history():
    """Clear conversation history (start fresh session)."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
        print("Session history cleared.")
    else:
        print("No history to clear.")


def show_history():
    """Display current conversation history summary."""
    history = load_history()
    if not history:
        print("No conversation history yet.")
        return

    print(f"Session has {len(history)} messages:\n")
    for i, msg in enumerate(history):
        role = msg.get("role", "unknown")
        text = msg.get("text", "")[:200]
        marker = "CLAUDE:" if role == "user" else "GEMINI:"
        print(f"[{i+1}] {marker}")
        print(f"    {text}...")
        print()


def show_plan():
    """Display current plan."""
    plan = load_plan()
    print("=== CURRENT PLAN ===\n")
    print(plan)


def main():
    if len(sys.argv) < 2:
        print("Gemini Autonomous Development Partner")
        print("=" * 40)
        print("\nUsage:")
        print("  python gemini_consult.py <message>   - Consult with Gemini")
        print("  python gemini_consult.py --plan      - Show current plan")
        print("  python gemini_consult.py --history   - Show session history")
        print("  python gemini_consult.py --clear     - Clear session history")
        print("  python gemini_consult.py --no-plan <msg> - Consult without plan context")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--clear":
        clear_history()
    elif arg == "--history":
        show_history()
    elif arg == "--plan":
        show_plan()
    elif arg == "--no-plan":
        question = " ".join(sys.argv[2:])
        result = consult(question, include_plan=False)
        print(result)
    else:
        question = " ".join(sys.argv[1:])
        result = consult(question)
        print(result)


if __name__ == "__main__":
    main()
