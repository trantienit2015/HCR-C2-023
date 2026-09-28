"""AgentCore Platform v1.0 — HCR-C2-023 AESeverityClassify (inner subgraph node).

Deterministic ICH E2 serious/non-serious severity classification.
"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json
from src.services.validation_rules import classify_severity


class AESeverityClassifyNode(FunctionNode):
    """Inner subgraph node — trust authenticated once at the outer backbone."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = from_json(state.get("user_input"), {})
        structured = payload.get("structured") if isinstance(payload, dict) else None

        if not isinstance(structured, dict) or not structured:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["AESeverityClassifyNode: no structured AE fields in input"],
            }

        severity_tier = classify_severity(structured)

        emit_trace_event(
            "ae_severity_classified",
            {"correlation_id": state.get("correlation_id"), "severity_tier": severity_tier},
            state,
        )

        return {"severity_tier": severity_tier, "status": AgentStatus.SUCCESS.value}
