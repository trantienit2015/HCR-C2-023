# Test Specification

## Test Strategy
- Coverage target: every node ≥1 unit success + ≥1 error/edge path; ≥1 full-graph integration compile+invoke
- Test types: Unit (`tests/unit/`) / Integration (`tests/integration/`) / Proof-of-Boundary (`tests/proof_of_boundary/`)

## Framework Compliance Tests (Mandatory) — `tests/unit/test_framework_compliance.py`

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict extends `AgentState`, agent fields JSON-str | Type check pass, no Pydantic/dataclass | PASS |
| TC-02 | Empty/missing input → fail-closed ERROR, no raise | `InputValidateNode`/inner nodes return ERROR dict | PASS |
| TC-03 | No JWT/Credential literals or `os.environ` in `src/` | 0 offenders | PASS |
| TC-04 | InvocationContext via `configurable`/`from_state` only, never left in State post-invoke | 0 `InvocationContext` instances in result | PASS |
| TC-05 | S-4: domain event emitted; no backbone-event re-emit in `execute()`/hooks | `node_start`/`node_complete`/`node_error`/`node_skip` absent from `src/` | PASS |
| TC-06 | S-2: `_security_gate_input()` `@final` on `FunctionNode` | `TypeError` at class definition if overridden | PASS |
| TC-07 | S-3: `_security_gate_output()` `@final` on `FunctionNode`; credential-block fires | `TypeError` on override; credential in output raises | PASS |
| TC-08 | `required_trust_level` declared valid + enforced | Insufficient trust → ERROR status, no raise | PASS |

## Proof-of-Boundary Tests (Mandatory) — `tests/proof_of_boundary/`

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → AuditLogger | `emit_trace_event()` fires on every invocation path | No silent failures | PASS |
| PB-2 | State serialization | Post-invoke State is primitives/JSON-str only | No Pydantic/dataclass | PASS |
| PB-4 | Import isolation | No Level 0 / `agenticstar` imports | AST scan: 0 violations | PASS |
| PB-5 | Checkpoint safety | No JWT/Pydantic in checkpoint-eligible State fields | Inspection pass | PASS |
| PB-6 | Invoke execution order (`test_pb_invoke_order.py`) | S-1 → S-4 `node_start` → S-2 → `execute()` → S-3 → S-4 `node_complete`, every `src/nodes/*` `BaseNode` subclass | Order verified for all 6 nodes | PASS |
| PB-7 | HITL interrupt propagation (`test_pb7_hitl_interrupt_propagation.py`) | `hitl.enabled` not set in `config/agent.yaml` → auto-skip | Skipped (N/A — no `interrupt()` in this template) | SKIP (expected) |

## Business Logic Tests — `tests/unit/`, `tests/integration/test_graph.py`

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | `E2BFieldValidatorNode` — mandatory field missing | `structured` missing `reaction_term` | `field_verdicts` contains a `FAIL` verdict for `reaction_term` | PASS |
| BL-02 | `E2BFieldValidatorNode` — conditional field (fatal outcome) | `outcome="fatal"`, no `death_date` | `death_date` verdict = `FAIL` | PASS |
| BL-03 | `MedDRACodeCheckerNode` — license absent | `meddra_client=None` | `meddra_verdict.gated == True`, status SUCCESS (graceful) | PASS |
| BL-04 | `MedDRACodeCheckerNode` — license present | fake `meddra_client` | `meddra_verdict.gated == False`, `meddra_code` populated | PASS |
| BL-05 | `PMDAFormatCheckerNode` — bad date format | `reaction_onset_date="2026/07/10"` | `format_issues` non-empty, verdict `FAIL` | PASS |
| BL-06 | `AESeverityClassifyNode` — serious flag | `hospitalization=True` | `severity_tier == "serious"` | PASS |
| BL-07 | `AESeverityClassifyNode` — non-serious | no serious flags | `severity_tier == "non-serious"` | PASS |
| BL-08 | `ValidationReportGenerateNode` — S-3 non-suppressible PMDA flag | `pmda_flags` manually stripped from `validation_report` before hook | `_extra_security_gate_output` returns ERROR (flag suppressed) | PASS |
| BL-09 | `InputValidateNode` — incidental PHI in narrative | narrative contains `"MRN:12345"` | S-2 hook rejects, status ERROR | PASS |
| BL-10 | Full graph integration — happy path | valid `{structured, narrative}` AE report | `status` SUCCESS, `validation_report` populated | PASS |
| BL-11 | Full graph integration — empty input | `""` | `status` ERROR, no raise | PASS |

## Test Execution Summary
- Execution date: 2026-07-10
- Total tests: see `pytest tests/ -v` output (CI `run-tests` job)
- Pass / Fail / Skip: PB-7 SKIP (HITL not enabled — expected); all others PASS
- Coverage: every node ≥1 success + ≥1 error/edge unit test; 1 full-graph integration test
