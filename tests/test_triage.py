"""Triage tests — routing must be deterministic, explainable, and cheap."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from triage import route, estimate_tokens, RouteDecision, TIERS


def test_short_simple_goes_tier0():
    d = route("What time is it?")
    assert d.tier == 0
    assert "short input" in d.reason


def test_medium_reasoning_goes_tier1():
    d = route("Explain why the sky is blue in detail, with the physics. " * 5)
    assert d.tier >= 1


def test_long_input_goes_tier2():
    d = route("word " * 4000)  # ~1000 est tokens
    assert d.tier == 2
    assert "long input" in d.reason


def test_code_escalates():
    d = route("Fix this:\n```python\ndef broken():\n    return 1\n```")
    assert d.tier >= 1


def test_semantic_markers_escalate():
    d = route("Debug the root cause of this failure please")
    assert d.tier >= 1


def test_multiple_questions_escalate():
    d = route("Is X true? And what about Y? Also Z?")
    assert d.tier >= 1


def test_two_signals_escalate_to_frontier():
    d = route("Compare these designs and explain the trade-offs:\n```json\n{}\n```")
    assert d.tier == 2


def test_override_pins_tier():
    assert route("hi", override=2).tier == 2
    assert route("explain everything " * 500, override=0).tier == 0


def test_override_invalid_raises():
    with pytest.raises(ValueError):
        route("hi", override=9)


def test_estimate_tokens_documented_heuristic():
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 40) == 10
    assert estimate_tokens("") == 1


def test_decision_is_auditable():
    d = route("Why does this fail? ```py\nx=1\n```")
    assert d.reason  # non-empty human-readable reason
    assert d.signals["has_code"] is True
    assert d.to_dict()["tier"] == d.tier


def test_deterministic():
    p = "Explain the trade-offs between designs A and B? " * 3
    assert route(p).tier == route(p).tier


def test_tiers_named():
    assert TIERS == {0: "local-small", 1: "local-large", 2: "frontier"}


def test_route_decision_dataclass():
    d = RouteDecision(1, "local-large", "test")
    assert d.tier == 1 and d.name == "local-large"
