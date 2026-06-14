# Eval report — rules-as-code core

Ruleset: `snap-mi-fy2026.1` (USDA FNS FY2026 SNAP COLA (effective 2025-10-01))
Labeled cases: 18

## Headline metrics

| Metric | Result |
|---|---|
| Decision accuracy | 100% (18/18) |
| Rule-trace correctness | 100% (18/18) |
| Citation correctness | 100% (18/18) |
| Net-income spot checks | 100% |
| Input-robustness | 100% (7/7) |

## Per-case results

| Case | Category | Decision | Rules | Citations | Net | Pass |
|---|---|---|---|---|---|---|
| `single-zero-income` | eligible | ok | ok | ok | ok | PASS |
| `single-low-earned` | eligible | ok | ok | ok | ok | PASS |
| `single-high-earned-gross-fail` | ineligible | ok | ok | ok | - | PASS |
| `single-unearned-net-fail` | ineligible | ok | ok | ok | ok | PASS |
| `single-unearned-just-eligible` | near_threshold | ok | ok | ok | ok | PASS |
| `single-net-exactly-at-limit` | near_threshold | ok | ok | ok | ok | PASS |
| `single-net-one-dollar-over` | near_threshold | ok | ok | ok | ok | PASS |
| `family3-earned-with-shelter` | eligible | ok | ok | ok | ok | PASS |
| `family4-mid-income-eligible` | eligible | ok | ok | ok | ok | PASS |
| `family4-high-income-net-fail` | ineligible | ok | ok | ok | ok | PASS |
| `elderly-low-income-eligible` | elderly | ok | ok | ok | ok | PASS |
| `elderly-uncapped-shelter-and-medical` | elderly | ok | ok | ok | ok | PASS |
| `nonelderly-shelter-capped` | eligible | ok | ok | ok | ok | PASS |
| `disabled-high-income-net-fail` | elderly | ok | ok | ok | ok | PASS |
| `family3-dependent-care-and-child-support` | eligible | ok | ok | ok | ok | PASS |
| `family2-earned-eligible` | eligible | ok | ok | ok | ok | PASS |
| `family5-earned-eligible` | eligible | ok | ok | ok | ok | PASS |
| `single-bbce-asset-waived` | eligible | ok | ok | ok | - | PASS |

## Input-robustness (malformed input must be rejected)

| Bad input | Rejected cleanly |
|---|---|
| empty household | ok |
| negative income | ok |
| negative shelter | ok |
| bad income kind | ok |
| non-numeric income | ok |
| implausible age | ok |
| unknown field | ok |
