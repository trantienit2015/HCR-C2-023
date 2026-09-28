from framework.schemas.agent_status import AgentStatus

from src.nodes.meddra_code_checker_node import MedDRACodeCheckerNode
from src.schemas.state import from_json, to_json


class FakeMedDRAClient:
    def lookup_term(self, term: str):
        return f"MEDDRA-{term.upper()}" if term else None


class TestMedDRACodeCheckerNode:
    def test_license_absent_gates_gracefully(self):
        node = MedDRACodeCheckerNode(meddra_client=None)
        payload = to_json({"structured": {"reaction_term": "anaphylaxis"}, "narrative": ""})
        out = node.execute({"user_input": payload})
        assert out["status"] == AgentStatus.SUCCESS
        verdict = from_json(out["meddra_verdict"])
        assert verdict["gated"] is True

    def test_license_present_returns_code(self):
        node = MedDRACodeCheckerNode(meddra_client=FakeMedDRAClient())
        payload = to_json({"structured": {"reaction_term": "anaphylaxis"}, "narrative": ""})
        out = node.execute({"user_input": payload})
        assert out["status"] == AgentStatus.SUCCESS
        verdict = from_json(out["meddra_verdict"])
        assert verdict["gated"] is False
        assert verdict["meddra_code"] == "MEDDRA-ANAPHYLAXIS"

    def test_no_arg_constructor_default_gated(self):
        node = MedDRACodeCheckerNode()
        out = node.execute({"user_input": to_json({"structured": {}, "narrative": ""})})
        assert out["status"] == AgentStatus.SUCCESS
        assert from_json(out["meddra_verdict"])["gated"] is True
