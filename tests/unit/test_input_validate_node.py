from framework.schemas.agent_status import AgentStatus

from src.nodes.input_validate_node import InputValidateNode
from src.schemas.state import from_json, to_json

AE_REPORT = {
    "structured": {"patient_initials": "A.B.", "reaction_term": "anaphylaxis"},
    "narrative": "Patient developed a rash after administration.",
}


class TestInputValidateNode:
    def test_success(self):
        node = InputValidateNode()
        out = node.execute({"user_input": to_json(AE_REPORT)})
        assert out["status"] == AgentStatus.SUCCESS
        assert from_json(out["validated_input"])["structured"]["reaction_term"] == "anaphylaxis"

    def test_empty_input_error(self):
        node = InputValidateNode()
        out = node.execute({"user_input": ""})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]

    def test_missing_top_level_key_error(self):
        node = InputValidateNode()
        out = node.execute({"user_input": to_json({"structured": {"a": 1}})})
        assert out["status"] == AgentStatus.ERROR

    def test_empty_structured_error(self):
        node = InputValidateNode()
        out = node.execute({"user_input": to_json({"structured": {}, "narrative": "x"})})
        assert out["status"] == AgentStatus.ERROR

    def test_extra_gate_rejects_incidental_phi(self):
        node = InputValidateNode()
        payload = to_json({**AE_REPORT, "narrative": "Patient name: John Smith, MRN:123456"})
        result = node._extra_security_gate_input({"user_input": payload, "error_log": []})
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_extra_gate_passes_clean_narrative(self):
        node = InputValidateNode()
        state = {"user_input": to_json(AE_REPORT)}
        result = node._extra_security_gate_input(state)
        assert result is state
