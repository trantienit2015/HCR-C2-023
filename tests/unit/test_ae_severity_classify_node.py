from framework.schemas.agent_status import AgentStatus

from src.nodes.ae_severity_classify_node import AESeverityClassifyNode
from src.schemas.state import to_json


class TestAESeverityClassifyNode:
    def test_hospitalization_is_serious(self):
        structured = {"hospitalization": True}
        node = AESeverityClassifyNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["status"] == AgentStatus.SUCCESS
        assert out["severity_tier"] == "serious"

    def test_fatal_outcome_is_serious(self):
        structured = {"outcome": "fatal"}
        node = AESeverityClassifyNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["severity_tier"] == "serious"

    def test_no_serious_flags_is_non_serious(self):
        structured = {"outcome": "recovered"}
        node = AESeverityClassifyNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["severity_tier"] == "non-serious"

    def test_no_structured_fields_error(self):
        node = AESeverityClassifyNode()
        out = node.execute({"user_input": to_json({})})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]
