"""Rule -> policy citation mapping.

The thesis of this project: in government, "the model said so" is not a basis for
denying benefits. Every rule that can fire in a determination carries a citation
back to the authority behind it, so a determination is explainable to a caseworker,
an auditor, or a court.

Each citation names the authority, the section, and a public URL. Where a federal
rule (statute or regulation) is the controlling authority, we cite it; where a
figure is set by the annual USDA COLA, we cite the COLA release; where a state
exercises an option (Michigan's broad-based categorical eligibility), we cite the
state manual section.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """A pointer to the policy authority behind a single rule."""

    authority: str  # e.g. "7 CFR", "USDA FNS", "Michigan BEM"
    section: str  # e.g. "273.9(a)", "FY2026 COLA", "556"
    title: str  # human-readable description of what the section says
    url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "authority": self.authority,
            "section": self.section,
            "title": self.title,
            "url": self.url,
            "label": f"{self.authority} {self.section}",
        }


# Keyed by rule_id. Every rule_id emitted in a rule trace MUST appear here; a unit
# test enforces that, so a rule can never fire without a citation behind it.
CITATIONS: dict[str, Citation] = {
    "snap.gross_income_test": Citation(
        authority="7 CFR",
        section="273.9(a)(1)",
        title="Gross income eligibility standard: monthly gross income at or below 130% of the federal poverty guidelines.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.net_income_test": Citation(
        authority="7 CFR",
        section="273.9(a)(2)",
        title="Net income eligibility standard: monthly net income at or below 100% of the federal poverty guidelines.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.income_standards": Citation(
        authority="USDA FNS",
        section="FY2026 COLA",
        title="FY2026 SNAP monthly income eligibility standards (130% and 100% of poverty), 48 contiguous states and DC, effective 2025-10-01.",
        url="https://www.fns.usda.gov/snap/allotment/COLA",
    ),
    "snap.earned_income_deduction": Citation(
        authority="7 CFR",
        section="273.9(d)(2)",
        title="20% deduction from gross earned income.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.standard_deduction": Citation(
        authority="USDA FNS",
        section="FY2026 COLA",
        title="FY2026 standard deduction by household size, 48 contiguous states and DC.",
        url="https://www.fns.usda.gov/snap/allotment/COLA",
    ),
    "snap.dependent_care_deduction": Citation(
        authority="7 CFR",
        section="273.9(d)(4)",
        title="Deduction for actual costs of dependent care needed for work, training, or education.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.child_support_deduction": Citation(
        authority="7 CFR",
        section="273.9(d)(5)",
        title="Deduction for legally obligated child support paid to a non-household member.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.medical_deduction": Citation(
        authority="7 CFR",
        section="273.9(d)(3)",
        title="Deduction for out-of-pocket medical expenses over $35/month for elderly (60+) or disabled members.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.excess_shelter_deduction": Citation(
        authority="7 CFR",
        section="273.9(d)(6)",
        title="Excess shelter deduction: shelter costs over half of income after other deductions, capped except for households with an elderly or disabled member.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.elderly_disabled_gross_exemption": Citation(
        authority="7 CFR",
        section="273.9(a)(2)",
        title="Households with an elderly (60+) or disabled member are exempt from the gross income test and apply only the net income test.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.9",
    ),
    "snap.bbce": Citation(
        authority="Michigan BEM",
        section="213",
        title="FAP categorical eligibility: broad-based categorical eligibility raises the gross income limit to 200% of poverty and waives the asset test for most food assistance groups.",
        url="https://dhhs.michigan.gov/OLMWEB/EX/BP/Public/BEM/213.pdf",
    ),
    "snap.asset_test": Citation(
        authority="7 CFR",
        section="273.8",
        title="Resource (asset) limits; waived for households qualifying under broad-based categorical eligibility.",
        url="https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-D/section-273.8",
    ),
    "medicaid.magi_adult_screen": Citation(
        authority="42 CFR",
        section="435.119",
        title="Medicaid eligibility for the adult expansion group at or below 138% of the federal poverty level (MAGI-based, simplified income screen only).",
        url="https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-435",
    ),
}


def citation_for(rule_id: str) -> Citation:
    """Return the citation for a rule_id, or raise if the rule has none.

    Raising (rather than returning a default) is deliberate: a rule with no
    citation is a bug in this domain, and we want it to fail loudly in tests.
    """
    try:
        return CITATIONS[rule_id]
    except KeyError as exc:  # pragma: no cover - guarded by test_citations
        raise KeyError(f"No citation registered for rule_id {rule_id!r}") from exc
