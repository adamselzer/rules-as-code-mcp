"""Cross-program screening and verification requirements.

`screen_programs` gives a coarse, anonymous-safe "which programs is this household
likely to qualify for" signal across SNAP and a simplified Medicaid income screen.
It is explicitly NOT a determination — it is the triage step a screening tool
performs before a caseworker runs a full, cited determination.

`required_verifications` lists the documents needed to confirm eligibility, derived
from the facts the household actually presents (earned income implies pay stubs,
shelter costs imply a lease, and so on).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from . import constants as C
from .citations import citation_for
from .models import Household
from .snap import determine_snap_eligibility


class ProgramScreen(BaseModel):
    """A coarse screening signal for one program. Not a determination."""

    program: str
    likely_eligible: bool
    basis: str
    citation: dict[str, str]


class VerificationRequirement(BaseModel):
    """One document or fact a caseworker must verify to confirm eligibility."""

    item: str
    reason: str
    required: bool  # True = always required; False = required only given the facts present


def screen_programs(household: Household) -> list[ProgramScreen]:
    """Screen a household across the supported programs. Anonymous-safe."""
    screens: list[ProgramScreen] = []

    # SNAP: reuse the deterministic core, but report it as a screen, not a decision.
    snap = determine_snap_eligibility(household)
    screens.append(
        ProgramScreen(
            program="SNAP",
            likely_eligible=(snap.decision == "eligible"),
            basis=snap.summary,
            citation=citation_for("snap.net_income_test").as_dict(),
        )
    )

    # Medicaid: simplified MAGI income screen for the adult expansion group only.
    # This is a coarse income check (gross income vs 138% FPL), not a MAGI
    # determination — household composition and tax-filing rules are out of scope.
    medicaid_limit = C.medicaid_adult_income_limit(household.size)
    medicaid_likely = household.gross_income <= medicaid_limit
    screens.append(
        ProgramScreen(
            program="Medicaid (adult expansion, income screen only)",
            likely_eligible=medicaid_likely,
            basis=(
                f"Gross monthly income ${household.gross_income:.0f} "
                f"{'is at or below' if medicaid_likely else 'exceeds'} the "
                f"138% FPL screen of ${medicaid_limit} for a household of {household.size}. "
                "Income screen only; not a MAGI determination."
            ),
            citation=citation_for("medicaid.magi_adult_screen").as_dict(),
        )
    )

    return screens


# Verification rules for SNAP, derived from the facts the household presents.
def required_verifications(program: str, household: Household) -> list[VerificationRequirement]:
    """List the verifications needed to confirm eligibility for the program."""
    if program.upper() != "SNAP":
        raise ValueError(f"Verification requirements are only implemented for SNAP, got {program!r}.")

    items: list[VerificationRequirement] = [
        VerificationRequirement(
            item="Identity",
            reason="Identity must be verified for the applicant. (7 CFR 273.2(f)(1)(vii))",
            required=True,
        ),
        VerificationRequirement(
            item="Residency",
            reason="Residency in the state must be verified. (7 CFR 273.2(f)(1)(vi))",
            required=True,
        ),
    ]

    if household.earned_income > 0:
        items.append(
            VerificationRequirement(
                item="Earned income (pay stubs / employer statement)",
                reason="Earned income is reported and must be verified. (7 CFR 273.2(f)(1)(i))",
                required=True,
            )
        )
    if household.unearned_income > 0:
        items.append(
            VerificationRequirement(
                item="Unearned income (benefit award letters)",
                reason="Unearned income is reported and must be verified. (7 CFR 273.2(f)(1)(i))",
                required=True,
            )
        )
    if (household.shelter_cost_monthly + household.utilities_monthly) > 0:
        items.append(
            VerificationRequirement(
                item="Shelter and utility costs (lease, mortgage, utility bills)",
                reason="Shelter costs claimed for the excess shelter deduction may require verification.",
                required=False,
            )
        )
    if household.dependent_care_monthly > 0:
        items.append(
            VerificationRequirement(
                item="Dependent care costs",
                reason="Dependent care is claimed as a deduction and may require verification.",
                required=False,
            )
        )
    if household.medical_expenses_monthly > 0 and household.has_elderly_or_disabled:
        items.append(
            VerificationRequirement(
                item="Medical expenses (elderly/disabled)",
                reason="Medical expenses claimed for the medical deduction must be verified. (7 CFR 273.2(f)(1)(iv))",
                required=True,
            )
        )
    return items
