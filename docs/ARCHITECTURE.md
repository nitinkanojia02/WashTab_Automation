# WashTab Automation Framework Architecture

## 1. Executive Summary

The WashTab Automation Framework is an AI-assisted, human-in-the-loop automation generation framework for web UI workflows.

Its purpose is to transform workflow input and live page inspection into reusable, reviewable automation artifacts and final executable Robot Framework scripts.

Instead of generating final automation directly from a text requirement, the framework follows a staged pipeline where each stage creates an artifact that can be reviewed and improved before being reused downstream.

This architecture improves:
- traceability
- maintainability
- reuse
- quality control
- trust in generated automation

The current repository implements a working MVP of this approach.

---

## 2. Problem Statement

Traditional UI automation creation is slow because teams repeatedly perform the same work manually:
- inspect pages and identify stable locators
- create and maintain page object files
- derive manual tests from exploratory knowledge or requirements
- map manual tests to reusable keywords
- write or refine automation scripts
- troubleshoot weak generated outputs

A one-shot AI approach often fails because the generated script may not be grounded in the actual application, may invent locators, or may not follow framework standards.

This framework exists to address that gap by splitting automation generation into controlled, reviewable stages.

---

## 3. Architecture Goal

The goal of the framework is to convert test design inputs and live application understanding into reviewed automation assets and final executable Robot Framework suites.

It is intentionally designed as a layered architecture with human review checkpoints rather than a single-step script generation engine.

---

## 4. Architectural Style

This solution follows a staged pipeline architecture.

Each stage:
- accepts structured inputs
- performs deterministic logic and/or AI-assisted generation
- produces a durable artifact
- allows human review before the next major transition

### Core characteristics
- layered asset generation
- deterministic extraction where possible
- AI-assisted content generation where useful
- manual approval between critical transitions
- reusable automation artifacts
- POM-first automation structure

---

## 5. High-Level Architecture

```text
+--------------------------+
|   Workflow Input Layer   |
|   workflow_inputs/*.json |
+------------+-------------+
             |
             v
+--------------------------+
|  Page Inspection Layer   |
|  scripts/extract_page_   |
|  model.py                |
+------------+-------------+
             |
             v
+--------------------------+
|  POM Generation Layer    |
|  .elements.json          |
|  .resource               |
|  screenshot / debug HTML |
+------------+-------------+
             |
             v
+--------------------------+
|  Human Review Gate #1    |
|  POM / locator review    |
+------------+-------------+
             |
             +-------------------+
             |                   |
             v                   v
+--------------------------+   +--------------------------+
|  Manual Test Generation  |   |  Keyword / Resource Use  |
|  generate_manual_tests   |   |  from POM resource       |
+------------+-------------+   +------------+-------------+
             |                                  |
             v                                  v
+--------------------------+   +--------------------------+
|  Human Review Gate #2    |   |  Human Review Gate #3    |
|  Manual test review      |   |  Resource/keyword review |
+------------+-------------+   +------------+-------------+
             |                                  |
             +-------------------+--------------+
                                 |
                                 v
+------------------------------------------------+
|  Automation Generation Layer                   |
|  generate_robot_from_manual.py                 |
+------------------------+-----------------------+
                         |
                         v
+------------------------------------------------+
|  Human Review Gate #4                          |
|  Final suite review and stabilization          |
+------------------------+-----------------------+
                         |
                         v
+------------------------------------------------+
|  Execution and Reporting Layer                 |
|  Robot outputs in log/                         |
+------------------------------------------------+
```

---

## 6. End-to-End Runtime Flow

1. A workflow is created or edited.
2. Workflow data is stored under `workflow_inputs/`.
3. Page configuration is read from `config/page_model_config.json`.
4. Page extraction is run using `scripts/extract_page_model.py`.
5. Extracted page artifacts are stored under `pom_pages/`.
6. Resource/POM output is reviewed and corrected if required.
7. Manual test generation is triggered using `scripts/generate_manual_tests_json.py`.
8. Manual test JSON is saved in `manual_tests/`.
9. Manual test output is reviewed and refined.
10. Robot generation is triggered using `scripts/generate_robot_from_manual.py`.
11. Generated Robot Framework suite is saved in `tests/`.
12. Final generated automation is reviewed and optionally refined.
13. Automation is executed through Robot Framework.
14. Results are stored in `log/`.

---

## 7. Component View

## 7.1 Input Layer

### Purpose
Captures workflow and test intent that drives downstream generation.

### Main artifacts
- `workflow_inputs/*.json`
- `config/page_model_config.json`

### Responsibilities
- define workflow name
- define business/module context
- define steps and preconditions
- define expected results
- define fields and validations
- define page URLs and resource relationships
- define generation settings and AI configuration

---

## 7.2 Page Inspection and DOM Understanding Layer

### Main component
- `scripts/extract_page_model.py`

### Responsibilities
- open configured target pages
- inspect the DOM using Playwright
- identify relevant interactive elements
- infer labels, roles, and locator candidates
- filter duplicates and low-value elements
- generate evidence artifacts such as screenshots and debug HTML

### Outputs
- `pom_pages/<page>/<page>.elements.json`
- `pom_pages/<page>/<page>.png`
- `pom_pages/<page>/<page>.debug.html`

### Value
This stage grounds downstream automation generation in the real application UI rather than pure text interpretation.

---

## 7.3 Locator and POM Generation Layer

### Main component
- `scripts/extract_page_model.py`

### Responsibilities
- convert extracted elements into locator variables
- infer meaningful names based on role and label
- create Robot Framework resource files
- create reusable page action keywords

### Output
- `pom_pages/<page>/<page>.resource`

### Value
This stage creates the reusable page object layer for automation.

---

## 7.4 Manual Test Generation Layer

### Main component
- `scripts/generate_manual_tests_json.py`

### Responsibilities
- read workflow input JSON
- build an AI prompt for test case generation
- request practical manual tests from the configured AI endpoint
- normalize and standardize the returned output
- persist manual test artifacts for review

### Output
- `manual_tests/<workflow>.json`

### Value
This stage creates a structured manual testing layer between business workflow input and final automation generation.

---

## 7.5 Automation Generation Layer

### Main component
- `scripts/generate_robot_from_manual.py`

### Responsibilities
- load manual test artifacts
- load and parse approved resource files
- extract available resource keywords
- build an AI prompt with resource context and manual test context
- generate a Robot Framework suite
- validate output structure and resource imports

### Output
- `tests/<workflow>_tests.robot`

### Value
This stage creates executable automation using known page resources and reviewed test design input.

---

## 7.6 UI and Orchestration Layer

### Main component
- `app/main.py`

### Responsibilities
- provide the MVP web UI using FastAPI and Jinja templates
- render workflow, manual test, and automation review screens
- read and write repository artifacts
- trigger manual test generation and automation generation
- surface success and error states to the user

### Templates
- `app/templates/base.html`
- `app/templates/index.html`
- `app/templates/workflow_form.html`
- `app/templates/manual_tests.html`
- `app/templates/automation.html`

### Value
Makes the framework usable as a review-oriented MVP rather than only a script collection.

---

## 7.7 Execution and Reporting Layer

### Technology
- Robot Framework
- SeleniumLibrary

### Artifacts
- `log/output.xml`
- `log/report.html`
- `log/log.html`

### Value
Provides execution proof, reporting, and evidence for generated automation.

---

## 8. Repository Structure and Purpose

```text
app/
  main.py                  FastAPI application and workflow orchestration
  templates/               MVP UI templates

config/
  page_model_config.json   Framework and generation configuration

docs/
  README.md                Documentation index
  PLATFORM_VISION.md       Future platform vision
  PRESENTATION_GUIDE.md    Stakeholder/demo presentation guidance
  RUN_PIPELINE.md          How to run and demo the pipeline
  CAPABILITY_MATRIX.md     Capability and implementation status matrix
  ROADMAP.md               Future roadmap and planned enhancements

log/
  output.xml               Robot execution output
  report.html              Robot summary report
  log.html                 Robot execution log

manual_tests/
  *.json                   Generated manual test artifacts

pom_pages/
  <page>/
    *.elements.json        Extracted element inventory
    *.resource             Robot Framework POM/resource file
    *.png                  Page screenshot evidence
    *.debug.html           Debug snapshot of inspected page

scripts/
  extract_page_model.py           Page extraction and POM generation
  generate_manual_tests_json.py   Manual test generation
  generate_robot_from_manual.py   Robot suite generation

tests/
  *_tests.robot           Generated Robot Framework suites

workflow_inputs/
  *.json                  Workflow definition inputs
```

---

## 9. Important File and Module Details

### `app/main.py`
This is the main FastAPI application entry point.

Key responsibilities include:
- route handling
- template rendering
- workflow status display
- workflow save/update logic
- manual test generation orchestration
- automation generation orchestration
- file persistence across repository artifact folders

### `scripts/extract_page_model.py`
This script performs page understanding and resource generation.

Key responsibilities include:
- config loading and validation
- Playwright browser execution
- DOM inspection
- element filtering and role inference
- locator generation
- resource file generation
- evidence creation through screenshots/debug HTML

### `scripts/generate_manual_tests_json.py`
This script transforms workflow input into manual tests.

Key responsibilities include:
- workflow normalization
- AI prompt construction
- AI endpoint invocation
- output normalization
- manual test JSON persistence

### `scripts/generate_robot_from_manual.py`
This script transforms manual tests into Robot Framework suites.

Key responsibilities include:
- manual test loading
- resource parsing
- keyword extraction from resource files
- AI prompt construction with framework constraints
- generated Robot content validation
- final suite persistence

### `config/page_model_config.json`
This is the central config for:
- pages to inspect
- output directory structure
- browser and wait behavior
- AI endpoint settings
- generation control flags

---

## 10. AI Integration Design

AI is used as a controlled generation mechanism rather than an unrestricted code author.

### Current AI-assisted areas
- manual test generation
- Robot Framework suite generation

### Design pattern
1. Create structured input payload
2. Build a constrained prompt
3. Call the configured AI endpoint
4. Normalize returned output
5. Validate structure and framework rules
6. Save artifact for human review

### Why this matters
This design improves reliability because AI is not working in isolation. It is grounded in:
- workflow input
- resource context
- framework architecture rules
- validation logic
- human review

---

## 11. Framework Intelligence Areas

### Exploration
The framework inspects configured pages to understand visible interactive UI elements.

### DOM understanding
The framework derives labels, roles, and locator candidates from DOM structure and attributes.

### Workflow understanding
Workflow JSON acts as the intent source for manual and automated test generation.

### Locator generation
Extracted elements are converted into named locator variables within resource files.

### Manual test generation
AI converts exploratory workflow information into broader scenario-based manual coverage.

### Robot generation
AI converts approved manual tests and resource context into executable suites.

### Execution
Robot Framework executes generated suites and produces logs and reports.

### Healing
Healing is part of the future vision but not fully implemented in the current repository.

### Knowledge storage
Knowledge reuse is partly achieved through stored artifacts, but a formal framework memory layer is not yet implemented.

---

## 12. Generated Artifacts and Meaning

### Workflow Input JSON
Defines business and testing intent for a workflow.

### Elements JSON
Stores extracted page element inventory and metadata.

### Resource File
Represents the POM layer: locators and reusable page interaction keywords.

### Screenshot / Debug HTML
Supports traceability and troubleshooting of page understanding.

### Manual Test JSON
Represents AI-generated manual test coverage for review and reuse.

### Robot Test Suite
Represents generated executable automation built from approved upstream artifacts.

### Execution Logs and Reports
Represent runtime execution evidence.

---

## 13. Human Governance Model

Human review is a core architectural principle.

### Review checkpoints
- POM and locator review
- manual test review
- resource/keyword review
- final automation review

### Governance benefit
This prevents low-quality outputs from flowing into later stages unchallenged.

---

## 14. Current Strengths

- strong staged architecture
- real UI grounding through page inspection
- reusable POM/resource layer
- AI-assisted manual and automation generation
- clear human-in-the-loop review model
- working end-to-end login example
- MVP UI for artifact review and orchestration

---

## 15. Current Limitations and Gaps

The current repository is a strong MVP, but not yet a complete platform.

### Current limitations
- current demonstration is centered mostly on the login flow
- AI outputs still require human validation and refinement
- resource understanding is still relatively shallow semantically
- test data abstraction is not yet fully centralized
- execution-driven healing is not yet fully implemented
- broader multi-page workflow orchestration remains limited
- governance and approval metadata can be expanded significantly

---

## 16. Maturity Assessment

The framework is currently best categorized as:
- architecturally strong
- technically promising
- operationally MVP-level
- not yet production hardened

### Summary
- architecture maturity: high
- feature maturity: moderate
- determinism and governance: emerging
- production readiness: early

---

## 17. Future Architecture Evolution

Recommended evolution areas:
- stronger validation and repair loops for generated automation
- structured resource semantic parsing
- centralized test data strategy
- broader assertion and business-keyword generation in POM resources
- execution-aware regeneration and healing
- workflow status, versioning, and approval metadata
- expansion to multi-page workflows and platform-style UI experience

---

## 18. One-Slide Architecture Summary

```text
Workflow Input
    ↓
Page Inspection and DOM Understanding
    ↓
POM / Resource Generation
    ↓
Human Review
    ↓
AI Manual Test Generation
    ↓
Human Review
    ↓
AI Robot Framework Generation
    ↓
Human Review
    ↓
Execution and Reporting
```

---

## 19. Key Organizational Message

This architecture does not remove the need for automation engineers.

It amplifies them.

AI handles repetitive draft generation, while engineers remain responsible for:
- framework quality
- locator quality
- test design quality
- maintainability
- execution stability
- governance and approval

That is the core architectural strength of this solution.