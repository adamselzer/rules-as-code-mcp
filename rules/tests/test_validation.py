"""Input-validation tests at the model boundary.

The MCP server relies on these models to reject malformed input with a clean
error before any rule runs. A model on the other end of the wire should never be
able to push a negative income or an empty household into the calculation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rules import Household, IncomeSource, Person


def test_empty_household_rejected():
    with pytest.raises(ValidationError):
        Household(members=[])


def test_negative_income_rejected():
    with pytest.raises(ValidationError):
        IncomeSource(kind="earned", monthly_amount=-100)


def test_negative_shelter_rejected():
    with pytest.raises(ValidationError):
        Household(members=[Person(age=30)], shelter_cost_monthly=-50)


def test_bad_income_kind_rejected():
    with pytest.raises(ValidationError):
        IncomeSource(kind="investment", monthly_amount=100)


def test_implausible_age_rejected():
    with pytest.raises(ValidationError):
        Person(age=200)
    with pytest.raises(ValidationError):
        Person(age=-1)


def test_unknown_fields_rejected():
    # extra="forbid" guards against typo'd or injected fields.
    with pytest.raises(ValidationError):
        Household(members=[Person(age=30)], shelter_cost=900)  # typo: should be shelter_cost_monthly


def test_state_code_must_be_two_chars():
    with pytest.raises(ValidationError):
        Household(members=[Person(age=30)], state="Michigan")


def test_string_income_coerced_or_rejected():
    # Non-numeric income must not silently become zero.
    with pytest.raises(ValidationError):
        IncomeSource(kind="earned", monthly_amount="lots")


def test_valid_minimal_household_accepted():
    h = Household(members=[Person(age=30)])
    assert h.size == 1
    assert h.gross_income == 0.0
