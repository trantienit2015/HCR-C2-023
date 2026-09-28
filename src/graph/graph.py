"""AgentCore Platform v1.0 — HCR-C2-023 outer graph (Cat 2).

Clinical Trial Adverse Event (AE) Report Validation Agent. Cat 2: outer
AgentBaseGraph with the fixed 5-node backbone. Domain complexity (E2B(R3)
field validation -> MedDRA coding -> PMDA format check -> severity
classification) is encapsulated in AEValidationGraphNode (the `main` slot),
which wraps the inner AEValidationWorkflowGraph. Do NOT override
add_edges().

Backbone: initialize -> pre_process(InputValidate) -> main(GraphNode)
          -> post_process(ValidationReportGenerate) -> finalize

AEValidationGraphNode lives here (not under src/nodes/) — the PB-6
invoke-order test only discovers BaseNode subclasses under src/nodes/, and
a GraphNode's __call__ intentionally skips the standard S-2/S-4/S-3
lifecycle (gating is delegated to the inner subgraph).
"""

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.nodes.input_validate_node import InputValidateNode
from src.nodes.validation_report_generate_node import ValidationReportGenerateNode
from src.schemas.state import State


class AEValidationGraphNode(GraphNode):
    """Wraps the inner E2B(R3)/MedDRA/PMDA/severity validation workflow (Cat 2 composition)."""

    # S-1: outer main-slot wrapper — first node in the outer backbone to receive
    # caller input after pre_process; matches agent.yaml required_trust_level and
    # sibling outer nodes (InputValidateNode / ValidationReportGenerateNode).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL
    # "propagate": re-raise inner errors as SubgraphError (fail fast - default).
    error_strategy: ClassVar[str] = "propagate"
    # No HITL in this template.
    propagate_hitl: ClassVar[bool] = False

    def __init__(self, meddra_client: Any = None) -> None:
        super().__init__()
        self._meddra_client = meddra_client

    def get_subgraph(self) -> Any:
        from src.graph.ae_validation_workflow_graph import AEValidationWorkflowGraph

        sg = AEValidationWorkflowGraph(config=self._parent_config())
        sg.compile()
        return sg

    def extract_input(self, state: AgentState) -> str:
        emit_trace_event(
            "ae_validation_workflow_dispatched", {"correlation_id": state.get("correlation_id", "")}, state
        )
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        emit_trace_event(
            "ae_validation_workflow_completed",
            {"correlation_id": state.get("correlation_id", ""), "status": str(sub_result.get("status"))},
            state,
        )
        return {
            "field_verdicts": sub_result.get("field_verdicts"),
            "meddra_verdict": sub_result.get("meddra_verdict"),
            "pmda_verdict": sub_result.get("pmda_verdict"),
            "severity_tier": sub_result.get("severity_tier"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {"meddra_client": self._meddra_client}


class HCRAEValidationAgent(AgentBaseGraph):
    """HCR-C2-023 — Clinical Trial Adverse Event (AE) Report Validation Agent (Cat 2)."""

    @property
    def name(self) -> str:
        return "hcr-c2-023"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects initialize + finalize

        meddra_client = self.config.get("meddra_client")
        llm = self.config.get("llm")

        self._nodes["pre_process"] = InputValidateNode()
        self._nodes["main"] = AEValidationGraphNode(meddra_client=meddra_client)
        self._nodes["post_process"] = ValidationReportGenerateNode(llm=llm)

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.

    def get_output(self, state: Any) -> dict[str, Any]:
        # Override the AgentBaseGraph default (which only surfaces
        # output/status/trace_id/correlation_id/node_history) — the assembled
        # validation_report + component verdicts are the actual deliverable
        # of this agent, not a single formatted_output string.
        return {
            "output": state.get("validation_report"),
            "field_verdicts": state.get("field_verdicts"),
            "meddra_verdict": state.get("meddra_verdict"),
            "pmda_verdict": state.get("pmda_verdict"),
            "severity_tier": state.get("severity_tier"),
            "validation_report": state.get("validation_report"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }


# Alias for agent.yaml module:"src.graph" resolution (AgentRegistry / api/server.py).
Graph = HCRAEValidationAgent
