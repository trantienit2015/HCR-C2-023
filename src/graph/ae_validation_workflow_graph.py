"""AgentCore Platform v1.0 — HCR-C2-023 inner AE validation workflow graph.

Cat 2 inner graph: E2B(R3) field validation -> MedDRA term coding (license-
gated) -> PMDA format check -> ICH E2 severity classification. Instantiated
by AEValidationGraphNode.get_subgraph() in graph.py.

Pipeline (linear, fail-fast on ERROR):
    START -> e2b_field_validate -> meddra_code_check -> pmda_format_check
          -> ae_severity_classify -> END
"""

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus

from src.nodes.ae_severity_classify_node import AESeverityClassifyNode
from src.nodes.e2b_field_validator_node import E2BFieldValidatorNode
from src.nodes.meddra_code_checker_node import MedDRACodeCheckerNode
from src.nodes.pmda_format_checker_node import PMDAFormatCheckerNode
from src.schemas.state import State


class AEValidationWorkflowGraph(BaseGraph):
    """Inner graph for the HCR-C2-023 AE/E2B(R3) validation workflow."""

    @property
    def name(self) -> str:
        return "hcr-ae-e2b-validation-workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        # No mandatory config — meddra_client is optional (graceful license gate).
        pass

    def register_nodes(self) -> None:
        # No super() — BaseGraph.register_nodes() is abstract.
        meddra_client = self.config.get("meddra_client")

        self._nodes["e2b_field_validate"] = E2BFieldValidatorNode()
        self._nodes["meddra_code_check"] = MedDRACodeCheckerNode(meddra_client=meddra_client)
        self._nodes["pmda_format_check"] = PMDAFormatCheckerNode()
        self._nodes["ae_severity_classify"] = AESeverityClassifyNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "e2b_field_validate")
        self._sg.add_conditional_edges(
            "e2b_field_validate",
            lambda s: END if self._is_error(s) else "meddra_code_check",
            {"meddra_code_check": "meddra_code_check", END: END},
        )
        self._sg.add_edge("meddra_code_check", "pmda_format_check")
        self._sg.add_conditional_edges(
            "pmda_format_check",
            lambda s: END if self._is_error(s) else "ae_severity_classify",
            {"ae_severity_classify": "ae_severity_classify", END: END},
        )
        self._sg.add_edge("ae_severity_classify", END)

    @staticmethod
    def _is_error(state: AgentState) -> bool:
        return state.get("status") in (AgentStatus.ERROR.value, AgentStatus.ERROR.value)

    def route(self, state: AgentState) -> str:
        return END if self._is_error(state) else "ae_severity_classify"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "field_verdicts": state.get("field_verdicts"),
            "meddra_verdict": state.get("meddra_verdict"),
            "pmda_verdict": state.get("pmda_verdict"),
            "severity_tier": state.get("severity_tier"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
