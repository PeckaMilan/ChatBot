# Autonomous Development

**Category:** domain
**Created:** 2025-02-03
**Confidence:** high
**Source:** designed

## Summary
Development workflow where Claude acts as developer and Gemini acts as human proxy/tech lead, minimizing human intervention.

## Details

### Roles
- **Human**: Strategic decisions only, contacted only on ESCALATE
- **Gemini**: Tech lead, approves/rejects within plan scope
- **Claude**: Developer, implements features

### Decision Flow
```
Claude proposes → Gemini decides:
  APPROVED → Claude proceeds
  REVISE   → Claude adjusts
  ESCALATE → Human decides
```

### Key Principles
1. Human defines the plan (BUSINESS.md, PLAN.md)
2. Gemini guards the plan scope
3. Claude works autonomously within scope
4. Deviations trigger escalation

## Related
- [Gemini API](../technical/gemini-api.md)
- [Agile Iterations](agile-iterations.md)
