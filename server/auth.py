"""Scoped permissions: anonymous screening vs authenticated caseworker.

The boundary this models: anyone can run an anonymous *screen* (coarse "you might
qualify" signals, no PII, no stored determinations). Only an authenticated
*caseworker* can run a full determination, list verifications tied to a case, or
pull a stored determination back up by id.

Two scopes, with caseworker implying screening:

    screening   -> screen_programs, lookup_policy
    caseworker  -> everything, plus the screening tools

How scope is resolved depends on transport, and we are honest about that:

  - Over streamable-http with OAuth, scope comes from the verified bearer token
    (SimpleTokenVerifier maps a token to its scopes). This is the production path.
  - Over stdio (Claude Desktop / Claude Code), there is no bearer token, so the
    deployment's role is read from the RULES_MCP_ROLE environment variable. This
    is how the local client demo selects a role.

Resolving scope from a request context (never from a tool argument the model
controls) is the point: the model cannot escalate its own privileges.
"""

from __future__ import annotations

import os

from mcp.server.auth.provider import AccessToken, TokenVerifier

SCREENING = "screening"
CASEWORKER = "caseworker"

# caseworker is a superset of screening.
_ROLE_SCOPES = {
    "screening": frozenset({SCREENING}),
    "caseworker": frozenset({SCREENING, CASEWORKER}),
}

# Demonstration tokens for the OAuth/HTTP path. In a real deployment these are
# issued and validated by an identity provider; here they are static so the
# client demo and the eval can exercise both roles. They are not secrets and
# grant access to synthetic data only.
_DEMO_TOKENS = {
    "demo-screening-token": frozenset({SCREENING}),
    "demo-caseworker-token": frozenset({SCREENING, CASEWORKER}),
}


def scopes_for_role(role: str) -> frozenset[str]:
    """Map a role name to its scope set; unknown roles get screening only."""
    return _ROLE_SCOPES.get(role.strip().lower(), frozenset({SCREENING}))


def scopes_from_env() -> frozenset[str]:
    """Resolve scopes for the stdio transport from RULES_MCP_ROLE (default screening)."""
    return scopes_for_role(os.environ.get("RULES_MCP_ROLE", "screening"))


def resolve_scopes() -> frozenset[str]:
    """Resolve the active caller's scopes.

    Prefer a verified OAuth token (HTTP transport); fall back to the environment
    role (stdio transport). Never trust a value the model itself supplied.
    """
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        if token is not None:
            return frozenset(token.scopes)
    except Exception:
        # No auth middleware in scope (e.g. stdio): fall through to env role.
        pass
    return scopes_from_env()


class SimpleTokenVerifier(TokenVerifier):
    """Validate a bearer token against the demonstration token table."""

    async def verify_token(self, token: str) -> AccessToken | None:
        scopes = _DEMO_TOKENS.get(token)
        if scopes is None:
            return None
        return AccessToken(
            token=token,
            client_id="demo-client",
            scopes=list(scopes),
            expires_at=None,
        )
