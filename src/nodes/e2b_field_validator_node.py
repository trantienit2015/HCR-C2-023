"""AgentCore Platform v1.0 — HCR-C2-023 E2BFieldValidator (inner subgraph node).

Deterministic ICH E2B(R3) mandatory/conditional field check.
"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json, to_json
from src.services.validation_rules import validate_e2b_fields


class E2BFieldValidatorNode(FunctionNode):
    """Inner subgraph node — trust authenticated once at the outer backbone."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = from_json(state.get("user_input"), {})
        structured = payload.get("structured") if isinstance(payload, dict) else None

        if not isinstance(structured, dict) or not structured:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["E2BFieldValidatorNode: no structured AE fields in input"],
            }

        verdicts = validate_e2b_fields(structured)
        fail_count = sum(1 for v in verdicts if v["verdict"] == "FAIL")

        emit_trace_event(
            "e2b_fields_validated",
            {"correlation_id": state.get("correlation_id"), "fail_count": fail_count},
            state,
        )

        return {
            "field_verdicts": to_json(verdicts),
            "status": AgentStatus.SUCCESS.value,
        }
