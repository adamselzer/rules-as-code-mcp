"""The MCP server: tool registration, scope enforcement, and error translation.

This is the boundary the spec is really about. The model orchestrates; the
determination is made by the deterministic core in rules/. The server's job is to
expose that core as a handful of sharp tools, resolve the caller's scope from the
request context (never from a model-supplied argument), and translate the core's
structured errors into clean MCP ToolErrors a model can recover from.

Transports:
  - stdio (default): how Claude Desktop / Claude Code connect. Role comes from
    RULES_MCP_ROLE (screening | caseworker).
  - streamable-http: production path; scope comes from the OAuth bearer token
    validated by SimpleTokenVerifier.

Run:
  python -m server.main                 # stdio, screening role
  RULES_MCP_ROLE=caseworker python -m server.main
  python -m server.main --http          # streamable-http on 127.0.0.1:8000
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from rules.models import Determination, Household
from rules.version import SNAP_RULESET

from .auth import resolve_scopes
from .errors import RulesToolError
from . import tools as T

INSTRUCTIONS = f"""\
Deterministic SNAP eligibility tools for {SNAP_RULESET.jurisdiction}, ruleset \
{SNAP_RULESET.version}.

The eligibility determination is made by versioned, tested, cited code -- not by a \
model. Every determination returns the result, the rule trace, and the policy \
citation behind each rule. Use screen_programs for an anonymous coarse signal; use \
check_program_eligibility for a full, auditable determination (requires the \
caseworker scope).
"""

mcp = FastMCP(name="rules-as-code-mcp", instructions=INSTRUCTIONS)


def _guard(fn, *args):
    """Run tool logic, translating structured errors into MCP ToolErrors."""
    try:
        return fn(*args, resolve_scopes())
    except RulesToolError as exc:
        raise ToolError(exc.to_json()) from exc


@mcp.tool(
    title="Screen programs",
    description=(
        "Coarse, anonymous-safe screen of a household across SNAP and a simplified "
        "Medicaid income check. Returns a 'likely eligible' signal per program with a "
        "citation. This is NOT a determination and stores no data. Available to the "
        "screening scope. For a real determination, use check_program_eligibility."
    ),
)
def screen_programs(household: Household) -> T.ScreeningResult:
    return _guard(T.logic_screen_programs, household)


@mcp.tool(
    title="Check program eligibility",
    description=(
        "Run the full deterministic SNAP financial eligibility test for a household. "
        "Returns the decision PLUS the rule trace and the policy citation behind every "
        "rule that fired, plus the ruleset version -- never a bare yes/no. Requires the "
        "caseworker scope. 'program' must be 'SNAP'."
    ),
)
def check_program_eligibility(program: str, household: Household) -> Determination:
    return _guard(T.logic_check_program_eligibility, program, household)


@mcp.tool(
    title="List required verifications",
    description=(
        "List the documents a caseworker must verify to confirm SNAP eligibility for a "
        "household, derived from the facts the household presents (earned income implies "
        "pay stubs, shelter costs imply a lease, and so on). Requires the caseworker scope."
    ),
)
def list_required_verifications(program: str, household: Household) -> T.VerificationResult:
    return _guard(T.logic_list_required_verifications, program, household)


@mcp.tool(
    title="Explain determination",
    description=(
        "Return a plain, step-by-step trace of a prior determination by its id: which "
        "rules fired, what they saw, and the citation behind each. Requires the caseworker "
        "scope. Use the determination_id returned by check_program_eligibility."
    ),
)
def explain_determination(determination_id: str) -> T.ExplanationResult:
    return _guard(T.logic_explain_determination, determination_id)


@mcp.tool(
    title="Look up policy",
    description=(
        "Answer a SNAP policy question with citations to the eligibility manual. "
        "Delegates to the policy-manual-rag retrieval index. Currently a stub that returns "
        "an explicit placeholder rather than an invented answer. Available to the screening scope."
    ),
)
def lookup_policy(question: str) -> T.PolicyAnswer:
    return _guard(T.logic_lookup_policy, question)


def main() -> None:
    transport = "streamable-http" if "--http" in sys.argv[1:] else "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
