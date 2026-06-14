"""Exhaustive tests for the SNAP eligibility determination.

Covers eligible / ineligible / near-threshold households, each pathway through
the test (gross fail, net fail, asset behavior, elderly/disabled exemption), and
the structural invariants every determination must satisfy.
"""

from __future__ import annotations

import pytest

from rules import Household, IncomeSource, Person, determine_snap_eligibility
from rules import constants as C
from rules.version import SNAP_RULESET


def hh(members, income=None, **kw):
    return Household(members=members, income=income or [], **kw)


def earned(amount):
    return [IncomeSource(kind="earned", monthly_amount=amount, source="wages")]


def unearned(amount):
    return [IncomeSource(kind="unearned", monthly_amount=amount, source="benefit")]


# --- Clear cases ------------------------------------------------------------


def test_clearly_eligible_low_income_family():
    d = determine_snap_eligibility(hh([Person(age=30), Person(age=4)], earned(800)))
    assert d.decision == "eligible"


def test_clearly_ineligible_high_income_single():
    # Single person earning far above any limit.
    d = determine_snap_eligibility(hh([Person(age=40)], earned(6000)))
    assert d.decision == "ineligible"


def test_zero_income_household_is_eligible():
    d = determine_snap_eligibility(hh([Person(age=25)]))
    assert d.decision == "eligible"
    assert d.computed["net_income"] == 0.0


# --- Net income test pathway ------------------------------------------------


def test_unearned_income_gets_no_earned_deduction():
    # $1500 unearned for a single person: no 20% deduction, only standard.
    # net = 1500 - 209 = 1291 > 1305? 1291 <= 1305 -> eligible (barely)
    d = determine_snap_eligibility(hh([Person(age=30)], unearned(1500)))
    assert d.computed["earned_income_deduction"] == 0.0
    assert d.computed["net_income"] == pytest.approx(1291.0)
    assert d.decision == "eligible"


def test_fails_net_income_test_when_net_exceeds_limit():
    # Unearned income high enough that even the standard deduction can't bring
    # net below the 100% FPL limit for a single person ($1305).
    d = determine_snap_eligibility(hh([Person(age=30)], unearned(1600)))
    # net = 1600 - 209 = 1391 > 1305
    assert d.computed["net_income"] == pytest.approx(1391.0)
    assert d.decision == "ineligible"
    assert any(s.rule_id == "snap.net_income_test" and s.passed is False for s in d.rule_trace)


def test_near_threshold_just_eligible():
    # Construct a single-person unearned income exactly at the net limit.
    limit = C.net_income_limit(1)  # 1305
    income = limit + C.standard_deduction(1)  # add back the standard deduction
    d = determine_snap_eligibility(hh([Person(age=30)], unearned(income)))
    assert d.computed["net_income"] == pytest.approx(float(limit))
    assert d.decision == "eligible"  # at-or-below is eligible


def test_near_threshold_just_ineligible():
    limit = C.net_income_limit(1)
    income = limit + C.standard_deduction(1) + 1  # one dollar over
    d = determine_snap_eligibility(hh([Person(age=30)], unearned(income)))
    assert d.decision == "ineligible"


# --- Gross income test pathway (BBCE at 200%) -------------------------------


def test_gross_income_test_can_fail_under_bbce():
    # Earned income above 200% FPL gross limit for size 1 fails the gross test
    # even though deductions might bring net down.
    assert C.SNAP_BBCE_ENABLED  # this test assumes the shipped Michigan config
    gross_limit = C.bbce_gross_income_limit(1)
    d = determine_snap_eligibility(hh([Person(age=30)], earned(gross_limit + 100)))
    gross_step = next(s for s in d.rule_trace if s.rule_id == "snap.gross_income_test")
    assert gross_step.passed is False
    assert d.decision == "ineligible"


def test_gross_step_records_bbce_limit():
    d = determine_snap_eligibility(hh([Person(age=30)], earned(500)))
    gross_step = next(s for s in d.rule_trace if s.rule_id == "snap.gross_income_test")
    assert gross_step.inputs["limit"] == C.bbce_gross_income_limit(1)


# --- Elderly / disabled handling --------------------------------------------


def test_elderly_household_is_exempt_from_gross_test():
    d = determine_snap_eligibility(hh([Person(age=67)], earned(5000)))
    rule_ids = {s.rule_id for s in d.rule_trace}
    assert "snap.elderly_disabled_gross_exemption" in rule_ids
    assert "snap.gross_income_test" not in rule_ids


def test_disabled_member_triggers_exemption():
    d = determine_snap_eligibility(hh([Person(age=40, disabled=True), Person(age=10)], earned(4000)))
    rule_ids = {s.rule_id for s in d.rule_trace}
    assert "snap.elderly_disabled_gross_exemption" in rule_ids


def test_elderly_shelter_deduction_is_uncapped():
    # Very high shelter cost for an elderly household: shelter deduction exceeds
    # the cap, and the cap must NOT apply.
    members = [Person(age=70)]
    d = determine_snap_eligibility(
        hh(members, unearned(1000), shelter_cost_monthly=2000, utilities_monthly=300)
    )
    shelter_step = next(s for s in d.rule_trace if s.rule_id == "snap.excess_shelter_deduction")
    assert shelter_step.inputs["capped"] is False
    assert d.computed["excess_shelter_deduction"] > C.SNAP_EXCESS_SHELTER_CAP


def test_nonelderly_shelter_deduction_is_capped():
    d = determine_snap_eligibility(
        hh([Person(age=30)], earned(1000), shelter_cost_monthly=2000, utilities_monthly=300)
    )
    assert d.computed["excess_shelter_deduction"] == float(C.SNAP_EXCESS_SHELTER_CAP)


def test_medical_deduction_only_for_elderly_disabled():
    # Non-elderly household: medical expenses are ignored.
    d_young = determine_snap_eligibility(
        hh([Person(age=30)], earned(1000), medical_expenses_monthly=500)
    )
    assert d_young.computed["medical_deduction"] == 0.0

    # Elderly household: medical over $35 is deductible.
    d_old = determine_snap_eligibility(
        hh([Person(age=70)], unearned(1000), medical_expenses_monthly=135)
    )
    assert d_old.computed["medical_deduction"] == pytest.approx(100.0)  # 135 - 35


# --- Structural invariants every determination satisfies --------------------


def test_determination_is_reproducible():
    h = hh([Person(age=30), Person(age=5)], earned(1200), shelter_cost_monthly=700)
    a = determine_snap_eligibility(h)
    b = determine_snap_eligibility(h)
    assert a.determination_id == b.determination_id
    assert a.model_dump() == b.model_dump()


def test_different_households_get_different_ids():
    a = determine_snap_eligibility(hh([Person(age=30)], earned(1000)))
    b = determine_snap_eligibility(hh([Person(age=30)], earned(1001)))
    assert a.determination_id != b.determination_id


def test_determination_always_carries_trace_citations_and_version():
    d = determine_snap_eligibility(hh([Person(age=30)], earned(1000)))
    assert d.rule_trace, "every determination must have a non-empty rule trace"
    assert d.citations, "every determination must carry citations"
    assert d.ruleset_version["version"] == SNAP_RULESET.version
    assert d.decision in {"eligible", "ineligible"}


def test_summary_mentions_decision_basis():
    d = determine_snap_eligibility(hh([Person(age=30)], earned(6000)))
    assert "not financially eligible" in d.summary
    assert "income test" in d.summary
