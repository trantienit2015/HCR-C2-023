"""AgentCore Platform v1.0 — HCR-C2-023 InputValidate (outer pre_process, S-1+S-2).

Step 1: schema validation of the E2B(R3) structured payload + S-2 incidental-
PHI scan of the free-text AE narrative. Scope (docs/02_design.md): the
"no PHI" claim applies only to structured metadata fields (patient_initials
is an E2B-permitted pseudonym, not raw PHI); the free-text narrative is
scanned for incidental PHI leakage (MRN, phone number, a full patient name
in prose) and rejected if found.
"""

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import to_json

_REQUIRED_TOP_LEVEL = ("structured", "narrative")

# Incidental-PHI patterns in free-text narrative (S-2 domain check, scope
# limited per docs/02_design.md — MRN, phone numbers, "patient name: X Y").
_PHI_PATTERNS = re.compile(
    r"(MRN[\s:#]*\d{4,}|\b\d{3}-\d{3,4}-\d{4}\b|patient name[\s:]+[A-Z][a-z]+\s+[A-Z][a-z]+)",
    re.IGNORECASE,
)


class InputValidateNode(FunctionNode):
    """Outer pre_process: schema validation + incidental-PHI narrative scan."""

    # S-1: outer boundary node — matches agent.yaml required_trust_level
    # (regulated AE submission data, not anonymous public input).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        payload = self._parse(state.get("user_input", ""))

        if not isinstance(payload, dict) or not all(k in payload for k in _REQUIRED_TOP_LEVEL):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["InputValidateNode: AE report must be a JSON object with 'structured' + 'narrative'"],
            }

        structured = payload.get("structured") or {}
        narrative = payload.get("narrative") or ""

        if not isinstance(structured, dict) or not structured:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["InputValidateNode: 'structured' AE fields missing or empty"],
            }

        emit_trace_event(
            "ae_report_input_validated",
            {"correlation_id": state.get("correlation_id"), "narrative_length": len(narrative)},
            state,
        )

        return {
            "validated_input": to_json({"structured": structured, "narrative": narrative}),
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-2 domain hook — incidental-PHI scan on the free-text narrative.

        Non-raising per framework hook contract: always returns a dict (state
        unchanged on pass, ERROR delta on violation).
        """
        payload = self._parse(state.get("user_input", ""))
        narrative = payload.get("narrative", "") if isinstance(payload, dict) else ""

        if narrative and _PHI_PATTERNS.search(narrative):
            return {
                **state,
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    *state.get("error_log", []),
                    "InputValidateNode S-2: incidental PHI detected in AE narrative — rejected",
                ],
            }
        return state

    @staticmethod
    def _parse(raw: Any) -> Any:
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return None
