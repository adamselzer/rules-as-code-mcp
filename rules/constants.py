"""FY2026 SNAP figures — the versioned, citable data the rules operate on.

48 contiguous states and DC, effective 2025-10-01 through 2026-09-30.

These are the only "magic numbers" in the system, and they live here, in one
place, stamped to a fiscal year, each traceable to a citation in citations.py.
When the FY2027 COLA is published, this file (and version.py) change; the rule
logic in snap.py does not. That separation is the point of rules-as-code.

Sources:
  - Monthly gross/net income standards: USDA FNS FY2026 SNAP COLA.
    Independently verified by deriving 130% and 100% of the 2025 HHS poverty
    guidelines (annual / 12, rounded up to the next dollar); the derivation
    reproduces the published figures for household sizes 1-8.
  - Standard deduction, excess-shelter cap, earned-income %: CBPP "A Quick Guide
    to SNAP Eligibility and Benefits" (FY2026 values) and 7 CFR 273.9.
"""

from __future__ import annotations

# --- Federal poverty guidelines (the base everything derives from) ----------

# 2025 HHS poverty guidelines (annual, 48 contiguous states and DC). These are
# the base for the FY2026 SNAP income standards and the Medicaid MAGI screen.
# The published SNAP gross/net tables below are 130%/100% of these, rounded up
# to the next dollar; a unit test enforces that consistency.
POVERTY_GUIDELINE_ANNUAL: dict[int, int] = {
    1: 15650,
    2: 21150,
    3: 26650,
    4: 32150,
    5: 37650,
    6: 43150,
    7: 48650,
    8: 54150,
}
POVERTY_GUIDELINE_EACH_ADDITIONAL = 5500


def poverty_monthly(household_size: int) -> float:
    """Monthly federal poverty guideline (unrounded) for the household size."""
    if household_size < 1:
        raise ValueError("household_size must be >= 1")
    if household_size in POVERTY_GUIDELINE_ANNUAL:
        annual = POVERTY_GUIDELINE_ANNUAL[household_size]
    else:
        extra = household_size - 8
        annual = POVERTY_GUIDELINE_ANNUAL[8] + extra * POVERTY_GUIDELINE_EACH_ADDITIONAL
    return annual / 12.0


# --- Monthly income eligibility standards (dollars/month) -------------------

# Gross income test threshold = 130% of the federal poverty guideline.
SNAP_GROSS_INCOME_LIMIT: dict[int, int] = {
    1: 1696,
    2: 2292,
    3: 2888,
    4: 3483,
    5: 4079,
    6: 4675,
    7: 5271,
    8: 5867,
}
SNAP_GROSS_INCOME_LIMIT_EACH_ADDITIONAL = 596

# Net income test threshold = 100% of the federal poverty guideline.
SNAP_NET_INCOME_LIMIT: dict[int, int] = {
    1: 1305,
    2: 1763,
    3: 2221,
    4: 2680,
    5: 3138,
    6: 3596,
    7: 4055,
    8: 4513,
}
SNAP_NET_INCOME_LIMIT_EACH_ADDITIONAL = 459

# --- Deductions -------------------------------------------------------------

# Standard deduction by household size (1-3 share a value; 4, 5, and 6+ step up).
SNAP_STANDARD_DEDUCTION: dict[int, int] = {1: 209, 2: 209, 3: 209, 4: 223, 5: 261}
SNAP_STANDARD_DEDUCTION_6_PLUS = 299

# Fraction of earned income deducted before the net-income test (statutory, 20%).
SNAP_EARNED_INCOME_DEDUCTION_RATE = 0.20

# Excess shelter deduction: shelter costs above half of adjusted income are
# deductible, capped at this amount UNLESS the household has an elderly or
# disabled member (then uncapped).
SNAP_EXCESS_SHELTER_CAP = 744

# Out-of-pocket medical expenses over this monthly threshold are deductible, for
# elderly (60+) or disabled members only.
SNAP_MEDICAL_EXPENSE_THRESHOLD = 35

# --- Asset (resource) limits ------------------------------------------------

# Federal resource limits. Waived for households qualifying under broad-based
# categorical eligibility (Michigan applies BBCE, so the asset test is off by
# default; see SNAP_BBCE_ENABLED).
SNAP_RESOURCE_LIMIT_STANDARD = 3000
SNAP_RESOURCE_LIMIT_ELDERLY_DISABLED = 4500

# --- Categorical eligibility (state option) ---------------------------------

# Michigan uses broad-based categorical eligibility: the gross income limit is
# raised to this percentage of poverty and the asset test is waived. The net
# income test still applies.
SNAP_BBCE_ENABLED = True
SNAP_BBCE_GROSS_INCOME_PERCENT = 200  # percent of poverty

# --- Demographics -----------------------------------------------------------

SNAP_ELDERLY_AGE = 60  # age at which a member is "elderly" for SNAP purposes

# --- Medicaid (simplified income screen only, not a determination) ----------

# Adult expansion group income ceiling, as a percent of the federal poverty
# level (MAGI-based). Used by screen_programs for a coarse "likely qualifies"
# signal only.
MEDICAID_ADULT_MAGI_PERCENT = 138


def gross_income_limit(household_size: int) -> int:
    """Monthly gross income limit (130% FPL) for a household of the given size."""
    if household_size < 1:
        raise ValueError("household_size must be >= 1")
    if household_size in SNAP_GROSS_INCOME_LIMIT:
        return SNAP_GROSS_INCOME_LIMIT[household_size]
    extra = household_size - 8
    return SNAP_GROSS_INCOME_LIMIT[8] + extra * SNAP_GROSS_INCOME_LIMIT_EACH_ADDITIONAL


def net_income_limit(household_size: int) -> int:
    """Monthly net income limit (100% FPL) for a household of the given size."""
    if household_size < 1:
        raise ValueError("household_size must be >= 1")
    if household_size in SNAP_NET_INCOME_LIMIT:
        return SNAP_NET_INCOME_LIMIT[household_size]
    extra = household_size - 8
    return SNAP_NET_INCOME_LIMIT[8] + extra * SNAP_NET_INCOME_LIMIT_EACH_ADDITIONAL


def standard_deduction(household_size: int) -> int:
    """Standard deduction for a household of the given size."""
    if household_size < 1:
        raise ValueError("household_size must be >= 1")
    if household_size in SNAP_STANDARD_DEDUCTION:
        return SNAP_STANDARD_DEDUCTION[household_size]
    return SNAP_STANDARD_DEDUCTION_6_PLUS


def bbce_gross_income_limit(household_size: int) -> int:
    """Gross income limit under broad-based categorical eligibility (200% FPL)."""
    return _round_up(poverty_monthly(household_size) * SNAP_BBCE_GROSS_INCOME_PERCENT / 100)


def medicaid_adult_income_limit(household_size: int) -> int:
    """Monthly income ceiling for the Medicaid adult expansion screen (138% FPL)."""
    return _round_up(poverty_monthly(household_size) * MEDICAID_ADULT_MAGI_PERCENT / 100)


def _round_up(value: float) -> int:
    """Round up to the next whole dollar, the convention USDA uses for limits."""
    import math

    return int(math.ceil(round(value, 2)))
