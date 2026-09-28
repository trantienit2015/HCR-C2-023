# HCR-C2-023 - Framework compliance tests TC-01..TC-08.
# Adapted to this template's real architecture (Cat 2: outer pre/post + GraphNode-wrapped inner nodes).

import os
import re
import typing

from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.nodes import (
    ae_severity_classify_node,
    e2b_field_validator_node,
    input_validate_node,
    meddra_code_checker_node,
    pmda_format_checker_node,
    validation_report_generate_node,
)
from src.schemas.state import State, to_json

_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "src")
TRUST = TrustLevel.VERIFIED_EXTERNAL.value

AE_REPORT = {
    "structured": {
        "patient_initials": "A.B.",
        "patient_dob_or_age": "45",
        "patient_sex": "F",
        "reaction_term": "anaphylaxis",
        "reaction_onset_date": "2026-06-01",
        "reporter_type": "physician",
        "suspect_drug": "DrugX",
        "outcome": "recovered",
    },
    "narrative": "Patient developed a rash after administration.",
}


def _src_files():
    for root, _d, files in os.walk(_SRC):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def _unwrap(ann):
    if typing.get_origin(ann) is typing.NotRequired:
        return typing.get_args(ann)[0]
    return ann


# TC-01 - State is a flat TypedDict extending AgentState; agent fields are NotRequired[str] (JSON-encoded).
class TestTC01StateContract:
    def test_state_is_typeddict_extending_agent_state(self):
        assert hasattr(State, "__annotations__")
        assert "user_input" in State.__annotations__
        assert set(AgentState.__annotations__).issubset(set(State.__annotations__))

    def test_added_fields_are_notrequired_str(self):
        added = [k for k in State.__annotations__ if k not in AgentState.__annotations__]
        assert added, "State must declare agent-specific fields"
        for name in added:
            ann = State.__annotations__[name]
            unwrapped = _unwrap(ann)
            ann_str = getattr(unwrapped, "__name__", str(unwrapped))
            assert ann_str == "str", f"{name}: {ann_str} - compound fields must be JSON-string-encoded"


# TC-02 - Empty/missing input yields a fail-closed ERROR outcome, no raise.
class TestTC02Validation:
    def test_empty_input_no_raise(self):
        node = input_validate_node.InputValidateNode()
        out = node.execute({"user_input": ""})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]

    def test_missing_structured_no_raise(self):
        node = e2b_field_validator_node.E2BFieldValidatorNode()
        out = node.execute({"user_input": to_json({})})
        assert out["status"] == AgentStatus.ERROR
        assert out["error_log"]


# TC-03 - No JWT / API keys / secrets in src/; no direct os.environ reads.
class TestTC03NoCredentials:
    def test_no_credential_literals(self):
        pat = re.compile(r"(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)")
        offenders = []
        for fp in _src_files():
            with open(fp, encoding="utf-8") as f:
                if pat.search(f.read()):
                    offenders.append(fp)
        assert offenders == []

    def test_no_os_environ_secret_reads(self):
        # Sole exception: the standalone entry point reads its caller-auth tokens
        # (INVOKE_AUTH_TOKEN / STG_INTERNAL_RUNNER_TOKEN) before any InvocationContext exists.
        offenders = []
        for fp in _src_files():
            if os.path.normpath(fp).endswith(os.path.join("src", "api", "server.py")):
                continue
            with open(fp, encoding="utf-8") as f:
                if "os.environ" in f.read():
                    offenders.append(fp)
        assert offenders == []


# TC-04 - InvocationContext is never stored in State after invoke.
class TestTC04ContextIsolation:
    def test_no_invocationcontext_in_state_after_invoke(self):
        from src.graph.graph import Graph

        agent = Graph(config={"max_retry": 1})
        agent.compile()
        ctx = InvocationContext(
            session_id="tc04", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="cro-tc04"
        )
        result = agent.invoke(to_json(AE_REPORT), ctx=ctx)
        for v in result.values():
            assert not isinstance(v, InvocationContext)

    def test_from_state_available(self):
        assert hasattr(InvocationContext, "from_state")


# TC-05 - Domain events: every node emits >=1 domain event; no node under
# src/nodes/ ever re-emits a framework backbone lifecycle event.
class TestTC05Audit:
    def test_input_validate_emits_domain_event(self, monkeypatch):
        events = []
        monkeypatch.setattr(input_validate_node, "emit_trace_event", lambda e, p, s: events.append(e))
        out = input_validate_node.InputValidateNode().execute({"user_input": to_json(AE_REPORT)})
        assert out["status"] == AgentStatus.SUCCESS
        assert "ae_report_input_validated" in events
        assert not ({"node_start", "node_complete", "node_error", "node_skip"} & set(events))

    def test_source_has_no_backbone_events(self):
        pat = re.compile(r'emit_trace_event\(\s*["\'](node_start|node_complete|node_error|node_skip)["\']')
        offenders = []
        for fp in _src_files():
            with open(fp, encoding="utf-8") as f:
                if pat.search(f.read()):
                    offenders.append(fp)
        assert offenders == []


# TC-06/TC-07 - see tests/unit/test_framework_compliance_tc06_tc07.py (split out to
# match the scaffold's exact-name REQUIRED_STG_COMPLETE file list).


# TC-08 - required_trust_level enforced: insufficient trust -> ERROR state, no raise.
class TestTC08TrustGate:
    def test_declared_trust_levels_valid(self):
        for cls in (
            input_validate_node.InputValidateNode,
            e2b_field_validator_node.E2BFieldValidatorNode,
            meddra_code_checker_node.MedDRACodeCheckerNode,
            pmda_format_checker_node.PMDAFormatCheckerNode,
            ae_severity_classify_node.AESeverityClassifyNode,
            validation_report_generate_node.ValidationReportGenerateNode,
        ):
            assert cls.required_trust_level in (TrustLevel.ANONYMOUS, TrustLevel.VERIFIED_EXTERNAL, TrustLevel.INTERNAL)

    def test_insufficient_trust_returns_error(self):
        node = input_validate_node.InputValidateNode()
        out = node({"caller_trust_level": TrustLevel.ANONYMOUS.value, "user_input": to_json(AE_REPORT)})
        assert str(out.get("status")).lower().endswith("error")

    def test_sufficient_trust_succeeds(self):
        node = input_validate_node.InputValidateNode()
        out = node({"caller_trust_level": TRUST, "user_input": to_json(AE_REPORT)})
        assert out["status"] == AgentStatus.SUCCESS
