"""Tests for scope resolution and the demonstration token verifier."""

from __future__ import annotations

import asyncio

from server.auth import (
    CASEWORKER,
    SCREENING,
    SimpleTokenVerifier,
    scopes_for_role,
    scopes_from_env,
)


def test_role_to_scopes():
    assert scopes_for_role("screening") == frozenset({SCREENING})
    assert scopes_for_role("caseworker") == frozenset({SCREENING, CASEWORKER})


def test_caseworker_is_superset_of_screening():
    assert SCREENING in scopes_for_role("caseworker")


def test_unknown_role_defaults_to_screening():
    assert scopes_for_role("administrator") == frozenset({SCREENING})
    assert scopes_for_role("") == frozenset({SCREENING})


def test_env_role_resolution(monkeypatch):
    monkeypatch.setenv("RULES_MCP_ROLE", "caseworker")
    assert CASEWORKER in scopes_from_env()
    monkeypatch.delenv("RULES_MCP_ROLE", raising=False)
    assert scopes_from_env() == frozenset({SCREENING})  # default


def test_token_verifier_maps_known_tokens():
    v = SimpleTokenVerifier()
    tok = asyncio.run(v.verify_token("demo-caseworker-token"))
    assert tok is not None
    assert CASEWORKER in tok.scopes


def test_token_verifier_rejects_unknown_tokens():
    v = SimpleTokenVerifier()
    assert asyncio.run(v.verify_token("forged")) is None
