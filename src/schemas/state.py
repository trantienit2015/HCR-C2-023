"""AgentCore Platform v1.0 — HCR-C2-023 state schema.

Clinical Trial Adverse Event (AE) Report Validation Agent. Flat TypedDict
extension of AgentState (ADR-005). Compound payloads (dict/list) are
JSON-string-encoded before being stored in state fields (to_json/from_json
helpers below), and every agent-specific field is wrapped in NotRequired
(state-safety rule — absence from a resumed checkpoint must not KeyError mid-pipeline).
"""

import json
from typing import Any, NotRequired

from framework.schemas.agent_state import AgentState


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def from_json(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """Agent state for HCR-C2-023.

    field_verdicts: JSON list[dict] — ICH E2B(R3) mandatory/conditional field verdicts.
    meddra_verdict: JSON dict — MedDRA term-coding verdict (license-gated;
      {"gated": true, ...} when no MedDRA license/client is provisioned).
    pmda_verdict: JSON dict — PMDA-specific submission format verdict.
    severity_tier: "serious" | "non-serious" — ICH E2 severity classification.
    validation_report: JSON dict — field-by-field validation report incl. LLM
      remediation guidance narrative.
    pmda_flags: JSON list[str] — non-suppressible PMDA format issues, echoed
      by ValidationReportGenerateNode.execute() for its own S-3 preservation
      re-check (own-output self-consistency, not a cross-state re-derive).
    """

    field_verdicts: NotRequired[str]  # type: ignore[valid-type]
    meddra_verdict: NotRequired[str]  # type: ignore[valid-type]
    pmda_verdict: NotRequired[str]  # type: ignore[valid-type]
    severity_tier: NotRequired[str]  # type: ignore[valid-type]
    validation_report: NotRequired[str]  # type: ignore[valid-type]
    pmda_flags: NotRequired[str]  # type: ignore[valid-type]
