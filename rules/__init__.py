"""Rules-as-code core for SNAP eligibility.

Public surface:
    determine_snap_eligibility(household) -> Determination
    screen_programs(household) -> list[ProgramScreen]
    required_verifications(program, household) -> list[VerificationRequirement]
"""

from .models import Determination, Household, IncomeSource, Person, RuleStep
from .programs import ProgramScreen, VerificationRequirement, required_verifications, screen_programs
from .snap import determine_snap_eligibility
from .version import SNAP_RULESET

__all__ = [
    "Determination",
    "Household",
    "IncomeSource",
    "Person",
    "RuleStep",
    "ProgramScreen",
    "VerificationRequirement",
    "determine_snap_eligibility",
    "screen_programs",
    "required_verifications",
    "SNAP_RULESET",
]
