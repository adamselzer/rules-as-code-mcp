"""Structured, recoverable errors for the MCP tools.

Half of MCP quality is what happens when something goes wrong. A model on the
other end of the wire should never see a stack trace; it should see a small,
structured object that tells it what failed, whether retrying could help, and
what to fix. Every error this server raises carries:

  - type:        a stable machine-readable code
  - message:     a human-readable explanation
  - recoverable: whether a corrected retry could succeed
  - hint:        the concrete next action for the caller
  - details:     optional structured context (e.g. field-level validation errors)

These are JSON-encoded into the MCP ToolError so the client receives them as a
parseable payload rather than prose.
"""

from __future__ import annotations

import json
from typing import Any


class RulesToolError(Exception):
    """Base class for all expected, structured tool errors."""

    type = "tool_error"
    recoverable = False

    def __init__(self, message: str, *, hint: str = "", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "type": self.type,
                "message": self.message,
                "recoverable": self.recoverable,
                "hint": self.hint,
                "details": self.details,
            }
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class InputValidationError(RulesToolError):
    """The arguments did not match the tool's schema or domain constraints."""

    type = "input_validation_error"
    recoverable = True


class AuthorizationError(RulesToolError):
    """The caller's scope is insufficient for this tool."""

    type = "authorization_error"
    recoverable = False


class NotFoundError(RulesToolError):
    """A referenced resource (e.g. a determination id) does not exist."""

    type = "not_found_error"
    recoverable = False


class ToolMisuseError(RulesToolError):
    """The tool was called in a way that does not make sense (e.g. unsupported program)."""

    type = "tool_misuse_error"
    recoverable = True
