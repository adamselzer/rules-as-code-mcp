"""Server-level robustness eval: auth failure, tool misuse, and bad input.

The core eval (run_eval.py) measures whether determinations are correct. This
measures whether the server fails *safely*: every bad call must produce a clean,
structured, correctly-typed error, never a crash and never a determination the
caller wasn't authorized to get. It writes a failure-case table to
eval/server_report.md -- "show the structured response" for each.

Run:  python eval/run_server_eval.py            (prints + writes the report)
      python eval/run_server_eval.py --check     (exit nonzero on any miss)
"""

from __future__ import annotations

import sys
from pathlib import Path

from server import tools as T
from server.auth import scopes_for_role
from server.errors import (
    AuthorizationError,
    InputValidationError,
    NotFoundError,
    RulesToolError,
    ToolMisuseError,
)

REPORT_PATH = Path(__file__).with_name("server_report.md")

SCREENING = scopes_for_role("screening")
CASEWORKER = scopes_for_role("caseworker")
HH = {"members": [{"age": 30}], "income": [{"kind": "earned", "monthly_amount": 1000}]}


# Each robustness case: (label, callable, expected error type, expected recoverable)
CASES = [
    (
        "Screening scope tries a determination (privilege escalation)",
        lambda: T.logic_check_program_eligibility("SNAP", HH, SCREENING),
        AuthorizationError,
        False,
    ),
    (
        "Screening scope tries to list verifications",
        lambda: T.logic_list_required_verifications("SNAP", HH, SCREENING),
        AuthorizationError,
        False,
    ),
    (
        "Screening scope tries to explain a determination",
        lambda: T.logic_explain_determination("snap-x", SCREENING),
        AuthorizationError,
        False,
    ),
    (
        "Unsupported program (tool misuse)",
        lambda: T.logic_check_program_eligibility("TANF", HH, CASEWORKER),
        ToolMisuseError,
        True,
    ),
    (
        "Unknown determination id",
        lambda: T.logic_explain_determination("snap-does-not-exist", CASEWORKER),
        NotFoundError,
        False,
    ),
    (
        "Empty household (semantic validation)",
        lambda: T.logic_check_program_eligibility("SNAP", {"members": []}, CASEWORKER),
        InputValidationError,
        True,
    ),
    (
        "Negative income (domain constraint)",
        lambda: T.logic_check_program_eligibility(
            "SNAP", {"members": [{"age": 30}], "income": [{"kind": "earned", "monthly_amount": -5}]}, CASEWORKER
        ),
        InputValidationError,
        True,
    ),
    (
        "Household is not an object",
        lambda: T.logic_screen_programs("oops", SCREENING),
        InputValidationError,
        True,
    ),
    (
        "Empty policy question",
        lambda: T.logic_lookup_policy("", SCREENING),
        InputValidationError,
        True,
    ),
]


def run() -> tuple[list[dict], bool]:
    rows = []
    all_ok = True
    for label, thunk, expected_type, expected_recoverable in CASES:
        try:
            thunk()
            rows.append({"case": label, "outcome": "NO ERROR (leak!)", "ok": False, "response": "{}"})
            all_ok = False
        except RulesToolError as exc:
            type_ok = isinstance(exc, expected_type)
            rec_ok = exc.recoverable == expected_recoverable
            ok = type_ok and rec_ok
            all_ok = all_ok and ok
            rows.append(
                {
                    "case": label,
                    "outcome": exc.type,
                    "recoverable": exc.recoverable,
                    "ok": ok,
                    "response": exc.to_json(),
                }
            )
        except Exception as exc:  # an unstructured crash is a failure
            rows.append({"case": label, "outcome": f"UNSTRUCTURED: {type(exc).__name__}", "ok": False, "response": str(exc)})
            all_ok = False
    return rows, all_ok


def render(rows: list[dict], all_ok: bool) -> str:
    passed = sum(1 for r in rows if r["ok"])
    lines = [
        "# Server robustness report",
        "",
        "Every bad call must produce a clean, correctly-typed structured error -- "
        "never a crash, never an unauthorized result.",
        "",
        f"**Result: {passed}/{len(rows)} failure cases handled cleanly.**",
        "",
        "| Failure case | Error type | Handled cleanly |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['case']} | `{r['outcome']}` | {'ok' if r['ok'] else 'FAIL'} |")
    lines += ["", "## Structured responses", ""]
    for r in rows:
        lines.append(f"**{r['case']}**")
        lines.append("")
        lines.append("```json")
        lines.append(r["response"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    rows, all_ok = run()
    report = render(rows, all_ok)
    print(report)
    REPORT_PATH.write_text(report)
    if "--check" in argv and not all_ok:
        print("\nFAIL: a robustness case was not handled cleanly.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
