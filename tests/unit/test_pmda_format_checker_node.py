from framework.schemas.agent_status import AgentStatus

from src.nodes.pmda_format_checker_node import PMDAFormatCheckerNode
from src.schemas.state import from_json, to_json


class TestPMDAFormatCheckerNode:
    def test_valid_format_passes(self):
        structured = {"reporter_type": "physician", "reaction_onset_date": "2026-06-01"}
        node = PMDAFormatCheckerNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["status"] == AgentStatus.SUCCESS
        verdict = from_json(out["pmda_verdict"])
        assert verdict["verdict"] == "PASS"
        assert verdict["format_issues"] == []

    def test_bad_reporter_type_flagged(self):
        structured = {"reporter_type": "unknown_role"}
        node = PMDAFormatCheckerNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        verdict = from_json(out["pmda_verdict"])
        assert verdict["verdict"] == "FAIL"
        assert any("reporter_type" in issue for issue in verdict["format_issues"])

    def test_bad_date_format_flagged(self):
        structured = {"reaction_onset_date": "2026/06/01"}
        node = PMDAFormatCheckerNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        verdict = from_json(out["pmda_verdict"])
        assert verdict["verdict"] == "FAIL"

    def test_no_structured_fields_error(self):
        node = PMDAFormatCheckerNode()
        out = node.execute({"user_input": to_json({})})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]
