# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: `HCRAEValidationAgent` (`src/graph/graph.py`, aliased as `Graph`)
- **L1 Base**: `AgentBaseGraph` (outer) — Cat 2, `main` slot wraps `AEValidationGraphNode` (`GraphNode`) around inner `AEValidationWorkflowGraph` (`BaseGraph`)
- **Three-Layer Separation**:
  - State: flat TypedDict composition, all agent-specific fields `NotRequired[str]` (JSON-encoded)
  - Node: L1 inheritance (`FunctionNode.execute(self, state) -> dict` override only)
  - Graph: composition — outer `register_nodes()` (3 slots) + inner `register_nodes()`/`add_edges()`

## Architecture Overview

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | framework default | — | schema_version, session_id | InitializeNode (default) |
| pre_process | `InputValidateNode` — schema validate `{structured, narrative}` + S-2 incidental-PHI scan of narrative | `user_input` | `validated_input` | FunctionNode |
| main | `AEValidationGraphNode` (GraphNode) — dispatches inner AE-validation workflow | `validated_input` | `field_verdicts`, `meddra_verdict`, `pmda_verdict`, `severity_tier` | GraphNode wrapping `AEValidationWorkflowGraph` |
| ↳ inner: e2b_field_validate | `E2BFieldValidatorNode` — ICH E2B(R3) mandatory/conditional field check | `user_input` (envelope) | `field_verdicts` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: meddra_code_check | `MedDRACodeCheckerNode` — MedDRA term coding, license-gated | `user_input` | `meddra_verdict` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: pmda_format_check | `PMDAFormatCheckerNode` — deterministic PMDA format check | `user_input` | `pmda_verdict` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: ae_severity_classify | `AESeverityClassifyNode` — ICH E2 serious/non-serious | `user_input` | `severity_tier` | FunctionNode (inner, ANONYMOUS) |
| post_process | `ValidationReportGenerateNode` — LLM remediation narrative + S-3 non-suppressible PMDA gate | `field_verdicts`, `meddra_verdict`, `pmda_verdict`, `severity_tier` | `validation_report`, `pmda_flags` | FunctionNode |
| finalize | framework default | — | response_metadata, total_time_ms | FinalizeNode (default) |

### Data Flow

```
START -> initialize -> pre_process(InputValidate) -> main(AEValidationGraphNode)
      -> post_process(ValidationReportGenerate) -> finalize -> END

Inside main (inner subgraph):
  START -> e2b_field_validate -> meddra_code_check -> pmda_format_check
        -> ae_severity_classify -> END
```

`GraphNode.extract_input()` forwards `validated_input` (JSON string `{structured, narrative}`)
as the inner subgraph's `user_input`. `merge_output()` maps the inner `get_output()` fields
back into the outer state — only changed keys.

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `field_verdicts` | `NotRequired[str]` (JSON list[dict]) | ICH E2B(R3) mandatory/conditional field verdicts | No |
| `meddra_verdict` | `NotRequired[str]` (JSON dict) | MedDRA term-coding verdict (`{"gated": true, ...}` when license absent) | No |
| `pmda_verdict` | `NotRequired[str]` (JSON dict) | PMDA-specific format check verdict, incl. `format_issues` list | No |
| `severity_tier` | `NotRequired[str]` | `"serious"` \| `"non-serious"` (ICH E2) | No |
| `validation_report` | `NotRequired[str]` (JSON dict) | Assembled field-by-field report + LLM remediation narrative | No |
| `pmda_flags` | `NotRequired[str]` (JSON list[str]) | Non-suppressible PMDA flags, echoed by `ValidationReportGenerateNode.execute()` for its own S-3 preservation re-check | No |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types) — all agent-specific fields `NotRequired[...]`
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Dependency: MedDRA license (graceful gate)

MedDRA license is a hard **customer** dependency, but the template
degrades gracefully: `MedDRACodeCheckerNode` accepts an optional `meddra_client` injected
via constructor (forwarded outer -> `AEValidationGraphNode._parent_config()` -> inner graph
config -> node constructor). When `meddra_client is None`, the node returns
`{"gated": true, "reason": "MedDRA license not provisioned"}` and the pipeline continues
(status SUCCESS) — only the MedDRA-coding feature is gated, not the whole validation.

## S-2 incidental-PHI scope (AE free-text narrative)

Scope note: the "no PHI" claim applies only to structured E2B(R3) metadata
(`patient_initials` is an E2B-permitted pseudonym field, not raw PHI). The free-text
`narrative` field is scanned by `InputValidateNode._extra_security_gate_input()` for
incidental PHI leakage — MRN patterns, phone numbers, and "patient name: First Last"
strings — and the report is rejected (status ERROR) if any pattern matches. This is a
deterministic regex scan, not an LLM check, run before any downstream processing.

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, caller_trust_level)
- [x] S-2: `_extra_security_gate_input()` on `InputValidateNode` — incidental-PHI narrative scan
- [x] S-3: `_extra_security_gate_output()` on `ValidationReportGenerateNode` — non-suppressible
      PMDA-flag preservation check (own-output self-consistency: re-checks `pmda_flags` vs the
      `pmda_flags` key embedded in `validation_report`, both returned by the same `execute()` call)
- [x] S-4: `emit_trace_event()` — domain event in every node's `execute()` (`ae_report_input_validated`,
      `e2b_fields_validated`, `meddra_check_gated`/`meddra_term_checked`, `pmda_format_checked`,
      `ae_severity_classified`, `validation_report_generated`), plus GraphNode dispatch/completion
      events (`ae_validation_workflow_dispatched`/`_completed`) inside `extract_input()`/`merge_output()`

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` → no `_security_gate_*` override (gating delegated to the inner subgraph's
>   own `FunctionNode`s); S-4 audit provided via `extract_input()`/`merge_output()` hooks instead

### Composition Pattern

- **Pattern**: Cat 2 — outer `AgentBaseGraph` + `GraphNode` (`main` slot) wrapping inner `BaseGraph`
- **Composition target**: `AEValidationWorkflowGraph` (`src/graph/ae_validation_workflow_graph.py`)
- **Error propagation strategy**: `propagate` (fail fast — re-raise inner errors as SubgraphError)

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: `framework/` and `shared/` only

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph | Fixed multi-step validation pipeline, no autonomous loop needed |
| Composition pattern | Cat 1 flat 3-node | Cat 2 GraphNode + inner subgraph | Cat 2 GraphNode + inner subgraph | 4 domain steps (E2B/MedDRA/PMDA/severity) is a specific job-to-be-done — `gate-composition` requires GraphNode, not a flat MainNode |
| MedDRA license handling | Hard fail when absent | Graceful gate (skip + flag) | Graceful gate | License is customer-provided, must not block build/deploy |
