# HCR-C2-023 — Clinical Trial Adverse Event (AE) Report Validation Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific use case)
> **Industry**: HCR

## Overview

Checks a clinical-trial adverse-event (AE) report before it is submitted to the
regulator. The caller sends a JSON object with `structured` AE fields and a free-text
`narrative`. The agent validates the input shape and rejects narratives that contain
incidental personal health identifiers, then runs a fixed pipeline: an ICH E2B(R3)
mandatory/conditional field check, a MedDRA term-coding check, a Japanese PMDA
submission-format check (reporter category, `YYYY-MM-DD` dates) and an ICH E2
serious/non-serious severity classification. It returns a field-by-field validation
report in which every PMDA format flag is guaranteed to be present.

All checks are deterministic rule functions (`src/services/validation_rules.py`).
The MedDRA check needs a licensed MedDRA client, which is not included: without one
the check is reported as `gated` (skipped) rather than failing. The report can carry
LLM-written remediation guidance when a model client is injected; with no model
configured (the default here) that field states that LLM guidance is unavailable and
the raw findings are the result.

Input: JSON string in `input` with `structured` and `narrative`. Output:
`validation_report` (field verdicts, MedDRA verdict, PMDA verdict, severity tier,
remediation guidance) and `pmda_flags`.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
