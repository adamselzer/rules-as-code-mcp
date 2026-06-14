"""The SNAP eligibility core — rules as code.

This is the deterministic heart of the system. Given a fully-specified household,
it returns a determination plus the exact trace of rules that fired to reach it.
No model, no randomness, no network: the same household always yields the same
determination and the same determination_id.

The calculation implements the federal SNAP financial eligibility test for the
48 contiguous states and DC, with Michigan's broad-based categorical eligibility
applied as a state option:

  1. Asset test (waived under BBCE).
  2. Gross income test at 130% FPL (200% under BBCE; exempt for households with
     an elderly or disabled member).
  3. Net income test at 100% FPL, after the statutory deductions.

Every step appends a RuleStep carrying its citation, so the determination is
auditable by construction.
"""

from __future__ import annotations

import hashlib
import json
import math

from . import constants as C
from .citations import citation_for
from .models import Determination, Household, RuleStep
from .version import SNAP_RULESET


def _round_dollar(amount: float) -> int:
    """Round to the nearest dollar, rounding up at 50 cents (SNAP convention)."""
    return int(math.floor(amount + 0.5))


def _step(rule_id: str, description: str, inputs: dict, result: str, passed: bool | None) -> RuleStep:
    return RuleStep(
        rule_id=rule_id,
        description=description,
        inputs=inputs,
        result=result,
        passed=passed,
        citation=citation_for(rule_id).as_dict(),
    )


def _determination_id(household: Household, program: str) -> str:
    """Stable, reproducible id derived from the inputs and the ruleset version.

    Using a hash (not a random uuid) means the id is itself an audit artifact:
    re-running the same case under the same ruleset reproduces the same id.
    """
    payload = {
        "program": program,
        "ruleset": SNAP_RULESET.version,
        "household": household.model_dump(),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"snap-{digest[:16]}"


def compute_net_income(household: Household, trace: list[RuleStep]) -> dict[str, float]:
    """Compute net monthly income, appending a RuleStep for each deduction.

    Returns a breakdown dict so the determination can report exactly how net
    income was built up.
    """
    earned = household.earned_income
    unearned = household.unearned_income
    gross = earned + unearned

    # 1. Earned income deduction: 20% of gross earned income.
    earned_deduction = round(earned * C.SNAP_EARNED_INCOME_DEDUCTION_RATE, 2)
    trace.append(
        _step(
            "snap.earned_income_deduction",
            "Deduct 20% of gross earned income.",
            {"earned_income": round(earned, 2), "rate": C.SNAP_EARNED_INCOME_DEDUCTION_RATE},
            f"earned_income_deduction=${earned_deduction:.2f}",
            None,
        )
    )

    # 2. Standard deduction by household size.
    std = C.standard_deduction(household.size)
    trace.append(
        _step(
            "snap.standard_deduction",
            "Apply the standard deduction for the household size.",
            {"household_size": household.size},
            f"standard_deduction=${std}",
            None,
        )
    )

    # 3. Dependent care (actual cost).
    dep_care = round(household.dependent_care_monthly, 2)
    if dep_care > 0:
        trace.append(
            _step(
                "snap.dependent_care_deduction",
                "Deduct out-of-pocket dependent care needed for work or training.",
                {"dependent_care_monthly": dep_care},
                f"dependent_care_deduction=${dep_care:.2f}",
                None,
            )
        )

    # 4. Child support paid (legally obligated).
    child_support = round(household.child_support_paid_monthly, 2)
    if child_support > 0:
        trace.append(
            _step(
                "snap.child_support_deduction",
                "Deduct legally obligated child support paid to a non-household member.",
                {"child_support_paid_monthly": child_support},
                f"child_support_deduction=${child_support:.2f}",
                None,
            )
        )

    # 5. Medical expenses over $35 — elderly/disabled members only.
    medical_deduction = 0.0
    if household.has_elderly_or_disabled and household.medical_expenses_monthly > 0:
        over = household.medical_expenses_monthly - C.SNAP_MEDICAL_EXPENSE_THRESHOLD
        medical_deduction = round(max(0.0, over), 2)
        trace.append(
            _step(
                "snap.medical_deduction",
                "Deduct out-of-pocket medical expenses over $35/month for elderly or disabled members.",
                {
                    "medical_expenses_monthly": round(household.medical_expenses_monthly, 2),
                    "threshold": C.SNAP_MEDICAL_EXPENSE_THRESHOLD,
                },
                f"medical_deduction=${medical_deduction:.2f}",
                None,
            )
        )

    # Adjusted income after the non-shelter deductions.
    adjusted = gross - earned_deduction - std - dep_care - child_support - medical_deduction
    adjusted = max(0.0, adjusted)

    # 6. Excess shelter deduction: shelter cost over half of adjusted income,
    #    capped unless the household has an elderly/disabled member.
    shelter_total = round(household.shelter_cost_monthly + household.utilities_monthly, 2)
    half_adjusted = adjusted / 2.0
    excess = shelter_total - half_adjusted
    shelter_deduction = 0.0
    if excess > 0:
        shelter_deduction = round(excess, 2)
        capped = False
        if not household.has_elderly_or_disabled and shelter_deduction > C.SNAP_EXCESS_SHELTER_CAP:
            shelter_deduction = float(C.SNAP_EXCESS_SHELTER_CAP)
            capped = True
        trace.append(
            _step(
                "snap.excess_shelter_deduction",
                "Deduct shelter costs above half of adjusted income"
                + (", capped" if capped else "")
                + ("; cap waived (elderly/disabled present)." if household.has_elderly_or_disabled else "."),
                {
                    "shelter_costs": shelter_total,
                    "half_adjusted_income": round(half_adjusted, 2),
                    "cap": C.SNAP_EXCESS_SHELTER_CAP,
                    "capped": capped,
                    "uncapped_elderly_disabled": household.has_elderly_or_disabled,
                },
                f"excess_shelter_deduction=${shelter_deduction:.2f}",
                None,
            )
        )

    net = max(0.0, adjusted - shelter_deduction)
    return {
        "gross_income": round(gross, 2),
        "earned_income": round(earned, 2),
        "unearned_income": round(unearned, 2),
        "earned_income_deduction": earned_deduction,
        "standard_deduction": float(std),
        "dependent_care_deduction": dep_care,
        "child_support_deduction": child_support,
        "medical_deduction": medical_deduction,
        "adjusted_income": round(adjusted, 2),
        "excess_shelter_deduction": shelter_deduction,
        "net_income": round(net, 2),
    }


def determine_snap_eligibility(household: Household, *, include_pii: bool = False) -> Determination:
    """Run the full SNAP financial eligibility test and return a Determination."""
    trace: list[RuleStep] = []
    size = household.size
    bbce = C.SNAP_BBCE_ENABLED

    # --- Asset test (waived under BBCE) -------------------------------------
    asset_passed = True
    if bbce:
        trace.append(
            _step(
                "snap.bbce",
                "Broad-based categorical eligibility in effect: asset test waived; "
                "gross income limit raised to 200% of poverty.",
                {"bbce_enabled": True, "bbce_gross_percent": C.SNAP_BBCE_GROSS_INCOME_PERCENT},
                "asset_test=waived",
                None,
            )
        )
    else:
        limit = (
            C.SNAP_RESOURCE_LIMIT_ELDERLY_DISABLED
            if household.has_elderly_or_disabled
            else C.SNAP_RESOURCE_LIMIT_STANDARD
        )
        asset_passed = household.countable_resources <= limit
        trace.append(
            _step(
                "snap.asset_test",
                "Countable resources must not exceed the resource limit.",
                {"countable_resources": round(household.countable_resources, 2), "limit": limit},
                f"resources ${household.countable_resources:.2f} {'<=' if asset_passed else '>'} ${limit}",
                asset_passed,
            )
        )

    # --- Gross income test --------------------------------------------------
    gross = household.gross_income
    gross_passed = True
    if household.has_elderly_or_disabled:
        trace.append(
            _step(
                "snap.elderly_disabled_gross_exemption",
                "Household contains an elderly (60+) or disabled member: gross income test waived.",
                {"has_elderly_or_disabled": True},
                "gross_income_test=exempt",
                None,
            )
        )
    else:
        gross_limit = C.bbce_gross_income_limit(size) if bbce else C.gross_income_limit(size)
        rounded_gross = _round_dollar(gross)
        gross_passed = rounded_gross <= gross_limit
        trace.append(
            _step(
                "snap.gross_income_test",
                f"Gross monthly income must be at or below the {'200%' if bbce else '130%'} "
                "of poverty limit for the household size.",
                {"gross_income": rounded_gross, "limit": gross_limit, "household_size": size},
                f"gross ${rounded_gross} {'<=' if gross_passed else '>'} ${gross_limit}",
                gross_passed,
            )
        )
        # Record which standards table the limit came from.
        trace.append(
            _step(
                "snap.income_standards",
                "Income limits are the FY2026 SNAP standards for the household size.",
                {"household_size": size, "gross_income_limit": gross_limit},
                f"gross_income_limit=${gross_limit}",
                None,
            )
        )

    # --- Net income test ----------------------------------------------------
    breakdown = compute_net_income(household, trace)
    net_limit = C.net_income_limit(size)
    rounded_net = _round_dollar(breakdown["net_income"])
    net_passed = rounded_net <= net_limit
    trace.append(
        _step(
            "snap.net_income_test",
            "Net monthly income (after deductions) must be at or below the 100% of poverty limit.",
            {"net_income": rounded_net, "limit": net_limit, "household_size": size},
            f"net ${rounded_net} {'<=' if net_passed else '>'} ${net_limit}",
            net_passed,
        )
    )

    # --- Decision -----------------------------------------------------------
    eligible = asset_passed and gross_passed and net_passed
    decision = "eligible" if eligible else "ineligible"

    if eligible:
        summary = (
            f"Household of {size} is financially eligible for SNAP under {SNAP_RULESET.version}: "
            f"net income ${rounded_net} is at or below the ${net_limit} limit."
        )
    else:
        failed = []
        if not asset_passed:
            failed.append("asset test")
        if not gross_passed:
            failed.append("gross income test")
        if not net_passed:
            failed.append("net income test")
        summary = (
            f"Household of {size} is not financially eligible for SNAP under "
            f"{SNAP_RULESET.version}: failed the {', '.join(failed)}."
        )

    computed = {
        **breakdown,
        "gross_income_limit": float(
            C.bbce_gross_income_limit(size)
            if (bbce and not household.has_elderly_or_disabled)
            else (C.gross_income_limit(size) if not household.has_elderly_or_disabled else 0)
        ),
        "net_income_limit": float(net_limit),
    }

    citations = _dedupe_citations(trace)

    return Determination(
        determination_id=_determination_id(household, "SNAP"),
        program="SNAP",
        decision=decision,
        summary=summary,
        household_size=size,
        computed=computed,
        rule_trace=trace,
        citations=citations,
        ruleset_version=SNAP_RULESET.as_dict(),
        pii_included=include_pii,
    )


def _dedupe_citations(trace: list[RuleStep]) -> list[dict[str, str]]:
    """Collect the distinct citations referenced by a trace, preserving order."""
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for step in trace:
        label = step.citation["label"]
        if label not in seen:
            seen.add(label)
            out.append(step.citation)
    return out
