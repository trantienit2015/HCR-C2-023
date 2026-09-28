"""AgentCore Platform v1.0 — HCR-C2-023 ValidationReportGenerate (outer post_process, S-1+S-3).

Step 5: LLM-generated field-by-field remediation guidance narrative. S-3
non-suppressible gate keeps PMDA-flagged items in the final report — if the
assembled report were to drop a PMDA format issue, the node fails closed
rather than silently suppressing a regulatory-critical flag (S-3 preservation
variant).
"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json, to_json


class ValidationReportGenerateNode(FunctionNode):
    """Outer post_process: assemble the field-by-field validation report."""

    # S-1: outer boundary node — matches agent.yaml required_trust_level.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self, llm: Any = None) -> None:
        super().__init__()
        self._llm = llm

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        field_verdicts = from_json(state.get("field_verdicts"), [])
        meddra_verdict = from_json(state.get("meddra_verdict"), {})
        pmda_verdict = from_json(state.get("pmda_verdict"), {})
        severity_tier = state.get("severity_tier", "")

        if not field_verdicts:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["ValidationReportGenerateNode: no field verdicts to report on"],
            }

        pmda_flags = list(pmda_verdict.get("format_issues", []))
        failed_fields = [v["field"] for v in field_verdicts if v.get("verdict") == "FAIL"]

        remediation_guidance = self._generate_remediation(failed_fields, pmda_flags, meddra_verdict, severity_tier)

        report = {
            "field_verdicts": field_verdicts,
            "meddra_verdict": meddra_verdict,
            "pmda_verdict": pmda_verdict,
            "severity_tier": severity_tier,
            "remediation_guidance": remediation_guidance,
            # Echoed here (not re-derived from pmda_verdict alone) so the S-3
            # hook re-checks this node's OWN execute() output for internal
            # consistency, per the "own-output self-consistency" pattern.
            "pmda_flags": pmda_flags,
        }

        emit_trace_event(
            "validation_report_generated",
            {
                "correlation_id": state.get("correlation_id"),
                "failed_field_count": len(failed_fields),
                "pmda_flag_count": len(pmda_flags),
            },
            state,
        )

        return {
            "validation_report": to_json(report),
            "pmda_flags": to_json(pmda_flags),
            "status": AgentStatus.SUCCESS.value,
        }

    def _generate_remediation(
        self, failed_fields: Any, pmda_flags: Any, meddra_verdict: Any, severity_tier: Any
    ) -> str:
        if self._llm is None:
            return "LLM remediation unavailable — see field_verdicts/pmda_verdict for raw findings."
        prompt = (
            f"Failed E2B(R3) fields: {failed_fields}. PMDA format issues: {pmda_flags}. "
            f"MedDRA verdict: {meddra_verdict}. Severity: {severity_tier}. "
            "Write concise field-by-field remediation guidance for the CRO regulatory-affairs submitter."
        )
        return self._normalize_completion(self._llm.complete(prompt))

    @staticmethod
    def _normalize_completion(result: Any) -> str:
        """Some LLM clients return {"content": "..."} / {"text": "..."} instead of a
        bare string — normalize before the result is embedded as report text."""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return str(result.get("content") or result.get("text") or result)
        return str(result)

    def _extra_security_gate_output(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-3 preservation variant (non-suppressible PMDA flags).

        Re-checks the two keys this node's own execute() just returned
        (pmda_flags + validation_report) for internal consistency — every
        PMDA flag computed for this invocation must still be present inside
        the assembled report. Never returns None, never raises.
        """
        pmda_flags = from_json(state.get("pmda_flags"), [])
        report = from_json(state.get("validation_report"), {})
        report_flags = report.get("pmda_flags", []) if isinstance(report, dict) else []

        missing = [f for f in pmda_flags if f not in report_flags]
        if missing:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    f"ValidationReportGenerateNode S-3: PMDA flag(s) {missing} suppressed from validation_report"
                ],
            }
        return state
