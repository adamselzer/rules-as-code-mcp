"""Domain models for SNAP eligibility.

Pydantic does double duty here: these models ARE the input-validation layer the
MCP server relies on (bad types, negative dollars, empty households fail at the
boundary with a clean error), and they are the shape the rules logic consumes.

Note what is deliberately absent: names, SSNs, addresses, dates of birth. The
rule logic needs ages and flags, not identities. Keeping PII out of the core
model is what lets the anonymous screening role exist at all.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, NonNegativeFloat


class Person(BaseModel):
    """A household member. Carries only what the rules need: age and disability."""

    model_config = {"extra": "forbid"}

    age: int = Field(ge=0, le=130, description="Age in years.")
    disabled: bool = Field(
        default=False,
        description="Whether the member meets SNAP's disability definition.",
    )

    @property
    def is_elderly(self) -> bool:
        from .constants import SNAP_ELDERLY_AGE

        return self.age >= SNAP_ELDERLY_AGE


class IncomeSource(BaseModel):
    """One stream of monthly income."""

    model_config = {"extra": "forbid"}

    kind: Literal["earned", "unearned"] = Field(
        description="'earned' = wages/self-employment; 'unearned' = benefits, support, etc."
    )
    monthly_amount: NonNegativeFloat = Field(description="Gross monthly amount in dollars.")
    source: str = Field(
        default="",
        max_length=120,
        description="Free-text label, e.g. 'wages' or 'SSI'. Not used in the calculation.",
    )


class Household(BaseModel):
    """A SNAP filing unit and the facts needed to test its eligibility.

    All monetary fields are monthly dollar amounts. The household is the unit of
    analysis: income and expenses are aggregated across members for the test.
    """

    model_config = {"extra": "forbid"}

    members: list[Person] = Field(min_length=1, description="Household members (at least one).")
    income: list[IncomeSource] = Field(default_factory=list, description="Monthly income streams.")
    shelter_cost_monthly: NonNegativeFloat = Field(
        default=0.0, description="Rent or mortgage, monthly."
    )
    utilities_monthly: NonNegativeFloat = Field(
        default=0.0, description="Utility costs counted toward the shelter deduction, monthly."
    )
    dependent_care_monthly: NonNegativeFloat = Field(
        default=0.0, description="Out-of-pocket dependent care needed for work/training, monthly."
    )
    child_support_paid_monthly: NonNegativeFloat = Field(
        default=0.0, description="Legally obligated child support paid out, monthly."
    )
    medical_expenses_monthly: NonNegativeFloat = Field(
        default=0.0,
        description="Out-of-pocket medical costs (counted only for elderly/disabled members), monthly.",
    )
    countable_resources: NonNegativeFloat = Field(
        default=0.0, description="Countable assets/resources in dollars."
    )
    state: str = Field(default="MI", max_length=2, min_length=2, description="Two-letter state code.")

    # --- Derived facts the rules read off the household -----------------------

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def has_elderly_or_disabled(self) -> bool:
        return any(m.is_elderly or m.disabled for m in self.members)

    @property
    def earned_income(self) -> float:
        return sum(s.monthly_amount for s in self.income if s.kind == "earned")

    @property
    def unearned_income(self) -> float:
        return sum(s.monthly_amount for s in self.income if s.kind == "unearned")

    @property
    def gross_income(self) -> float:
        return self.earned_income + self.unearned_income


# --- Determination output ---------------------------------------------------

Decision = Literal["eligible", "ineligible", "indeterminate"]


class RuleStep(BaseModel):
    """One step in a rule trace: a rule that fired, what it saw, what it concluded."""

    rule_id: str
    description: str
    inputs: dict[str, float | int | str | bool]
    result: str
    passed: bool | None = Field(
        default=None,
        description="True/False for pass-fail rules; None for steps that only compute a value.",
    )
    citation: dict[str, str]


class Determination(BaseModel):
    """The result of testing a household against one program.

    Never a bare yes/no: the decision always travels with the rule trace, the
    citations, the computed figures, and the ruleset version that produced it.
    """

    determination_id: str
    program: str
    decision: Decision
    summary: str
    household_size: int
    computed: dict[str, float]
    rule_trace: list[RuleStep]
    citations: list[dict[str, str]]
    ruleset_version: dict[str, str]
    pii_included: bool = False
