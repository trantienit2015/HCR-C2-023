"""AgentCore Platform v1.0 — HCR-C2-023 PMDAFormatChecker (inner subgraph node).

Deterministic PMDA-specific submission format check.
"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json, to_json
from src.services.validation_rules import check_pmda_format


class PMDAFormatCheckerNode(FunctionNode):
    """Inner subgraph node — trust authenticated once at the outer backbone."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = from_json(state.get("user_input"), {})
        structured = payload.get("structured") if isinstance(payload, dict) else None

        if not isinstance(structured, dict) or not structured:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PMDAFormatCheckerNode: no structured AE fields in input"],
            }

        verdict = check_pmda_format(structured)

        emit_trace_event(
            "pmda_format_checked",
            {"correlation_id": state.get("correlation_id"), "issue_count": len(verdict["format_issues"])},
            state,
        )

        return {"pmda_verdict": to_json(verdict), "status": AgentStatus.SUCCESS.value}
