# WashTab Automation Framework

AI-assisted, human-in-the-loop test automation generation framework for WashTab UI workflows.

## Executive Summary

WashTab Automation Framework is a staged automation generation solution that transforms workflow input and live web page understanding into reusable automation assets and executable Robot Framework test suites.

Instead of asking AI to generate a final test script in one step, the framework breaks automation creation into controlled stages:
- workflow definition
- page inspection and DOM understanding
- locator and POM/resource generation
- manual test generation
- automation script generation
- human review and refinement at every critical stage

This approach improves traceability, reviewability, maintainability, and confidence in generated automation.

The current repository represents a working MVP focused on demonstrating the framework using a login workflow.

---

## Problem Statement

Creating UI automation manually is time-consuming and repetitive. Teams often spend significant effort on:
- understanding application pages
- identifying stable locators
- creating and maintaining page object files
- writing manual test coverage from exploratory findings or requirements
- converting those tests into maintainable automation scripts
- fixing weak generated scripts after one-shot AI generation

A direct AI-to-script approach is often unreliable because the model may not understand the real page, may invent locators, or may generate automation that does not follow framework standards.

This framework exists to solve that problem through staged generation, real UI grounding, and human review checkpoints.

---

## Vision

The long-term vision of this framework is to become a governed AI-assisted automation platform that can:
- understand workflows and page structure
- explore live web pages and infer relevant UI controls
- generate maintainable POM/resource files
- generate meaningful manual tests from workflow intent
- generate framework-compliant Robot Framework automation
- support execution feedback, repair, and future self-healing capabilities
- retain reusable knowledge across workflows and pages

The goal is not blind automation generation. The goal is AI-assisted acceleration under engineering control.

---

## Current Scope and Status

The current implementation supports:
- workflow input capture and editing through the FastAPI UI
- page inspection and page model extraction through scripts
- POM/resource generation
- manual test generation using AI
- Robot Framework generation using AI and available resource context
- review of generated artifacts through the MVP UI
- local Robot execution and result artifacts

Current maturity:
- architecture: strong
- implementation: working MVP
- usability: good for internal demos and engineering use
- production readiness: early stage

---

## Core Capabilities

- **Workflow-driven test design input**
- **Live page inspection and element extraction**
- **Locator generation and page object resource creation**
- **AI-assisted manual test generation**
- **AI-assisted Robot Framework generation**
- **POM-based automation reuse**
- **Human review at every key stage**
- **Execution artifact generation through Robot Framework**

---

## High-Level Workflow

1. Define a workflow in `workflow_inputs/`
2. Configure the target page in `config/page_model_config.json`
3. Run page extraction to generate page artifacts in `pom_pages/`
4. Review and refine generated POM/resource files
5. Generate manual test cases into `manual_tests/`
6. Review and refine manual tests
7. Generate Robot Framework automation into `tests/`
8. Review the generated automation
9. Execute tests and inspect results in `log/`

---

## Repository Structure

```text
app/                 FastAPI web application and HTML templates
config/              Framework configuration
docs/                Documentation
log/                 Robot Framework execution outputs
manual_tests/        Generated manual test artifacts
pom_pages/           Extracted page artifacts and Robot resource files
scripts/             Generation and extraction scripts
tests/               Generated Robot Framework test suites
workflow_inputs/     Workflow definition inputs
ARCHITECTURE.md      Detailed architecture narrative
README.md            Repository overview and quick start
```

---

## Important Modules

### `app/main.py`
FastAPI application entry point and orchestration layer for the MVP UI.

### `scripts/extract_page_model.py`
Inspects configured pages, extracts element information, and generates page artifacts including resource files.

### `scripts/generate_manual_tests_json.py`
Uses workflow input to generate manual test case JSON.

### `scripts/generate_robot_from_manual.py`
Uses approved manual test JSON and resource context to generate Robot Framework suites.

---

## Technology Stack

- **Python** — main implementation language
- **FastAPI** — orchestration UI backend
- **Jinja2 / Starlette templates** — server-side HTML rendering
- **Playwright** — page inspection and DOM-driven extraction
- **Requests** — AI endpoint integration
- **Robot Framework** — automation suite format
- **SeleniumLibrary** — browser automation execution layer
- **Pabot** — parallel execution support
- **JSON** — workflow and intermediate artifact format

---

## Generated Artifacts

The framework currently produces and uses these artifact types:
- workflow input JSON
- page elements inventory JSON
- screenshot and debug HTML evidence
- Robot Framework `.resource` POM files
- manual test JSON
- generated Robot test suites
- Robot execution logs and reports

---

## Documentation

See the following files for detailed documentation:
- `ARCHITECTURE.md`
- `docs/README.md`
- `docs/PLATFORM_VISION.md`
- `docs/PRESENTATION_GUIDE.md`
- `docs/RUN_PIPELINE.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/ROADMAP.md`

---

## How to Run Locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Playwright browsers
```bash
playwright install
```

### 3. Configure AI access
Set the token expected in configuration, for example:
```bash
export DEVEX_AI_TOKEN=<your_token>
```

### 4. Start the MVP UI
```bash
uvicorn app.main:app --reload
```

### 5. Open the app
```text
http://127.0.0.1:8000
```

### Optional script-based flow
```bash
python scripts/extract_page_model.py
python scripts/generate_manual_tests_json.py
python scripts/generate_robot_from_manual.py
robot -d log tests/
```

---

## How Teams Can Use It Today

### QA Teams
- capture exploratory workflow inputs
- generate and review manual tests faster
- validate coverage before automation is created

### Automation Engineers
- bootstrap page resources and Robot suites
- review and harden generated locators and automation logic
- reuse approved page objects and keywords

### Engineering Teams
- convert known business workflows into reusable test assets
- accelerate first-draft test automation creation

### Leadership and Stakeholders
- understand the staged automation model
- review generated artifacts and governance points
- evaluate future platform potential

---

## Current Limitations

The repository already demonstrates a useful framework foundation, but several areas are still evolving:
- the repository demo is centered primarily on the login flow
- AI output still requires validation and review
- generated automation can still need additional framework hardening
- structured test data reuse is not yet fully mature
- execution feedback, healing, and knowledge retention are not yet fully realized
- broader multi-page workflow orchestration remains a future enhancement area

---

## Maturity Assessment

This framework is currently best described as:
- a strong concept
- a working MVP
- suitable for demos and controlled internal usage
- not yet a production-hardened platform

### Summary rating
- architecture: strong
- test asset generation: implemented
- governance: emerging
- automation reliability: moderate with review
- production readiness: early stage

---

## Recommended Next Steps

1. Strengthen validation and repair of generated Robot automation
2. Deepen semantic understanding of resource/POM files
3. Introduce a stronger test data abstraction layer
4. Expand generated POM content with richer validation and assertion keywords
5. Improve stage approval tracking and governance
6. Extend support to broader multi-page workflows
7. Evolve the MVP UI into a more guided platform experience

---

## Key Value Proposition

The primary value of this framework is not that AI writes tests alone.

The value is that it helps teams generate the right automation artifacts in the right order, with human review gates in between, so test automation becomes:
- faster to create
- easier to review
- more reusable
- more maintainable
- better aligned to real application structure