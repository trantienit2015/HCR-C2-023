# HCR-C2-023 - Framework compliance tests TC-06/TC-07 (exact-name file required by
# scaffold REQUIRED_STG_COMPLETE — split out of test_framework_compliance.py so the
# gate-scaffold-integrity file-existence check finds it by this exact path).

import pytest
from framework.nodes.function_node import FunctionNode

from src.nodes import input_validate_node, validation_report_generate_node


# TC-06 / TC-07 - S-2/S-3 gates are @final on FunctionNode (overriding raises TypeError at class def).
class TestTC0607FinalGates:
    def test_input_gate_is_final(self):
        with pytest.raises(TypeError):

            class BadIn(FunctionNode):  # noqa: N801
                def _security_gate_input(self, state):
                    return state

    def test_output_gate_is_final(self):
        with pytest.raises(TypeError):

            class BadOut(FunctionNode):  # noqa: N801
                def _security_gate_output(self, result):
                    return result

    def test_extra_hooks_overridable(self):
        assert (
            input_validate_node.InputValidateNode._extra_security_gate_input
            is not FunctionNode._extra_security_gate_input
        )
        assert (
            validation_report_generate_node.ValidationReportGenerateNode._extra_security_gate_output
            is not FunctionNode._extra_security_gate_output
        )

    def test_output_gate_blocks_credentials(self):
        node = validation_report_generate_node.ValidationReportGenerateNode()
        with pytest.raises(Exception):
            node._security_gate_output({"validation_report": "token AKIAIOSFODNN7EXAMPLE leaked"})
