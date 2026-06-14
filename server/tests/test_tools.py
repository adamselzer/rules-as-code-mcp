"""Tests for tool logic: scope enforcement, structured errors, and happy paths.

These exercise the tool functions directly with explicit scopes, which is the
whole reason the logic takes scopes as an argument: no transport needed.
"""

from __future__ import annotations

import pytest

from server import tools as T
from server.auth import scopes_for_role
from server.errors import (
    AuthorizationError,
    InputValidationError,
    NotFoundError,
    ToolMisuseError,
)

SCREENING = scopes_for_role("screening")
CASEWORKER = scopes_for_role("caseworker")

HH = {
    "members": [{"age": 34}, {"age": 6}],
    "income": [{"kind": "earned", "monthly_amount": 1200}],
    "shelter_cost_monthly": 800,
}


# --- screen_programs (screening scope) --------------------------------------


def test_screen_allowed_for_screening():
    r = T.logic_screen_programs(HH, SCREENING)
    assert r.household_size == 2
    assert len(r.screens) == 2
    assert "not a determination" in r.disclaimer.lower() or "screening only" in r.disclaimer.lower()


def test_screen_allowed_for_caseworker():
    # caseworker scope is a superset and may also screen
    assert T.logic_screen_programs(HH, CASEWORKER).screens


# --- check_program_eligibility (caseworker scope) ---------------------------


def test_determination_requires_caseworker():
    with pytest.raises(AuthorizationError) as e:
        T.logic_check_program_eligibility("SNAP", HH, SCREENING)
    assert e.value.type == "authorization_error"
    assert e.value.recoverable is False
    assert "caseworker" in e.value.details["required_scope"]


def test_determination_happy_path_and_storage():
    det = T.logic_check_program_eligibility("SNAP", HH, CASEWORKER)
    assert det.decision in {"eligible", "ineligible"}
    assert det.rule_trace and det.citations
    # determination is stored and retrievable via explain
    exp = T.logic_explain_determination(det.determination_id, CASEWORKER)
    assert exp.determination_id == det.determination_id
    assert exp.steps


def test_unsupported_program_is_tool_misuse():
    with pytest.raises(ToolMisuseError) as e:
        T.logic_check_program_eligibility("TANF", HH, CASEWORKER)
    assert e.value.recoverable is True
    assert "SNAP" in str(e.value.details["supported_programs"])


def test_malformed_household_is_input_validation_error():
    with pytest.raises(InputValidationError) as e:
        T.logic_check_program_eligibility("SNAP", {"members": []}, CASEWORKER)
    assert e.value.recoverable is True
    assert e.value.details["validation_errors"]


def test_non_object_household_rejected():
    with pytest.raises(InputValidationError):
        T.logic_check_program_eligibility("SNAP", "not a household", CASEWORKER)


# --- explain_determination --------------------------------------------------


def test_explain_requires_caseworker():
    with pytest.raises(AuthorizationError):
        T.logic_explain_determination("snap-anything", SCREENING)


def test_explain_unknown_id_is_not_found():
    with pytest.raises(NotFoundError) as e:
        T.logic_explain_determination("snap-nope", CASEWORKER)
    assert e.value.type == "not_found_error"


# --- list_required_verifications --------------------------------------------


def test_verifications_require_caseworker():
    with pytest.raises(AuthorizationError):
        T.logic_list_required_verifications("SNAP", HH, SCREENING)


def test_verifications_happy_path():
    r = T.logic_list_required_verifications("SNAP", HH, CASEWORKER)
    items = [v["item"] for v in r.verifications]
    assert "Identity" in items
    assert any("Earned income" in i for i in items)


# --- lookup_policy ----------------------------------------------------------


def test_lookup_policy_is_honest_stub():
    r = T.logic_lookup_policy("How is income counted?", SCREENING)
    assert r.stub is True
    assert r.citations == []
    assert "not yet connected" in r.answer.lower()


def test_lookup_policy_rejects_empty_question():
    with pytest.raises(InputValidationError):
        T.logic_lookup_policy("   ", SCREENING)


# --- error serialization ----------------------------------------------------


def test_structured_error_serializes_for_the_wire():
    try:
        T.logic_check_program_eligibility("SNAP", HH, SCREENING)
    except AuthorizationError as e:
        payload = e.to_dict()["error"]
        assert set(payload) == {"type", "message", "recoverable", "hint", "details"}
