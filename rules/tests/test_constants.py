"""Tests for the FY2026 SNAP constants and the derived limit functions.

The published USDA income limits are reproduced here from an independent source
(derivation from the 2025 HHS poverty guidelines), so this file also guards
against a typo in constants.py silently shifting an eligibility threshold.
"""

from __future__ import annotations

import math

import pytest

from rules import constants as C

# 2025 HHS poverty guidelines (annual, 48 contiguous states + DC), the basis for
# the FY2026 SNAP income standards. Source: HHS / USDA FNS.
POVERTY_ANNUAL = {1: 15650, 2: 21150, 3: 26650, 4: 32150, 5: 37650, 6: 43150, 7: 48650, 8: 54150}
POVERTY_EACH_ADDITIONAL = 5500


def _round_up(x: float) -> int:
    return int(math.ceil(round(x, 2)))


@pytest.mark.parametrize("size", list(range(1, 9)))
def test_gross_income_limit_matches_130_percent_of_poverty(size):
    expected = _round_up(POVERTY_ANNUAL[size] * 1.30 / 12)
    assert C.gross_income_limit(size) == expected


@pytest.mark.parametrize("size", list(range(1, 9)))
def test_net_income_limit_matches_100_percent_of_poverty(size):
    expected = _round_up(POVERTY_ANNUAL[size] / 12)
    assert C.net_income_limit(size) == expected


def test_gross_limit_published_values():
    # Spot-check against the figures USDA published for FY2026.
    assert C.SNAP_GROSS_INCOME_LIMIT[1] == 1696
    assert C.SNAP_GROSS_INCOME_LIMIT[4] == 3483
    assert C.SNAP_GROSS_INCOME_LIMIT[8] == 5867


def test_net_limit_published_values():
    assert C.SNAP_NET_INCOME_LIMIT[1] == 1305
    assert C.SNAP_NET_INCOME_LIMIT[4] == 2680
    assert C.SNAP_NET_INCOME_LIMIT[8] == 4513


def test_limits_extend_beyond_eight_with_increment():
    expected_gross = C.SNAP_GROSS_INCOME_LIMIT[8] + 2 * C.SNAP_GROSS_INCOME_LIMIT_EACH_ADDITIONAL
    assert C.gross_income_limit(10) == expected_gross
    expected_net = C.SNAP_NET_INCOME_LIMIT[8] + 3 * C.SNAP_NET_INCOME_LIMIT_EACH_ADDITIONAL
    assert C.net_income_limit(11) == expected_net


def test_standard_deduction_by_size():
    assert C.standard_deduction(1) == 209
    assert C.standard_deduction(3) == 209
    assert C.standard_deduction(4) == 223
    assert C.standard_deduction(5) == 261
    assert C.standard_deduction(6) == 299
    assert C.standard_deduction(9) == 299  # 6+ band


def test_bbce_gross_limit_is_200_percent_of_poverty():
    for size in range(1, 9):
        poverty_monthly = POVERTY_ANNUAL[size] / 12
        expected = _round_up(poverty_monthly * 2.0)
        assert C.bbce_gross_income_limit(size) == expected


def test_medicaid_screen_is_138_percent():
    for size in range(1, 6):
        poverty_monthly = POVERTY_ANNUAL[size] / 12
        expected = _round_up(poverty_monthly * 1.38)
        assert C.medicaid_adult_income_limit(size) == expected


def test_invalid_household_size_raises():
    with pytest.raises(ValueError):
        C.gross_income_limit(0)
    with pytest.raises(ValueError):
        C.net_income_limit(-1)
    with pytest.raises(ValueError):
        C.standard_deduction(0)
