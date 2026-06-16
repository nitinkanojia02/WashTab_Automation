# Capability and Status Matrix

This document summarizes the current framework capability set and its maturity based strictly on the repository’s current implementation state.

## Capability Matrix

| Capability Area | Description | Current Status | Notes |
|---|---|---|---|
| Workflow definition | Define workflow input artifacts | Implemented | Workflow JSON is stored under `workflow_inputs/` and managed through the MVP UI |
| Workflow editing UI | Create or update workflow definitions | Implemented | Available in the FastAPI UI |
| Page inspection | Open and inspect configured target pages | Implemented | Driven through `scripts/extract_page_model.py` and configuration |
| DOM understanding | Extract relevant page controls and metadata | Implemented | Heuristic and DOM-driven extraction |
| Locator generation | Create locator variables for page resources | Implemented | Generated into Robot resource files |
| POM/resource generation | Create reusable Robot Framework resource files | Implemented | Includes locators and reusable page keywords |
| Manual test generation | Generate manual test scenarios from workflow inputs | Implemented | AI-assisted |
| Manual test review | Review and refine generated manual tests | Implemented | Supported through the MVP UI |
| Automation generation | Generate Robot Framework suites from manual tests | Implemented | AI-assisted and resource-context aware |
| Resource grounding | Use available resource files during automation generation | Implemented | Present in current Robot generation design |
| Automation review UI | Review generated automation before use | Implemented | Available in the MVP UI |
| Local execution support | Execute generated Robot suites locally | Implemented | Standard Robot execution is supported |
| Execution result artifacts | Produce logs and reports from execution | Implemented | `log/output.xml`, `log/log.html`, `log/report.html` |
| Validation of generated Robot output | Enforce basic generated suite quality | Partial | Validation exists but can be expanded significantly |
| Structured test data strategy | Centralize reusable test data cleanly | Partial | Some patterns exist, but not yet fully formalized |
| Approval workflow metadata | Track review, approval, version, and ownership | Partial | Review exists, but metadata-driven governance is limited |
| Multi-page workflow orchestration | Support larger cross-page journeys | Partial | Current MVP is strongest on targeted single-flow generation |
| Execution feedback loop | Feed failures back into refinement | Limited | Not yet fully realized as a structured closed loop |
| Self-healing | Detect and repair broken automation intelligently | Not Yet Implemented | Future direction |
| Knowledge retention layer | Persist and reuse learned patterns across runs | Not Yet Implemented | Future direction |
| Enterprise governance | Full audit, versioning, role alignment, and controlled promotion | Early Stage | Requires future expansion |

---

## Maturity Summary

| Area | Maturity Assessment |
|---|---|
| Overall architecture | Strong |
| UI orchestration | Good MVP |
| Page extraction | Practical MVP |
| POM generation | Good foundation |
| Manual test generation | Implemented and useful |
| Robot generation | Implemented and useful, but still improving |
| Validation and governance | Emerging |
| Execution intelligence | Early |
| Healing and learning | Planned |
| Production readiness | Early-stage MVP |

---

## Summary Interpretation

The framework is already capable of demonstrating a full AI-assisted automation pipeline from workflow definition to executable Robot Framework output.

Its strongest current value lies in:
- staged artifact generation
- human-in-the-loop review
- reusable POM/resource creation
- acceleration of manual and automated test design

Its biggest current growth opportunities are:
- stronger validation
- richer framework intelligence
- structured test data handling
- execution-aware improvement
- future healing and knowledge reuse