"""
Triage — complexity-routing gateway.

Not every prompt deserves the big model. Triage classifies each request
and routes it to the cheapest tier that can handle it:

    tier-0  local-small    short, simple, single-intent  (mini lanes)
    tier-1  local-large    reasoning, code, multi-step   (spark/studio)
    tier-2  frontier       long-context, agentic, high-stakes

Routing signals (deterministic, explainable — no model call to route):
- token estimate (chars/4 heuristic, documented)
- structural complexity: code fences, numbered steps, multiple questions
- semantic markers: "why", "explain", "compare", "design", "debug"
- explicit override: caller pins a tier (SLA or user preference)

Public API:
    route(prompt, override=None) -> RouteDecision
    RouteDecision(tier, name, reason, signals)  — .to_dict() for logs

The point is the REASON field: every routing decision is auditable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__version__ = "0.1.0"

TIERS = {0: "local-small", 1: "local-large", 2: "frontier"}

# chars per token — English prose averages ~4; conservative for routing
CHARS_PER_TOKEN = 4

TIER0_MAX_TOKENS = 60          # short asks
TIER2_MIN_TOKENS = 800         # long-context territory

SEMANTIC_MARKERS = re.compile(
    r"\b(why|explain|compare|design|debug|analyze|refactor|architect|"
    r"trade-?offs?|step by step|root cause|prove|derive)\b", re.I)
CODE_FENCE = re.compile(r"```")
MULTI_QUESTION = re.compile(r"\?.*\?")


@dataclass
class RouteDecision:
    tier: int
    name: str
    reason: str
    signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tier": self.tier, "name": self.name,
                "reason": self.reason, "signals": self.signals}


def estimate_tokens(text: str) -> int:
    """Documented heuristic: len(text) / 4, minimum 1."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _signals(prompt: str) -> dict:
    tokens = estimate_tokens(prompt)
    return {
        "est_tokens": tokens,
        "has_code": bool(CODE_FENCE.search(prompt)),
        "has_semantic_markers": bool(SEMANTIC_MARKERS.search(prompt)),
        "multi_question": bool(MULTI_QUESTION.search(prompt)),
        "sentences": max(1, prompt.count(".") + prompt.count("!") + prompt.count("?")),
    }


def route(prompt: str, override: int | None = None) -> RouteDecision:
    """Route a prompt to a tier. override pins the tier (0/1/2)."""
    if override is not None:
        if override not in TIERS:
            raise ValueError(f"override must be one of {sorted(TIERS)}")
        return RouteDecision(override, TIERS[override], "explicit override", {})

    s = _signals(prompt)
    score = 0
    reasons = []

    if s["est_tokens"] > TIER2_MIN_TOKENS:
        score = 2
        reasons.append(f"long input ({s['est_tokens']} est tokens)")
    elif s["est_tokens"] > TIER0_MAX_TOKENS:
        score = 1
        reasons.append(f"medium input ({s['est_tokens']} est tokens)")
    else:
        reasons.append(f"short input ({s['est_tokens']} est tokens)")

    if s["has_code"]:
        score = max(score, 1)
        reasons.append("contains code")
    if s["has_semantic_markers"]:
        score = max(score, 1)
        reasons.append("reasoning markers")
    if s["multi_question"]:
        score = max(score, 1)
        reasons.append("multiple questions")

    # two or more complexity signals escalates to frontier
    complexity = sum([s["has_code"], s["has_semantic_markers"], s["multi_question"]])
    if complexity >= 2 and score < 2:
        score = 2
        reasons.append(f"{complexity} complexity signals")

    return RouteDecision(score, TIERS[score], "; ".join(reasons), s)
