"""Ruleset versioning.

Every determination this system emits is stamped with a ruleset version and the
policy effective period it was computed under. A version stamp is what lets a
caseworker, auditor, or court reproduce a determination months later: "show me
the rules that were in force on the date this decision was made."

The version string is intentionally tied to the federal fiscal year, because the
SNAP income standards and deductions are reissued by USDA FNS via an annual
cost-of-living adjustment (COLA) effective each October 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RulesetVersion:
    """An immutable stamp identifying which body of rules produced a result."""

    version: str
    program: str
    jurisdiction: str
    effective_start: date
    effective_end: date
    source_release: str

    def covers(self, on: date) -> bool:
        """True if this ruleset was in force on the given date."""
        return self.effective_start <= on <= self.effective_end

    def as_dict(self) -> dict[str, str]:
        return {
            "version": self.version,
            "program": self.program,
            "jurisdiction": self.jurisdiction,
            "effective_start": self.effective_start.isoformat(),
            "effective_end": self.effective_end.isoformat(),
            "source_release": self.source_release,
        }


# The SNAP ruleset currently shipped. FY2026 = the federal fiscal year running
# October 1, 2025 through September 30, 2026, under which the FY2026 COLA figures
# in constants.py are in force.
SNAP_RULESET = RulesetVersion(
    version="snap-mi-fy2026.1",
    program="SNAP",
    jurisdiction="MI",  # Michigan; income standards are federal, BBCE option is state-set
    effective_start=date(2025, 10, 1),
    effective_end=date(2026, 9, 30),
    source_release="USDA FNS FY2026 SNAP COLA (effective 2025-10-01)",
)
