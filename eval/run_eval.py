"""Evaluation harness for the rules-as-code core.

Evaluation is the deliverable, not the demo. This runs the labeled cases in
cases.json against the determination engine and reports four things:

  1. Decision accuracy        -- does each determination match the labeled outcome?
  2. Rule-trace correctness   -- did the *right* rules fire for each case?
  3. Citation correctness     -- does each determination carry the expected citation?
  4. Net-income accuracy       -- where a case pins an expected net income, does it match?

It also runs a robustness suite at the model boundary (malformed input must be
rejected cleanly, not silently coerced). Server-level robustness -- auth failure
and tool misuse -- is exercised separately by eval/run_server_eval.py once the
MCP server is in place.

Run:  python eval/run_eval.py            (prints a report, writes eval/report.md)
      python eval/run_eval.py --check    (exit nonzero if anything fails; for CI)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from rules import Household, IncomeSource, Person, determine_snap_eligibility
from rules.snap import _round_dollar
from rules.version import SNAP_RULESET

CASES_PATH = Path(__file__).with_name("cases.json")
REPORT_PATH = Path(__file__).with_name("report.md")


@dataclass
class CaseResult:
    case_id: str
    category: str
    decision_ok: bool
    rules_ok: bool
    citations_ok: bool
    net_ok: bool | None  # None when the case pins no net income
    detail: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        checks = [self.decision_ok, self.rules_ok, self.citations_ok]
        if self.net_ok is not None:
            checks.append(self.net_ok)
        return all(checks)


def evaluate_case(case: dict) -> CaseResult:
    expected = case["expected"]
    det = determine_snap_eligibility(Household(**case["household"]))
    detail: list[str] = []

    decision_ok = det.decision == expected["decision"]
    if not decision_ok:
        detail.append(f"decision: expected {expected['decision']}, got {det.decision}")

    fired = {s.rule_id for s in det.rule_trace}
    must_fire = set(expected.get("must_fire", []))
    rules_ok = must_fire.issubset(fired)
    if not rules_ok:
        detail.append(f"missing rules: {sorted(must_fire - fired)}")

    labels = {c["label"] for c in det.citations}
    must_cite = set(expected.get("must_cite", []))
    citations_ok = must_cite.issubset(labels)
    if not citations_ok:
        detail.append(f"missing citations: {sorted(must_cite - labels)}")

    net_ok: bool | None = None
    if "net_income" in expected:
        # Compare against the SNAP-rounded net income that actually drives the
        # net-income test (round half up to the dollar), matching the engine.
        got = _round_dollar(det.computed["net_income"])
        net_ok = got == expected["net_income"]
        if not net_ok:
            detail.append(f"net_income: expected {expected['net_income']}, got {got}")

    return CaseResult(
        case_id=case["id"],
        category=case["category"],
        decision_ok=decision_ok,
        rules_ok=rules_ok,
        citations_ok=citations_ok,
        net_ok=net_ok,
        detail=detail,
    )


# --- Robustness at the model boundary --------------------------------------

ROBUSTNESS_CASES = [
    ("empty household", lambda: Household(members=[])),
    ("negative income", lambda: IncomeSource(kind="earned", monthly_amount=-100)),
    ("negative shelter", lambda: Household(members=[Person(age=30)], shelter_cost_monthly=-5)),
    ("bad income kind", lambda: IncomeSource(kind="lottery", monthly_amount=10)),
    ("non-numeric income", lambda: IncomeSource(kind="earned", monthly_amount="lots")),
    ("implausible age", lambda: Person(age=999)),
    ("unknown field", lambda: Household(members=[Person(age=30)], shelter_cost=900)),
]


def run_robustness() -> list[tuple[str, bool]]:
    """Each malformed input must raise a ValidationError, not silently pass."""
    results = []
    for label, thunk in ROBUSTNESS_CASES:
        try:
            thunk()
            results.append((label, False))  # should have raised
        except ValidationError:
            results.append((label, True))
        except Exception:
            results.append((label, False))  # wrong error type counts as a miss
    return results


def main(argv: list[str]) -> int:
    data = json.loads(CASES_PATH.read_text())
    cases = data["cases"]
    results = [evaluate_case(c) for c in cases]
    robustness = run_robustness()

    n = len(results)
    decision_acc = sum(r.decision_ok for r in results) / n
    rules_acc = sum(r.rules_ok for r in results) / n
    cite_acc = sum(r.citations_ok for r in results) / n
    net_checked = [r for r in results if r.net_ok is not None]
    net_acc = (sum(r.net_ok for r in net_checked) / len(net_checked)) if net_checked else 1.0
    robustness_acc = sum(ok for _, ok in robustness) / len(robustness)
    all_passed = all(r.passed for r in results) and all(ok for _, ok in robustness)

    report = render_report(
        results, robustness, decision_acc, rules_acc, cite_acc, net_acc, robustness_acc
    )
    print(report)
    REPORT_PATH.write_text(report)

    if "--check" in argv and not all_passed:
        print("\nFAIL: one or more checks did not pass.", file=sys.stderr)
        return 1
    return 0


def render_report(results, robustness, decision_acc, rules_acc, cite_acc, net_acc, robustness_acc) -> str:
    n = len(results)
    lines = [
        "# Eval report — rules-as-code core",
        "",
        f"Ruleset: `{SNAP_RULESET.version}` ({SNAP_RULESET.source_release})",
        f"Labeled cases: {n}",
        "",
        "## Headline metrics",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Decision accuracy | {decision_acc:.0%} ({sum(r.decision_ok for r in results)}/{n}) |",
        f"| Rule-trace correctness | {rules_acc:.0%} ({sum(r.rules_ok for r in results)}/{n}) |",
        f"| Citation correctness | {cite_acc:.0%} ({sum(r.citations_ok for r in results)}/{n}) |",
        f"| Net-income spot checks | {net_acc:.0%} |",
        f"| Input-robustness | {robustness_acc:.0%} ({sum(ok for _, ok in robustness)}/{len(robustness)}) |",
        "",
        "## Per-case results",
        "",
        "| Case | Category | Decision | Rules | Citations | Net | Pass |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        net = "-" if r.net_ok is None else ("ok" if r.net_ok else "FAIL")
        lines.append(
            f"| `{r.case_id}` | {r.category} | {_m(r.decision_ok)} | {_m(r.rules_ok)} | "
            f"{_m(r.citations_ok)} | {net} | {'PASS' if r.passed else 'FAIL'} |"
        )
    fails = [r for r in results if not r.passed]
    if fails:
        lines += ["", "## Failures", ""]
        for r in fails:
            lines.append(f"- `{r.case_id}`: {'; '.join(r.detail)}")
    lines += ["", "## Input-robustness (malformed input must be rejected)", "",
              "| Bad input | Rejected cleanly |", "|---|---|"]
    for label, ok in robustness:
        lines.append(f"| {label} | {_m(ok)} |")
    lines.append("")
    return "\n".join(lines)


def _m(ok: bool) -> str:
    return "ok" if ok else "FAIL"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
