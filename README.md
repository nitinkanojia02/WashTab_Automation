# AI Automation Framework

AI-assisted, human-in-the-loop test automation generation framework for web UI workflows.

## Executive Summary

This repository contains a FastAPI-based MVP that helps users turn workflow input and live page understanding into reviewable automation artifacts and Robot Framework tests.

Rather than generating a final test script in one step, the framework breaks the process into controlled stages:
- workflow definition
- page inspection and element extraction
- locator and resource generation
- keyword review
- manual test generation
- automation generation
- human review at each critical stage

The current repo is a working MVP and is primarily demonstrated with a login workflow.

---

## What the Repository Currently Contains

```text
app/                 FastAPI application and HTML templates
config/              Framework configuration
docs/                Architecture, capability matrix, and roadmap
resources/           Shared Robot Framework resources
scripts/             Extraction and generation scripts
workflow_inputs/     Saved workflow definitions
README.md            Repository overview and quick start
requirements.txt     Python dependencies
```

Some additional folders such as `pom_pages/`, `manual_tests/`, and `tests/` are created at runtime when the pipeline is used. They are part of the framework design, but they may not be present in a clean checkout until artifacts are generated.

---

## Current Architecture in Practice

The current implementation is centered around `app/main.py`, which provides a staged UI flow.

AI orchestration now uses a hybrid context model:
- one workflow-scoped AI session per feature/workflow
- separate stages inside that workflow session for manual generation, resource generation/review, and Robot generation/review
- persisted artifacts remain the source of truth
- lightweight session history is used only to carry forward prior AI decisions and reviewer feedback within the same workflow

This means context is shared within a single workflow such as `login`, but isolated across different workflows so one feature does not pollute another.

The staged UI flow is:

1. create or edit a workflow
2. extract page information from a live URL
3. review extracted page elements and locators
4. review generated page keywords/resources
5. generate and review manual tests
6. generate and review Robot Framework automation

So the repo is best understood as a review-driven orchestration app layered on top of extraction and AI-backed generation scripts.

---

## Main Components

### `app/main.py`
FastAPI application entry point and orchestration layer.

Responsibilities include:
- workflow CRUD through the UI
- page extraction orchestration
- page review persistence
- keyword review persistence
- manual test generation/review
- Robot Framework generation/review

### `scripts/extract_page_model.py`
Uses Playwright to inspect a target page and generate page artifacts.

Typical outputs:
- `pom_pages/<page>/<page>.elements.json`
- `pom_pages/<page>/<page>.resource`
- `pom_pages/<page>/<page>.png`
- `pom_pages/<page>/<page>.debug.html`

### `scripts/generate_manual_tests_json.py`
Uses workflow input plus AI to generate structured manual test JSON.

Typical output:
- `manual_tests/<workflow>.json`

### `scripts/generate_robot_from_manual.py`
Uses approved manual tests plus approved resource context to generate a Robot Framework suite.

Typical output:
- `tests/<workflow>_tests.robot`

### `config/page_model_config.json`
Central configuration for:
- artifact output directories
- browser settings
- AI endpoint settings
- application abbreviation settings used in generated automation naming/tagging
- generation control options
- configured pages

Example:
- `application_code: "WT"` ensures generated testcase IDs use the stable application abbreviation `WT`
- generated testcase IDs follow the standard `<APPCODE>-<FEATURECODE><NN>`, for example `WT-LOGIN01`, and the same ID format is used consistently in manual test matrices, Robot tags, and related generated artifacts
- generated Robot test case names follow the standard `AUT-<APPCODE>-<FEATURECODE><NN>: <Title>`, for example `AUT-WT-LOGIN01: Verify login page loads successfully`
- generated Robot `[Tags]` are intentionally minimal and include only the testcase ID and the scenario type, for example `[Tags]    WT-LOGIN01    positive`

### `resources/common_keywords.resource`
Shared common Robot keywords and variables used across generated resources/tests.

Current intent of this shared layer:
- common variables such as `${BROWSER}` and `${DEFAULT_TIMEOUT}`
- browser lifecycle keywords such as `Open Browser Session` and `Close Browser Session`
- generic navigation helpers such as `Open Browser To Url`, `Open Login Page`, and `Go To Url`
- generic interaction helpers such as `Wait For Element To Be Ready`, `Click When Ready`, and `Input Text When Ready`

Page-specific resource files under `pom_pages/<page>/` should avoid duplicating these common concerns and should focus on page locators, page-specific actions, page-specific validations, and page-specific test-data variables.

---

## High-Level Workflow

### Stage 1: Workflow definition
A workflow is created through the UI and stored under `workflow_inputs/`.

### Stage 2: Page extraction
The extraction script opens the target page with Playwright, inspects the DOM, and generates page-level artifacts under `pom_pages/`.

### Stage 3: Page and keyword review
The UI allows users to review extracted elements, update names/locators, and approve generated page keywords/resources.

### Stage 4: Manual test generation
AI generates manual test cases based on the workflow input, and the user reviews/approves them.

### Stage 5: Automation generation
AI generates Robot Framework automation using approved manual tests and available resource files.

### Stage 6: Final review
The generated Robot suite is reviewed and saved through the UI.

---

## Technology Stack

- Python
- FastAPI
- Jinja2 templates
- Playwright
- Requests
- Robot Framework
- SeleniumLibrary
- Pabot
- JSON-based artifact exchange

---

## Current Scope and Status

The current implementation supports:
- workflow input capture and editing
- page extraction from a live application page
- page element/locator review
- keyword/resource review
- AI-assisted manual test generation
- AI-assisted Robot Framework generation
- final automation review and save

Current maturity:
- architecture: strong
- implementation: working MVP
- production readiness: early stage

---

## Documentation

Available documentation in this repo:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/ROADMAP.md`

These documents have been aligned to the current repository contents and actual implementation behavior.

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
Set the token expected by `config/page_model_config.json`:
```bash
export DEVEX_AI_TOKEN=<your_token>
```

### 4. Start the UI
```bash
uvicorn app.main:app --reload
```

### 5. Open the app
```text
http://127.0.0.1:8000
```

---

## Optional Script-Level Usage

Depending on your local setup and generated artifacts, the pipeline scripts can also be run directly:

```bash
python scripts/extract_page_model.py
python scripts/generate_manual_tests_json.py
python scripts/generate_robot_from_manual.py
```

If Robot tests have been generated into `tests/`, they can then be executed with standard Robot Framework commands.

---

## Current Limitations

- the sample workflow is primarily login-oriented
- many artifact directories are generated only after pipeline usage
- AI outputs still require human review and validation
- broader multi-page workflow orchestration is still limited
- governance, validation, and execution feedback loops can be expanded significantly

---

## Key Value Proposition

The value of this framework is not one-shot AI script generation.

The value is a staged, review-driven process that helps teams generate better automation artifacts in the right order, with human control between stages.
