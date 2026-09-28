from framework.schemas.agent_status import AgentStatus

from src.nodes.e2b_field_validator_node import E2BFieldValidatorNode
from src.schemas.state import from_json, to_json


class TestE2BFieldValidatorNode:
    def test_all_mandatory_fields_present(self):
        structured = {
            "patient_initials": "A.B.",
            "patient_dob_or_age": "45",
            "patient_sex": "F",
            "reaction_term": "anaphylaxis",
            "reaction_onset_date": "2026-06-01",
            "reporter_type": "physician",
            "suspect_drug": "DrugX",
            "outcome": "recovered",
        }
        node = E2BFieldValidatorNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["status"] == AgentStatus.SUCCESS
        verdicts = from_json(out["field_verdicts"])
        assert all(v["verdict"] == "PASS" for v in verdicts)

    def test_missing_mandatory_field_fails(self):
        structured = {"patient_initials": "A.B."}
        node = E2BFieldValidatorNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        assert out["status"] == AgentStatus.SUCCESS
        verdicts = from_json(out["field_verdicts"])
        reaction = next(v for v in verdicts if v["field"] == "reaction_term")
        assert reaction["verdict"] == "FAIL"

    def test_conditional_death_date_required_when_fatal(self):
        structured = {"outcome": "fatal"}
        node = E2BFieldValidatorNode()
        out = node.execute({"user_input": to_json({"structured": structured, "narrative": ""})})
        verdicts = from_json(out["field_verdicts"])
        death_date = next(v for v in verdicts if v["field"] == "death_date")
        assert death_date["verdict"] == "FAIL"

    def test_no_structured_fields_error(self):
        node = E2BFieldValidatorNode()
        out = node.execute({"user_input": to_json({})})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]

    def test_empty_user_input_error(self):
        node = E2BFieldValidatorNode()
        out = node.execute({"user_input": ""})
        assert out["status"] == AgentStatus.ERROR
