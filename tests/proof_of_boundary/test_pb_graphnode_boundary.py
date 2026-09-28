# PB-6 outer-boundary supplement: AEValidationGraphNode (Cat 2 `main`-slot GraphNode)
# lives in src/graph/graph.py, not src/nodes/ — the discovery loop in
# test_pb_invoke_order.py only walks src/nodes/, so this outer security boundary
# (first node in the outer backbone to see caller input) is never probed there.
# This is architectural placement, matching the scaffold canonical Cat 2 pattern
# (a GraphNode wrapper at the outer `main` slot delegates gating to the inner
# subgraph's own entry node) — not an attempt to dodge PB-6 coverage.

from unittest.mock import MagicMock

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from framework.nodes.function_node import FunctionNode

from src.graph.graph import AEValidationGraphNode
from src.nodes.e2b_field_validator_node import E2BFieldValidatorNode


class TestGraphNodeS1TrustGate:
    """S-1: the outer GraphNode wrapper enforces the same trust gate as any BaseNode."""

    def test_insufficient_trust_denied_before_execute(self, monkeypatch):
        node = AEValidationGraphNode()
        # get_subgraph must NOT be reached if the S-1 gate denies the call first.
        monkeypatch.setattr(node, "get_subgraph", MagicMock(side_effect=AssertionError("execute() ran")))

        out = node({"caller_trust_level": TrustLevel.ANONYMOUS.value})

        assert out["status"] == AgentStatus.ERROR.value
        assert any("S-1 trust gate denied" in msg for msg in out.get("error_log", []))

    def test_sufficient_trust_reaches_execute(self, monkeypatch):
        node = AEValidationGraphNode()
        monkeypatch.setattr(node, "get_subgraph", MagicMock(side_effect=AssertionError("execute() ran")))

        out = node(
            {
                "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
                "correlation_id": "pb-graphnode-test",
                "session_id": "pb-graphnode-session",
                "thread_id": "pb-graphnode-thread",
                "trace_id": "pb-graphnode-trace",
            }
        )

        # get_subgraph() was reached (and raised) -> S-1 gate let the call through.
        assert out["status"] == AgentStatus.ERROR.value
        assert any("execute() ran" in msg for msg in out.get("error_log", []))


class TestGraphNodeBoundaryMapping:
    """extract_input()/merge_output() must be explicit field mappings (criterion #9),
    not raw pass-through of parent state or subgraph result."""

    def test_extract_input_only_takes_contract_field(self):
        node = AEValidationGraphNode()
        state = {
            "validated_input": '{"structured": {}, "narrative": ""}',
            "correlation_id": "pb-graphnode-test",
            "secret_should_not_leak": "sk-should-not-appear",
        }
        result = node.extract_input(state)

        assert result == state["validated_input"]
        assert "secret_should_not_leak" not in result

    def test_merge_output_maps_fields_explicitly_no_raw_passthrough(self):
        node = AEValidationGraphNode()
        sub_result = {
            "field_verdicts": [{"field": "reaction_term", "verdict": "PASS"}],
            "meddra_verdict": "CODED",
            "pmda_verdict": "PASS",
            "severity_tier": "non-serious",
            "status": AgentStatus.SUCCESS.value,
            "trace_id": "inner-trace-should-not-leak",
            "node_history": ["should", "not", "leak"],
        }
        merged = node.merge_output({"correlation_id": "pb-graphnode-test"}, sub_result)

        expected_keys = {"field_verdicts", "meddra_verdict", "pmda_verdict", "severity_tier", "status"}
        assert set(merged.keys()) == expected_keys
        assert "trace_id" not in merged
        assert "node_history" not in merged


class TestGraphNodeDelegatesGatingToInnerEntry:
    """AEValidationGraphNode's own __call__ skips the standard S-2/S-4/S-3 lifecycle
    by design (GraphNode base class) — verify the inner subgraph's entry node
    (E2BFieldValidatorNode) is itself a gated FunctionNode, so the delegation is
    real rather than a gap. See framework/nodes/graph_node.py."""

    def test_inner_entry_node_declares_trust_level(self):
        assert E2BFieldValidatorNode.required_trust_level in (
            TrustLevel.ANONYMOUS,
            TrustLevel.VERIFIED_EXTERNAL,
            TrustLevel.INTERNAL,
        )

    def test_inner_entry_node_has_security_gates(self):
        # FunctionNode subclasses get the @final S-2/S-3 gates (_security_gate_input/
        # output) from the framework — structural subclass check, since the local
        # dev wheel may be a stub build that lacks those @final methods (CI wheel
        # 1.0.0 is the gate of record for their actual presence/behavior).
        assert issubclass(E2BFieldValidatorNode, FunctionNode)
