from framework.schemas.agent_status import AgentStatus

from src.nodes.validation_report_generate_node import ValidationReportGenerateNode
from src.schemas.state import from_json, to_json


class FakeLLM:
    def complete(self, prompt: str) -> str:
        return f"remediation for: {prompt[:20]}"


FIELD_VERDICTS = [
    {"field": "reaction_term", "mandatory": True, "present": True, "verdict": "PASS"},
    {"field": "suspect_drug", "mandatory": True, "present": False, "verdict": "FAIL"},
]
PMDA_VERDICT_WITH_FLAG = {"format_issues": ["reporter_type 'x' not recognized"], "verdict": "FAIL"}


class TestValidationReportGenerateNode:
    def test_success_with_llm(self):
        node = ValidationReportGenerateNode(llm=FakeLLM())
        state = {
            "field_verdicts": to_json(FIELD_VERDICTS),
            "meddra_verdict": to_json({"gated": True}),
            "pmda_verdict": to_json(PMDA_VERDICT_WITH_FLAG),
            "severity_tier": "non-serious",
        }
        out = node.execute(state)
        assert out["status"] == AgentStatus.SUCCESS
        report = from_json(out["validation_report"])
        assert report["remediation_guidance"].startswith("remediation for:")
        assert from_json(out["pmda_flags"]) == PMDA_VERDICT_WITH_FLAG["format_issues"]

    def test_success_without_llm(self):
        node = ValidationReportGenerateNode()
        state = {"field_verdicts": to_json(FIELD_VERDICTS), "pmda_verdict": to_json({"format_issues": []})}
        out = node.execute(state)
        assert out["status"] == AgentStatus.SUCCESS
        report = from_json(out["validation_report"])
        assert "unavailable" in report["remediation_guidance"]

    def test_no_field_verdicts_error(self):
        node = ValidationReportGenerateNode()
        out = node.execute({})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]

    def test_s3_gate_rejects_suppressed_pmda_flag(self):
        node = ValidationReportGenerateNode()
        # validation_report is missing the flag that pmda_flags claims exists —
        # simulates a report-assembly bug that silently dropped it.
        state = {
            "pmda_flags": to_json(["reporter_type issue"]),
            "validation_report": to_json({"pmda_flags": []}),
        }
        out = node._extra_security_gate_output(state)
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]

    def test_s3_gate_passes_when_flags_preserved(self):
        node = ValidationReportGenerateNode()
        state = {
            "pmda_flags": to_json(["reporter_type issue"]),
            "validation_report": to_json({"pmda_flags": ["reporter_type issue"]}),
        }
        result = node._extra_security_gate_output(state)
        assert result is state
