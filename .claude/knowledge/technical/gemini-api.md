# Gemini API Integration

**Category:** technical
**Created:** 2025-02-03
**Confidence:** high
**Source:** implemented

## Summary
Google GenAI SDK for persistent conversation with Gemini as human proxy.

## Details

### SDK
Use `google-genai` (NOT deprecated `google-generativeai`).

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
```

### Model
- Primary: `gemini-2.0-flash`
- Fallback chain: `gemini-2.5-pro` → `gemini-2.5-flash` → `gemini-2.0-flash`

### Persistent Conversation
History stored in `.claude/gemini_session.json`:
```json
{
  "last_updated": "ISO-date",
  "model": "gemini-2.0-flash",
  "history": [
    {"role": "user", "text": "..."},
    {"role": "model", "text": "..."}
  ]
}
```

### System Instruction
Gemini is configured as "human proxy" with instructions to:
- APPROVE work aligned with plan
- REVISE for minor adjustments
- ESCALATE only for plan deviations

## Code Example
```python
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.4,
        max_output_tokens=2048
    )
)
```

## Related
- [Autonomous Development](../domain/autonomous-development.md)
