"""AgentCore Platform v1.0 — HCR-C2-023 MedDRACodeChecker (inner subgraph node).

MedDRA term-coding validation, license-gated: when no MedDRA client is
provisioned (the MedDRA license is a customer-provided dependency),
this node degrades gracefully and returns a "gated"
verdict instead of failing the pipeline.
"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import from_json, to_json


class MedDRACodeCheckerNode(FunctionNode):
    """Inner subgraph node — trust authenticated once at the outer backbone."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, meddra_client: Any = None) -> None:
        super().__init__()
        self._meddra_client = meddra_client

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = from_json(state.get("user_input"), {})
        structured = payload.get("structured") if isinstance(payload, dict) else {}
        reaction_term = (structured or {}).get("reaction_term", "")

        if self._meddra_client is None:
            verdict = {"gated": True, "reason": "MedDRA license not provisioned — coding check skipped"}
            emit_trace_event(
                "meddra_check_gated",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {"meddra_verdict": to_json(verdict), "status": AgentStatus.SUCCESS.value}

        coded = self._meddra_client.lookup_term(reaction_term)
        verdict = {"gated": False, "reaction_term": reaction_term, "meddra_code": coded}

        emit_trace_event(
            "meddra_term_checked",
            {"correlation_id": state.get("correlation_id"), "matched": bool(coded)},
            state,
        )

        return {"meddra_verdict": to_json(verdict), "status": AgentStatus.SUCCESS.value}
