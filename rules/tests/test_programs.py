"""Tests for cross-program screening and verification requirements."""

from __future__ import annotations

import pytest

from rules import (
    Household,
    IncomeSource,
    Person,
    required_verifications,
    screen_programs,
)
from rules import constants as C


def hh(members, income=None, **kw):
    return Household(members=members, income=income or [], **kw)


def test_screen_returns_snap_and_medicaid():
    screens = screen_programs(hh([Person(age=30)], [IncomeSource(kind="earned", monthly_amount=800)]))
    programs = [s.program for s in screens]
    assert any("SNAP" in p for p in programs)
    assert any("Medicaid" in p for p in programs)


def test_low_income_likely_eligible_for_both():
    screens = screen_programs(hh([Person(age=30)], [IncomeSource(kind="earned", monthly_amount=500)]))
    assert all(s.likely_eligible for s in screens)


def test_medicaid_screen_tracks_138_percent_threshold():
    size = 1
    limit = C.medicaid_adult_income_limit(size)
    below = screen_programs(hh([Person(age=30)], [IncomeSource(kind="unearned", monthly_amount=limit)]))
    above = screen_programs(hh([Person(age=30)], [IncomeSource(kind="unearned", monthly_amount=limit + 1)]))
    med_below = next(s for s in below if "Medicaid" in s.program)
    med_above = next(s for s in above if "Medicaid" in s.program)
    assert med_below.likely_eligible is True
    assert med_above.likely_eligible is False


def test_verifications_always_include_identity_and_residency():
    items = required_verifications("SNAP", hh([Person(age=30)]))
    labels = [i.item for i in items]
    assert "Identity" in labels
    assert "Residency" in labels


def test_verifications_are_derived_from_facts():
    h = hh(
        [Person(age=40)],
        [IncomeSource(kind="earned", monthly_amount=1500)],
        shelter_cost_monthly=900,
        dependent_care_monthly=200,
    )
    labels = " ".join(i.item for i in required_verifications("SNAP", h))
    assert "Earned income" in labels
    assert "Shelter" in labels
    assert "Dependent care" in labels


def test_no_income_means_no_income_verification():
    items = required_verifications("SNAP", hh([Person(age=30)]))
    labels = " ".join(i.item for i in items)
    assert "income" not in labels.lower()


def test_medical_verification_only_for_elderly_disabled():
    young = required_verifications(
        "SNAP", hh([Person(age=30)], medical_expenses_monthly=400)
    )
    assert not any("Medical" in i.item for i in young)
    old = required_verifications(
        "SNAP", hh([Person(age=70)], [IncomeSource(kind="unearned", monthly_amount=900)], medical_expenses_monthly=400)
    )
    assert any("Medical" in i.item for i in old)


def test_unsupported_program_raises():
    with pytest.raises(ValueError):
        required_verifications("TANF", hh([Person(age=30)]))
