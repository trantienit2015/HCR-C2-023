"""AgentCore Platform v1.0 — HCR-C2-023 deterministic validation rule functions.

Pure functions, no framework/agenticstar imports — unit-testable directly and
reused from the inner-subgraph nodes (E2BFieldValidatorNode,
PMDAFormatCheckerNode, AESeverityClassifyNode).
"""

from typing import Any
import re

E2B_MANDATORY_FIELDS = [
    "patient_initials",
    "patient_dob_or_age",
    "patient_sex",
    "reaction_term",
    "reaction_onset_date",
    "reporter_type",
    "suspect_drug",
    "outcome",
]

PMDA_ALLOWED_REPORTER_TYPES = ("physician", "pharmacist", "nurse", "sponsor")

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

_SERIOUS_FLAGS = ("death", "life_threatening", "hospitalization", "disability", "congenital_anomaly")


def validate_e2b_fields(structured: dict[str, Any]) -> list[dict[str, Any]]:
    """ICH E2B(R3) mandatory/conditional field check. Returns per-field verdicts."""
    verdicts = []
    for field in E2B_MANDATORY_FIELDS:
        present = bool(structured.get(field))
        verdicts.append(
            {
                "field": field,
                "mandatory": True,
                "present": present,
                "verdict": "PASS" if present else "FAIL",
            }
        )

    # Conditional field: death_date required when outcome is fatal.
    if structured.get("outcome") == "fatal":
        present = bool(structured.get("death_date"))
        verdicts.append(
            {
                "field": "death_date",
                "mandatory": True,
                "present": present,
                "verdict": "PASS" if present else "FAIL",
                "reason": "conditional — required when outcome=fatal",
            }
        )

    return verdicts


def check_pmda_format(structured: dict[str, Any]) -> dict[str, Any]:
    """Deterministic PMDA-specific submission format check."""
    issues: list[str] = []

    reporter_type = structured.get("reporter_type")
    if reporter_type and reporter_type not in PMDA_ALLOWED_REPORTER_TYPES:
        issues.append(f"reporter_type '{reporter_type}' not a recognized PMDA reporter category")

    for date_field in ("reaction_onset_date", "death_date"):
        value = structured.get(date_field)
        if value and not _ISO_DATE.fullmatch(str(value)):
            issues.append(f"{date_field} '{value}' is not YYYY-MM-DD format required by PMDA")

    return {"format_issues": issues, "verdict": "PASS" if not issues else "FAIL"}


def classify_severity(structured: dict[str, Any]) -> str:
    """Deterministic ICH E2 serious/non-serious severity classification."""
    for flag in _SERIOUS_FLAGS:
        if structured.get(flag):
            return "serious"
    if structured.get("outcome") == "fatal":
        return "serious"
    return "non-serious"
