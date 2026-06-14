"""Tool logic: pure functions behind the MCP tools.

Each function takes the caller's resolved scopes explicitly, so the logic is
fully testable without a live server or transport. The FastMCP layer in main.py
resolves scopes from the request context and forwards them here; it never lets
the model choose its own scope.

These functions raise the structured errors in errors.py. main.py translates
those into MCP ToolErrors. Input parsing goes through parse_household, which
turns a pydantic ValidationError into a recoverable InputValidationError with
field-level detail a model can act on.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from rules import determine_snap_eligibility, required_verifications, screen_programs
from rules.models import Determination, Household

from .auth import CASEWORKER, SCREENING
from .errors import (
    AuthorizationError,
    InputValidationError,
    NotFoundError,
    ToolMisuseError,
)
from .store import STORE

SUPPORTED_PROGRAMS = {"SNAP"}


# --- Response models --------------------------------------------------------


class ScreeningResult(BaseModel):
    """Coarse, anonymous-safe cross-program screen. Not a determination."""

    disclaimer: str
    household_size: int
    screens: list[dict[str, Any]]


class VerificationResult(BaseModel):
    program: str
    household_size: int
    verifications: list[dict[str, Any]]


class ExplanationResult(BaseModel):
    determination_id: str
    program: str
    decision: str
    summary: str
    ruleset_version: dict[str, str]
    steps: list[dict[str, Any]]


class PolicyAnswer(BaseModel):
    """Stub response for lookup_policy until the policy-manual-rag index is wired in."""

    question: str
    answer: str
    citations: list[dict[str, str]]
    source: str
    stub: bool


# --- Helpers ----------------------------------------------------------------


def require_scope(scopes: frozenset[str], needed: str) -> None:
    if needed not in scopes:
        raise AuthorizationError(
            f"This tool requires the '{needed}' scope.",
            hint=(
                "Authenticate as a caseworker. Over HTTP, present a bearer token "
                "with the caseworker scope; over stdio, launch the server with "
                "RULES_MCP_ROLE=caseworker."
            ),
            details={"required_scope": needed, "granted_scopes": sorted(scopes)},
        )


def parse_household(data: Any) -> Household:
    # Accept an already-validated model (the typed MCP path) or a raw dict (direct
    # and eval calls). Anything else is a usage error.
    if isinstance(data, Household):
        return data
    if not isinstance(data, dict):
        raise InputValidationError(
            "The 'household' argument must be an object.",
            hint="Pass household as a JSON object with a 'members' array.",
            details={"received_type": type(data).__name__},
        )
    try:
        return Household(**data)
    except ValidationError as exc:
        raise InputValidationError(
            "The household failed validation.",
            hint="Fix the listed fields and retry. Monetary fields must be non-negative numbers.",
            details={"validation_errors": exc.errors(include_url=False, include_input=False)},
        ) from exc


def _require_supported_program(program: str) -> str:
    norm = program.strip().upper()
    if norm not in SUPPORTED_PROGRAMS:
        raise ToolMisuseError(
            f"Program {program!r} is not supported.",
            hint=f"Supported programs: {sorted(SUPPORTED_PROGRAMS)}. This server determines SNAP.",
            details={"supported_programs": sorted(SUPPORTED_PROGRAMS)},
        )
    return norm


# --- Tool logic -------------------------------------------------------------


def logic_screen_programs(household: Any, scopes: frozenset[str]) -> ScreeningResult:
    require_scope(scopes, SCREENING)
    hh = parse_household(household)
    screens = [s.model_dump() for s in screen_programs(hh)]
    return ScreeningResult(
        disclaimer=(
            "Screening only: a coarse signal of likely eligibility, not a determination. "
            "No personal information is collected or stored. Run check_program_eligibility "
            "for a full, cited determination."
        ),
        household_size=hh.size,
        screens=screens,
    )


def logic_check_program_eligibility(
    program: str, household: Any, scopes: frozenset[str]
) -> Determination:
    require_scope(scopes, CASEWORKER)
    _require_supported_program(program)
    hh = parse_household(household)
    det = determine_snap_eligibility(hh, include_pii=False)
    STORE.put(det)
    return det


def logic_list_required_verifications(
    program: str, household: Any, scopes: frozenset[str]
) -> VerificationResult:
    require_scope(scopes, CASEWORKER)
    norm = _require_supported_program(program)
    hh = parse_household(household)
    items = [v.model_dump() for v in required_verifications(norm, hh)]
    return VerificationResult(program=norm, household_size=hh.size, verifications=items)


def logic_explain_determination(determination_id: str, scopes: frozenset[str]) -> ExplanationResult:
    require_scope(scopes, CASEWORKER)
    det = STORE.get(determination_id)
    if det is None:
        raise NotFoundError(
            f"No determination found with id {determination_id!r}.",
            hint="Run check_program_eligibility first; use the determination_id it returns.",
            details={"known_count": len(STORE)},
        )
    steps = [
        {
            "rule": s.rule_id,
            "explanation": s.description,
            "inputs": s.inputs,
            "result": s.result,
            "passed": s.passed,
            "citation": s.citation["label"],
            "citation_url": s.citation["url"],
        }
        for s in det.rule_trace
    ]
    return ExplanationResult(
        determination_id=det.determination_id,
        program=det.program,
        decision=det.decision,
        summary=det.summary,
        ruleset_version=det.ruleset_version,
        steps=steps,
    )


def logic_lookup_policy(question: str, scopes: frozenset[str]) -> PolicyAnswer:
    require_scope(scopes, SCREENING)
    if not question or not question.strip():
        raise InputValidationError(
            "The 'question' argument must be a non-empty string.",
            hint="Pass a policy question, e.g. 'How is self-employment income counted?'",
        )
    # Stub: this will delegate to the policy-manual-rag retrieval index. Until
    # that repo is wired in, return an explicit, honest placeholder rather than
    # an invented policy answer -- fabricating policy here is exactly the failure
    # this whole project exists to prevent.
    return PolicyAnswer(
        question=question.strip(),
        answer=(
            "Policy lookup is not yet connected. This tool will delegate to the "
            "policy-manual-rag retrieval index, which returns answers grounded in "
            "the Bridges Eligibility Manual with inline section citations. Until "
            "then, no policy answer is fabricated."
        ),
        citations=[],
        source="policy-manual-rag (not yet connected)",
        stub=True,
    )
