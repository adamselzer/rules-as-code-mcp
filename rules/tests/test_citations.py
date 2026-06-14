"""Tests enforcing the auditability invariant: no rule fires without a citation.

These are the tests that make "every determination traces to policy" a guarantee
rather than an aspiration.
"""

from __future__ import annotations

import itertools

import pytest

from rules import Household, IncomeSource, Person, determine_snap_eligibility, screen_programs
from rules.citations import CITATIONS, Citation, citation_for


def _all_trace_rule_ids():
    """Generate determinations across varied households and collect rule_ids fired."""
    households = [
        Household(members=[Person(age=30)], income=[IncomeSource(kind="earned", monthly_amount=1000)]),
        Household(members=[Person(age=70)], income=[IncomeSource(kind="unearned", monthly_amount=1000)],
                  shelter_cost_monthly=2000, medical_expenses_monthly=200),
        Household(
            members=[Person(age=40), Person(age=8)],
            income=[IncomeSource(kind="earned", monthly_amount=2500)],
            shelter_cost_monthly=1200, dependent_care_monthly=300, child_support_paid_monthly=200,
        ),
        Household(members=[Person(age=30)], income=[IncomeSource(kind="earned", monthly_amount=9000)]),
    ]
    ids = set()
    for h in households:
        for step in determine_snap_eligibility(h).rule_trace:
            ids.add(step.rule_id)
    return ids


def test_every_fired_rule_has_a_citation():
    for rule_id in _all_trace_rule_ids():
        cite = citation_for(rule_id)  # raises if missing
        assert isinstance(cite, Citation)


def test_every_trace_step_embeds_a_well_formed_citation():
    h = Household(
        members=[Person(age=40), Person(age=8)],
        income=[IncomeSource(kind="earned", monthly_amount=2500)],
        shelter_cost_monthly=1200, dependent_care_monthly=300, child_support_paid_monthly=200,
    )
    for step in determine_snap_eligibility(h).rule_trace:
        for key in ("authority", "section", "title", "url", "label"):
            assert step.citation.get(key), f"{step.rule_id} citation missing {key}"
        assert step.citation["url"].startswith("http")


def test_citation_registry_entries_are_complete():
    for rule_id, cite in CITATIONS.items():
        assert cite.authority and cite.section and cite.title
        assert cite.url.startswith("http"), f"{rule_id} has a non-URL source"


def test_citation_for_unknown_rule_raises():
    with pytest.raises(KeyError):
        citation_for("snap.does_not_exist")


def test_screen_programs_carry_citations():
    h = Household(members=[Person(age=30)], income=[IncomeSource(kind="earned", monthly_amount=800)])
    for screen in screen_programs(h):
        assert screen.citation["url"].startswith("http")
        assert screen.citation["label"]
