# Triage

**Complexity-routing gateway — not every prompt deserves the big model.**

Triage classifies each request and routes it to the cheapest tier that can handle it:

| Tier | Name | Handles |
|---|---|---|
| 0 | `local-small` | short, simple, single-intent asks (mini lanes) |
| 1 | `local-large` | reasoning, code, multi-step (spark/studio) |
| 2 | `frontier` | long-context, agentic, high-stakes |

## The design choice

Routing uses **no model call** — deterministic signals only (token estimate, code fences, reasoning markers, multi-question detection). That means routing is free, instant, and **explainable**: every decision carries a `reason` field you can log and audit.

```python
from triage import route

d = route("Why does this fail?\n```python\n...\n```")
d.tier    # 1
d.name    # 'local-large'
d.reason  # 'medium input (38 est tokens); contains code; reasoning markers'
```

Escalation rule: any single complexity signal bumps the tier; **two or more** goes straight to frontier. Callers can pin a tier with `override=` for SLA or user preference.

## Part of the TechGuardCoders portfolio

- **Ball Knowledge** already runs a BackendChain — Triage is the policy layer that decides *which* backend before the chain is consulted
- **statsheet** can prove the routing saves money without hurting quality (paired tests on tier-0 vs tier-1 outcomes)
- **Forerunner** can watch per-tier error rates for drift

## Tests

```bash
python -m pytest tests/ -q   # 14 tests
```

Every escalation path is locked by a test, routing is deterministic, and the decision object is auditable end to end.
