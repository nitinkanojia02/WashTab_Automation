from pathlib import Path
import json
import re
import subprocess
import sys
from openpyxl import Workbook

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER

from scripts.generate_manual_tests_json import (
    build_prompt as build_manual_prompt,
    call_devex_ai,
    get_ai_token as get_manual_ai_token,
    load_config as load_manual_config,
    normalize_manual_test,
    validate_config as validate_manual_config,
)
from scripts.generate_robot_from_manual import (
    build_manual_review_prompt,
    build_prompt as build_robot_prompt,
    build_review_prompt,
    build_validation_review_prompt,
    call_ai_chat,
    get_ai_token as get_robot_ai_token,
    load_json as load_robot_ai_json,
    parse_resource_file,
    validate_config as validate_robot_config,
    validate_manual_content,
    validate_resource_content,
    validate_robot_content,
)

BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = BASE_DIR / "workflow_inputs"
MANUAL_DIR = BASE_DIR / "manual_tests"
TESTS_DIR = BASE_DIR / "tests"
POM_DIR = BASE_DIR / "pom_pages"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
CONFIG_PATH = BASE_DIR / "config" / "page_model_config.json"

app = FastAPI(title="WashTab Automation MVP")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# -------------------------------------------------------------------
# Generic helpers
# -------------------------------------------------------------------

def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    payload = {"request": request, "success_message": None, "error_message": None}
    payload.update(context)
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=payload,
        status_code=status_code,
    )

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


CONFIG = read_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
SESSION_DIR = BASE_DIR / "ai_sessions"


def get_session_path(workflow_name: str) -> Path:
    return SESSION_DIR / f"{workflow_name}.json"


def reset_workflow_session(workflow_name: str) -> dict:
    session = {
        "workflow": workflow_name,
        "messages": [],
        "run_active": False,
    }
    save_workflow_session(workflow_name, session)
    return session


def load_workflow_session(workflow_name: str) -> dict:
    session_path = get_session_path(workflow_name)
    if session_path.exists():
        try:
            data = read_json(session_path)
            if isinstance(data, dict) and isinstance(data.get("messages"), list):
                data.setdefault("workflow", workflow_name)
                data.setdefault("run_active", False)
                return data
        except Exception:
            pass
    return reset_workflow_session(workflow_name)


def begin_workflow_run(workflow_name: str) -> dict:
    session = reset_workflow_session(workflow_name)
    session["run_active"] = True
    save_workflow_session(workflow_name, session)
    return session


def ensure_workflow_run(workflow_name: str) -> dict:
    session = load_workflow_session(workflow_name)
    if not session.get("run_active"):
        session = begin_workflow_run(workflow_name)
    return session


def save_workflow_session(workflow_name: str, session: dict):
    session_path = get_session_path(workflow_name)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(session_path, session)


def append_session_message(workflow_name: str, role: str, stage: str, content: str):
    cleaned = (content or "").strip()
    if not cleaned:
        return
    session = ensure_workflow_run(workflow_name)
    session.setdefault("messages", []).append({
        "role": role,
        "stage": stage,
        "content": cleaned,
    })
    session["messages"] = session["messages"][-12:]
    save_workflow_session(workflow_name, session)


def build_session_context(workflow_name: str, stage: str) -> str:
    session = ensure_workflow_run(workflow_name)
    messages = session.get("messages", [])[-8:]
    if not messages:
        return ""

    lines = [
        "Workflow AI session context from earlier stages in the current run. Reuse established decisions where appropriate.",
        "Keep this context subordinate to the current task instructions and current source artifacts.",
    ]
    for entry in messages:
        role = clean_text(str(entry.get("role", "assistant"))).upper() or "ASSISTANT"
        prior_stage = clean_text(str(entry.get("stage", "unknown"))) or "unknown"
        content = str(entry.get("content", "")).strip()
        if not content:
            continue
        lines.append(f"[{role} | {prior_stage}]\n{content}")

    lines.append(f"Current stage: {stage}")
    return "\n\n".join(lines)


def call_ai_with_workflow_session(
    workflow_name: str,
    stage: str,
    endpoint: str,
    token: str,
    prompt: str,
    timeout_seconds: int = 120,
    verify_ssl: bool = False,
) -> str:
    context = build_session_context(workflow_name, stage)
    effective_prompt = prompt if not context else f"{context}\n\n{prompt}"
    append_session_message(workflow_name, "user", stage, prompt)
    response = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=effective_prompt,
        timeout_seconds=timeout_seconds,
        verify_ssl=verify_ssl,
    )
    append_session_message(workflow_name, "assistant", stage, response)
    return response


def call_manual_ai_with_workflow_session(
    workflow_name: str,
    stage: str,
    endpoint: str,
    token: str,
    prompt: str,
) -> dict:
    context = build_session_context(workflow_name, stage)
    effective_prompt = prompt if not context else f"{context}\n\n{prompt}"
    append_session_message(workflow_name, "user", stage, prompt)
    response = call_devex_ai(endpoint=endpoint, token=token, prompt=effective_prompt)
    append_session_message(workflow_name, "assistant", stage, json.dumps(response, indent=2, ensure_ascii=False))
    return response


def export_manual_tests_to_excel(workflow_name: str, workflow: dict | None, manual_data: dict) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Manual Tests"

    headers = [
        "Manual Test ID",
        "Title",
        "Type",
        "Priority",
        "Preconditions",
        "Steps",
        "Expected Result",
    ]
    sheet.append(headers)

    app_code = derive_app_code(workflow, workflow_name)
    feature_code = derive_feature_code(workflow, workflow_name)

    cases = manual_data.get("testCases") or manual_data.get("manualTests") or []
    for index, case in enumerate(cases, start=1):
        case_id = f"{app_code}-{feature_code}{index:02d}"
        preconditions = "\n".join(str(item).strip() for item in case.get("preconditions", []) if str(item).strip())
        steps = "\n".join(str(item).strip() for item in case.get("steps", []) if str(item).strip())
        expected = clean_text(str(case.get("expectedResult", "")))
        sheet.append([
            case_id,
            clean_text(str(case.get("title", f"Test Case {index}"))),
            clean_text(str(case.get("type", ""))),
            clean_text(str(case.get("priority", ""))),
            preconditions,
            steps,
            expected,
        ])

    for column_cells in sheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 14), 60)

    output_path = MANUAL_DIR / f"{workflow_name}_approved_manual_tests.xlsx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def get_workflow_status(workflow_name: str) -> dict:
    workflow = load_workflow_or_404(workflow_name)
    pages = workflow.get("pages", []) if isinstance(workflow, dict) else []
    page_name = ""
    if pages and isinstance(pages[0], dict):
        page_name = clean_text(str(pages[0].get("name", "")))

    page_dir = POM_DIR / page_name if page_name else None
    elements_path = page_dir / f"{page_name}.elements.json" if page_dir else None
    resource_path = page_dir / f"{page_name}.resource" if page_dir else None
    keywords_path = page_dir / f"{page_name}.keywords.json" if page_dir else None
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    automation_path = TESTS_DIR / f"{workflow_name}_tests.robot"

    page_reviewed = bool(elements_path and elements_path.exists())
    keywords_reviewed = bool(resource_path and resource_path.exists() and keywords_path and keywords_path.exists())

    manual_approved = False
    if manual_path.exists():
        try:
            manual_data = read_json(manual_path)
            manual_cases = extract_manual_test_cases(manual_data)
            manual_approved = len(manual_cases) > 0
        except Exception:
            manual_approved = False

    automation_generated = bool(automation_path.exists() and clean_text(read_text(automation_path)))

    return {
        "page_reviewed": page_reviewed,
        "keywords_reviewed": keywords_reviewed,
        "manual_approved": manual_approved,
        "automation_generated": automation_generated,
    }

def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "workflow"

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def compact_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", clean_text(value)).upper()


def derive_app_code(workflow: dict | None, workflow_name: str) -> str:
    workflow = workflow or {}

    config_code = compact_code(str(CONFIG.get("application_code", "")))
    if config_code:
        return config_code

    explicit_code = compact_code(
        workflow.get("applicationCode")
        or workflow.get("appCode")
        or workflow.get("moduleCode")
        or workflow.get("moduleAbbreviation")
    )
    if explicit_code:
        return explicit_code

    module = compact_code(workflow.get("module", ""))
    workflow_code = compact_code(workflow.get("workflowName", workflow_name))
    if module:
        if len(module) <= 4:
            return module
        return module[:2]
    return workflow_code[:2] or "APP"


def derive_feature_code(workflow: dict | None, workflow_name: str) -> str:
    feature = compact_code((workflow or {}).get("feature", ""))
    workflow_code = compact_code((workflow or {}).get("workflowName", workflow_name))
    return feature or workflow_code or "FLOW"

def to_keyword_title(element_name: str) -> str:
    base = clean_text(element_name).replace("_", " ")
    return " ".join(word.capitalize() for word in base.split())

def to_robot_variable_name(name: str) -> str:
    return slugify(name).upper()

# -------------------------------------------------------------------
# Workflow status
# -------------------------------------------------------------------

def get_status_path(workflow_name: str) -> Path:
    return WORKFLOW_DIR / f"{workflow_name}.status.json"

def load_workflow_status(workflow_name: str) -> dict:
    status_path = get_status_path(workflow_name)
    if status_path.exists():
        try:
            return read_json(status_path)
        except Exception:
            pass
    return {
        "page_reviewed": False,
        "keywords_reviewed": False,
        "manual_approved": False,
        "automation_generated": False
    }

def save_workflow_status(workflow_name: str, status: dict):
    write_json(get_status_path(workflow_name), status)

def update_workflow_status(workflow_name: str, **updates):
    status = load_workflow_status(workflow_name)
    status.update(updates)
    save_workflow_status(workflow_name, status)

# -------------------------------------------------------------------
# Workflow handling
# -------------------------------------------------------------------

def load_workflow_or_404(workflow_name: str) -> dict:
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
    return read_json(workflow_path)

def clean_workflow_for_prompting(workflow: dict) -> dict:
    cleaned = json.loads(json.dumps(workflow))

    fields = cleaned.get("fields", [])
    if isinstance(fields, list):
        cleaned_fields = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = clean_text(str(field.get("name", "")))
            label = clean_text(str(field.get("label", "")))
            field_type = clean_text(str(field.get("type", "")))
            required = bool(field.get("required", False))
            if not any([name, label, field_type, required]):
                continue
            cleaned_fields.append({
                "name": name,
                "label": label,
                "type": field_type,
                "required": required,
            })
        cleaned["fields"] = cleaned_fields

    test_data = cleaned.get("testData", {})
    if isinstance(test_data, dict):
        cleaned["testData"] = {
            key: clean_text(str(value))
            for key, value in test_data.items()
            if clean_text(str(value))
        }

    resource_files = cleaned.get("resourceFiles", [])
    if isinstance(resource_files, list):
        cleaned["resourceFiles"] = [clean_text(str(item)) for item in resource_files if clean_text(str(item))]

    return cleaned


def build_workflow_payload(
    workflow_name: str,
    module: str,
    feature: str,
    page_name: str,
    page_url: str,
    resource_file: str,
    preconditions_text: str,
    steps_text: str,
    expected_result: str,
    fields_text: str,
    validations_text: str,
    scenario_intent_text: str,
    valid_username: str,
    valid_password: str,
    application_code: str = "",
):
    preconditions = [line.strip() for line in preconditions_text.splitlines() if line.strip()]
    steps = [line.strip() for line in steps_text.splitlines() if line.strip()]
    validations = [line.strip() for line in validations_text.splitlines() if line.strip()]
    scenario_intent = [line.strip() for line in scenario_intent_text.split(",") if line.strip()]

    fields = []
    for line in fields_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        field = {
            "name": parts[0] if len(parts) > 0 else "",
            "label": parts[1] if len(parts) > 1 else parts[0] if parts else "",
            "type": parts[2] if len(parts) > 2 else "textbox",
            "required": (parts[3].lower() == "true") if len(parts) > 3 else False,
        }
        if any([clean_text(field["name"]), clean_text(field["label"]), clean_text(field["type"]), field["required"]]):
            fields.append(field)

    return {
        "inputType": "exploratory_workflow",
        "workflowId": f"{slugify(workflow_name).upper()}_001",
        "workflowName": workflow_name,
        "module": module,
        "feature": feature,
        "applicationCode": application_code.strip(),
        "source": {
            "createdBy": "UI user",
            "notes": "Workflow entered from MVP UI."
        },
        "resourceFiles": [resource_file],
        "pages": [
            {
                "name": page_name,
                "url": page_url
            }
        ],
        "observedPreconditions": preconditions,
        "observedSteps": steps,
        "observedExpectedResult": expected_result,
        "fields": fields,
        "observedValidations": validations,
        "testData": {
            "validUsername": valid_username.strip(),
            "validPassword": valid_password.strip()
        },
        "scenarioIntent": scenario_intent,
    }

# -------------------------------------------------------------------
# Extraction handling
# -------------------------------------------------------------------

def run_page_extraction(page_name: str, page_url: str):
    script_path = BASE_DIR / "scripts" / "extract_page_model.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Page extraction script not found.")

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--page-name",
            page_name,
            "--url",
            page_url
        ],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )

    stdout_text = (result.stdout or "").strip()
    stderr_text = (result.stderr or "").strip()
    combined_output = "\n".join(part for part in [stdout_text, stderr_text] if part).strip()

    if result.returncode != 0:
        error_message = combined_output or "Unknown extraction error."
        raise HTTPException(status_code=500, detail=f"Page extraction failed: {error_message}")

    if "extraction will be skipped" in combined_output.lower():
        raise HTTPException(status_code=400, detail=combined_output)

    return combined_output

def infer_type_from_raw_item(item: dict) -> str:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}
    input_type = clean_text(attrs.get("type", "")).lower()

    if tag in {"button", "ion-button", "ion-fab-button", "app-main-button"}:
        return "button"
    if tag == "a":
        return "link"
    if tag in {"select", "ion-select"}:
        return "dropdown"
    if tag == "textarea":
        return "textbox"
    if tag in {"input", "ion-input"}:
        if input_type == "password":
            return "password_textbox"
        return "textbox"
    return "element"

def infer_label_from_raw_item(item: dict) -> str:
    attrs = item.get("attributes", {}) or {}
    candidates = [
        item.get("label", ""),
        item.get("text", ""),
        attrs.get("placeholder", ""),
        attrs.get("aria-label", ""),
        attrs.get("name", ""),
        attrs.get("id", "")
    ]
    for candidate in candidates:
        value = clean_text(candidate)
        if value:
            return value
    return ""

def normalize_ui_element_name(label: str, role: str) -> str:
    base = slugify(label)
    base = re.sub(r"^(btn|button)_", "", base)
    base = re.sub(r"_(outline|icon)$", "", base)
    if base in {"person", "profile", "user"}:
        base = "profile"
    if role == "textbox" and not base.endswith("textbox"):
        return f"{base}_textbox"
    if role == "password_textbox" and not base.endswith("textbox"):
        return f"{base}_textbox"
    if role == "button" and not base.endswith("button"):
        return f"{base}_button"
    if role == "dropdown" and not base.endswith("dropdown"):
        return f"{base}_dropdown"
    if role == "link" and not base.endswith("link"):
        return f"{base}_link"
    return base or role or "element"

def infer_name_from_raw_item(item: dict, index: int) -> str:
    role = infer_type_from_raw_item(item)
    label = infer_label_from_raw_item(item)

    if label:
        return normalize_ui_element_name(label, role)
    return f"element_{index+1}"

def build_locator_from_raw_item(item: dict) -> str:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}
    text = clean_text(item.get("text", ""))
    placeholder = clean_text(attrs.get("placeholder", ""))
    aria = clean_text(attrs.get("aria-label", ""))
    name = clean_text(attrs.get("name", ""))
    el_id = clean_text(attrs.get("id", ""))

    def xpath_literal(value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f"\"{value}\""
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

    if el_id:
        return f"id={el_id}"
    if tag == "ion-fab-button":
        if text:
            return f"xpath=//ion-fab-button[.//ion-icon[@aria-label={xpath_literal(text)}] or normalize-space(.)={xpath_literal(text)}]"
        if aria:
            return f"xpath=//ion-fab-button[@aria-label={xpath_literal(aria)}]"
        return "xpath=//ion-fab-button"
    if placeholder and tag in {"input", "textarea"}:
        return f"xpath=//{tag}[@placeholder={xpath_literal(placeholder)}]"
    if name and tag in {"input", "textarea", "select"}:
        return f"xpath=//{tag}[@name={xpath_literal(name)}]"
    if aria:
        return f"xpath=//{tag}[@aria-label={xpath_literal(aria)}]"
    if text and tag in {"button", "a", "ion-button", "app-main-button"}:
        return f"xpath=//{tag}[normalize-space(.)={xpath_literal(text)}]"
    return f"xpath=//{tag}"

def normalize_extracted_element(item: dict, index: int) -> dict:
    extracted_name = infer_name_from_raw_item(item, index)
    inferred_type = infer_type_from_raw_item(item)
    locator = build_locator_from_raw_item(item)

    display_type = inferred_type
    if display_type == "password_textbox":
        display_type = "textbox"

    return {
        "approvedName": extracted_name,
        "type": display_type,
        "locator": locator,
        "approved": True,
    }

def get_page_review_data(workflow: dict):
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else "page"
    page_url = pages[0].get("url") if pages else ""
    workflow_name = clean_text(str(workflow.get("workflowName", ""))) or page_name

    page_dir = POM_DIR / page_name
    elements_path = page_dir / f"{page_name}.elements.json"
    screenshot_path = page_dir / f"{page_name}.png"
    resource_path = page_dir / f"{page_name}.resource"

    extracted_elements_data = []
    approved_elements_data = []
    if elements_path.exists():
        try:
            data = read_json(elements_path)
            if isinstance(data, list):
                extracted_elements_data = data
            elif isinstance(data, dict):
                approved_elements_data = data.get("elements", [])
                extracted_elements_data = data.get("rawElements", approved_elements_data)
        except Exception:
            extracted_elements_data = []
            approved_elements_data = []

    source_elements = approved_elements_data or extracted_elements_data
    normalized_elements = []

    resource_elements_by_locator = {}
    if resource_path.exists():
        try:
            resource_context = parse_resource_file(resource_path)
            for variable in resource_context.get("variables", []):
                locator = clean_text(str(variable.get("value", "")))
                variable_name = clean_text(str(variable.get("name", "")))
                if not locator or not variable_name:
                    continue
                normalized_name = normalize_ui_element_name(variable_name.lower(), "button" if variable_name.upper().endswith("_BUTTON") else "element")
                resource_elements_by_locator[locator] = {
                    "approvedName": normalized_name,
                    "type": "button" if normalized_name.endswith("_button") else "element",
                    "locator": locator,
                    "approved": True,
                }
        except Exception:
            resource_elements_by_locator = {}

    for idx, item in enumerate(source_elements):
        if not isinstance(item, dict):
            continue
        if "approvedName" in item and "locator" in item and "type" in item:
            locator = clean_text(item.get("locator", ""))
            stronger = resource_elements_by_locator.get(locator)
            if stronger:
                normalized_elements.append(stronger)
            else:
                normalized_elements.append({
                    "approvedName": item.get("approvedName") or f"element_{idx+1}",
                    "type": item.get("type", "element"),
                    "locator": locator,
                    "approved": item.get("approved", True),
                })
        else:
            inferred = normalize_extracted_element(item, idx)
            stronger = resource_elements_by_locator.get(inferred.get("locator", ""))
            normalized_elements.append(stronger or inferred)

    if resource_path.exists() and normalized_elements:
        try:
            config = validate_robot_config(load_robot_ai_json(CONFIG_PATH))
            ai_cfg = config.get("ai", {})
            if ai_cfg.get("enabled", True):
                endpoint = ai_cfg.get("endpoint", "").strip()
                token = get_robot_ai_token(ai_cfg)
                if endpoint and token:
                    resource_context = parse_resource_file(resource_path)
                    ai_payload = {
                        "workflow": clean_workflow_for_prompting(workflow),
                        "raw_elements": extracted_elements_data,
                        "approved_elements": approved_elements_data,
                        "ui_elements": normalized_elements,
                        "resource_file": resource_context,
                        "goal": "Review and refine the page review UI model for display. Prefer approved elements and resource-backed variables, preserve strong locator choices already present, keep only meaningful visible page elements, and return only valid JSON as an array of objects with keys approvedName, type, locator, approved. Do not invent elements that are not grounded in the extracted data, approved elements, or current resource file."
                    }
                    ai_prompt = (
                        "You are AI Layer P1: a page-model refinement specialist for an AI-first automation framework.\n"
                        "Return only valid JSON array data.\n"
                        "Preserve strong resource-backed semantics and approved element decisions when available.\n"
                        "Keep the page model meaningful, visible, and review-friendly.\n\n"
                        f"Input JSON:\n{json.dumps(ai_payload, indent=2)}"
                    )
                    reviewed_elements_raw = call_ai_with_workflow_session(
                        workflow_name=workflow_name,
                        stage="page_ui_review",
                        endpoint=endpoint,
                        token=token,
                        prompt=ai_prompt,
                        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
                        verify_ssl=ai_cfg.get("verify_ssl", False),
                    )
                    reviewed_elements = json.loads(strip_markdown_fences(reviewed_elements_raw))
                    if isinstance(reviewed_elements, list):
                        normalized_reviewed = []
                        for idx, item in enumerate(reviewed_elements, start=1):
                            if not isinstance(item, dict):
                                continue
                            approved_name = clean_text(str(item.get("approvedName", ""))) or f"element_{idx}"
                            locator = clean_text(str(item.get("locator", "")))
                            if not locator:
                                continue
                            normalized_reviewed.append({
                                "approvedName": approved_name,
                                "type": clean_text(str(item.get("type", "element"))).lower() or "element",
                                "locator": locator,
                                "approved": bool(item.get("approved", True)),
                            })
                        if normalized_reviewed:
                            normalized_elements = normalized_reviewed
        except Exception:
            pass

    screenshot_web_path = None
    if screenshot_path.exists():
        screenshot_web_path = f"/static-artifacts/{page_name}/{page_name}.png"

    return {
        "page_name": page_name,
        "page_url": page_url,
        "elements": normalized_elements,
        "screenshot_web_path": screenshot_web_path,
        "raw_elements_count": len(extracted_elements_data or normalized_elements),
        "elements_path": elements_path,
        "raw_elements": extracted_elements_data,
        "approved_elements": approved_elements_data,
    }

# -------------------------------------------------------------------
# Keyword handling
# -------------------------------------------------------------------

def get_keywords_path(page_name: str) -> Path:
    return POM_DIR / page_name / f"{page_name}.keywords.json"

def get_resource_path(page_name: str) -> Path:
    return POM_DIR / page_name / f"{page_name}.resource"

def load_approved_elements_for_workflow(workflow: dict) -> list[dict]:
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else "page"
    elements_path = POM_DIR / page_name / f"{page_name}.elements.json"

    approved = []
    if elements_path.exists():
        try:
            data = read_json(elements_path)
            if isinstance(data, dict):
                approved = data.get("elements", [])
            elif isinstance(data, list):
                approved = data
        except Exception:
            approved = []

    canonical_elements = []
    for item in approved:
        if not isinstance(item, dict):
            continue
        approved_name = clean_text(str(item.get("approvedName", "")))
        locator = clean_text(str(item.get("locator", "")))
        if not approved_name or not locator or not bool(item.get("approved", True)):
            continue
        canonical_elements.append({
            "approvedName": approved_name,
            "type": clean_text(str(item.get("type", "element"))).lower() or "element",
            "locator": locator,
            "approved": True,
        })
    return canonical_elements

def build_keywords_from_elements(elements: list[dict]) -> list[dict]:
    keywords = []
    for idx, element in enumerate(elements, start=1):
        if not isinstance(element, dict) or not bool(element.get("approved", True)):
            continue

        element_name = clean_text(element.get("approvedName", ""))
        locator = clean_text(element.get("locator", ""))
        element_type = clean_text(element.get("type", "element")).lower()

        if not element_name or not locator:
            continue

        keyword_title = to_keyword_title(element_name)

        if element_type == "textbox":
            keyword_name = f"Enter {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{to_robot_variable_name(element_name)}}}    10s",
                f"Input Text    ${{{to_robot_variable_name(element_name)}}}    ${{text}}"
            ]
            arguments = ["text"]
            action = "input"
        elif element_type == "button":
            keyword_name = f"Click {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{to_robot_variable_name(element_name)}}}    10s",
                f"Click Element    ${{{to_robot_variable_name(element_name)}}}"
            ]
            arguments = []
            action = "click"
        elif element_type == "dropdown":
            keyword_name = f"Select {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{to_robot_variable_name(element_name)}}}    10s",
                f"Select From List By Label    ${{{to_robot_variable_name(element_name)}}}    ${{value}}"
            ]
            arguments = ["value"]
            action = "select"
        elif element_type == "link":
            keyword_name = f"Click {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{to_robot_variable_name(element_name)}}}    10s",
                f"Click Element    ${{{to_robot_variable_name(element_name)}}}"
            ]
            arguments = []
            action = "click"
        else:
            keyword_name = f"Use {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{to_robot_variable_name(element_name)}}}    10s",
                f"Click Element    ${{{to_robot_variable_name(element_name)}}}"
            ]
            arguments = []
            action = "generic"

        keywords.append({
            "keywordId": f"KW_{idx:03d}",
            "keywordName": keyword_name,
            "targetElement": element_name,
            "action": action,
            "arguments": arguments,
            "implementation": implementation,
            "approved": True,
        })

    return keywords

def get_keyword_review_data(workflow: dict):
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else "page"
    keywords_path = get_keywords_path(page_name)
    resource_path = get_resource_path(page_name)

    approved_elements = load_approved_elements_for_workflow(workflow)
    approved_elements_by_name = {
        clean_text(str(item.get("approvedName", ""))): item
        for item in approved_elements
        if clean_text(str(item.get("approvedName", "")))
    }
    approved_titles_to_name = {
        to_keyword_title(name).lower(): name
        for name in approved_elements_by_name
    }

    disallowed_resource_keywords = {
        "open page",
        "open browser to page",
    }

    def resolve_target_element(keyword_name: str) -> str:
        lowered_name = clean_text(keyword_name).lower()
        for candidate_title, element_name in approved_titles_to_name.items():
            if candidate_title and candidate_title in lowered_name:
                return element_name
        return ""

    keywords = []
    if resource_path.exists() and approved_elements_by_name:
        try:
            resource_context = parse_resource_file(resource_path)
            for idx, keyword in enumerate(resource_context.get("keywords", []), start=1):
                keyword_name = clean_text(str(keyword.get("name", "")))
                lowered_name = keyword_name.lower()
                if not keyword_name or lowered_name in disallowed_resource_keywords:
                    continue

                target_element = resolve_target_element(keyword_name)
                if not target_element:
                    continue

                action = "generic"
                if lowered_name.startswith("click "):
                    action = "click"
                elif lowered_name.startswith("enter ") or lowered_name.startswith("input "):
                    action = "input"
                elif lowered_name.startswith("select "):
                    action = "select"
                elif lowered_name.startswith("verify "):
                    action = "verify"

                implementation_lines = [line.rstrip() for line in keyword.get("body", []) if clean_text(str(line))]
                keywords.append({
                    "keywordId": f"KW_{idx:03d}",
                    "keywordName": keyword_name,
                    "targetElement": target_element,
                    "action": action,
                    "arguments": [arg.replace("${", "").replace("}", "") for arg in keyword.get("args", [])],
                    "implementation": implementation_lines,
                    "approved": True,
                })
        except Exception:
            keywords = []

    if not keywords and keywords_path.exists() and approved_elements_by_name:
        try:
            payload = read_json(keywords_path)
            raw_keywords = payload.get("keywords", [])
            filtered_keywords = []
            for item in raw_keywords:
                keyword_name = clean_text(str(item.get("keywordName", "")))
                if not keyword_name or keyword_name.lower() in disallowed_resource_keywords:
                    continue
                target_element = clean_text(str(item.get("targetElement", ""))) or resolve_target_element(keyword_name)
                if target_element not in approved_elements_by_name:
                    continue
                normalized_item = dict(item)
                normalized_item["targetElement"] = target_element
                if not normalized_item.get("implementation"):
                    normalized_item["implementation"] = []
                filtered_keywords.append(normalized_item)
            keywords = filtered_keywords
        except Exception:
            keywords = []

    if not keywords:
        keywords = build_keywords_from_elements(approved_elements)

    if resource_path.exists() and approved_elements_by_name:
        try:
            workflow_name = clean_text(str(workflow.get("workflowName", ""))) or page_name
            config = validate_robot_config(load_robot_ai_json(CONFIG_PATH))
            ai_cfg = config.get("ai", {})
            if ai_cfg.get("enabled", True):
                endpoint = ai_cfg.get("endpoint", "").strip()
                token = get_robot_ai_token(ai_cfg)
                if endpoint and token and keywords:
                    resource_context = parse_resource_file(resource_path)
                    ai_payload = {
                        "workflow": clean_workflow_for_prompting(workflow),
                        "approved_elements": approved_elements,
                        "resource_keywords": keywords,
                        "resource_file": resource_context,
                        "goal": "Review and refine the provided page-specific keyword models for MVP UI display. Keep only approved-element-backed keywords, preserve implementation from the current resource file, improve naming/action classification if needed, and return only valid JSON as an array of keyword objects with keys keywordId, keywordName, targetElement, action, arguments, implementation, approved. Do not invent keywords not grounded in the current resource file and approved elements."
                    }
                    ai_prompt = (
                        "You are AI Layer K1: a keyword-review refinement specialist for an AI-first automation framework.\n"
                        "Return only valid JSON array data.\n"
                        "Preserve the current resource-backed implementations.\n"
                        "Use approved elements as the source of truth for targetElement mapping.\n"
                        "Keep the keyword list thin, readable, and page-specific.\n\n"
                        f"Input JSON:\n{json.dumps(ai_payload, indent=2)}"
                    )
                    reviewed_keywords_raw = call_ai_with_workflow_session(
                        workflow_name=workflow_name,
                        stage="keyword_ui_review",
                        endpoint=endpoint,
                        token=token,
                        prompt=ai_prompt,
                        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
                        verify_ssl=ai_cfg.get("verify_ssl", False),
                    )
                    reviewed_keywords = json.loads(strip_markdown_fences(reviewed_keywords_raw))
                    if isinstance(reviewed_keywords, list):
                        normalized_reviewed = []
                        for idx, item in enumerate(reviewed_keywords, start=1):
                            if not isinstance(item, dict):
                                continue
                            keyword_name = clean_text(str(item.get("keywordName", "")))
                            if not keyword_name or keyword_name.lower() in disallowed_resource_keywords:
                                continue
                            target_element = clean_text(str(item.get("targetElement", ""))) or resolve_target_element(keyword_name)
                            if target_element not in approved_elements_by_name:
                                continue
                            implementation = item.get("implementation", [])
                            if isinstance(implementation, str):
                                implementation = [line.rstrip() for line in implementation.splitlines() if clean_text(line)]
                            implementation = [str(line).rstrip() for line in implementation if clean_text(str(line))]
                            arguments = item.get("arguments", [])
                            if isinstance(arguments, str):
                                arguments = [arg.strip() for arg in arguments.split(",") if arg.strip()]
                            arguments = [str(arg).replace("${", "").replace("}", "").strip() for arg in arguments if clean_text(str(arg))]
                            normalized_reviewed.append({
                                "keywordId": clean_text(str(item.get("keywordId", ""))) or f"KW_{idx:03d}",
                                "keywordName": keyword_name,
                                "targetElement": target_element,
                                "action": clean_text(str(item.get("action", ""))) or "generic",
                                "arguments": arguments,
                                "implementation": implementation,
                                "approved": bool(item.get("approved", True)),
                            })
                        if normalized_reviewed:
                            keywords = normalized_reviewed
        except Exception:
            pass

    return {
        "page_name": page_name,
        "keywords_path": keywords_path,
        "resource_path": resource_path,
        "keywords": keywords,
        "approved_elements": approved_elements,
    }

def save_keywords_for_workflow(workflow: dict, keywords: list[dict]):
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else "page"
    keywords_path = get_keywords_path(page_name)
    resource_path = get_resource_path(page_name)

    approved_elements = load_approved_elements_for_workflow(workflow)
    approved_elements_by_name = {
        clean_text(str(item.get("approvedName", ""))): item
        for item in approved_elements
        if clean_text(str(item.get("approvedName", "")))
    }
    approved_titles_to_name = {
        to_keyword_title(name).lower(): name
        for name in approved_elements_by_name
    }

    disallowed_resource_keywords = {
        "open page",
        "open browser to page",
    }

    def resolve_target_element(keyword_name: str, provided_target: str = "") -> str:
        target = clean_text(provided_target)
        if target in approved_elements_by_name:
            return target
        lowered_name = clean_text(keyword_name).lower()
        for candidate_title, element_name in approved_titles_to_name.items():
            if candidate_title and candidate_title in lowered_name:
                return element_name
        return ""

    resource_keywords_by_name = {}
    if resource_path.exists():
        try:
            resource_context = parse_resource_file(resource_path)
            for resource_keyword in resource_context.get("keywords", []):
                resource_keyword_name = clean_text(str(resource_keyword.get("name", "")))
                if resource_keyword_name:
                    resource_keywords_by_name[resource_keyword_name.lower()] = resource_keyword
        except Exception:
            resource_keywords_by_name = {}

    approved_keywords_by_name = {
        clean_text(str(item.get("keywordName", ""))).lower(): item
        for item in keywords
        if clean_text(str(item.get("keywordName", "")))
    }

    normalized_keywords = []
    if resource_keywords_by_name and approved_elements_by_name:
        for idx, (keyword_name_lower, resource_keyword) in enumerate(resource_keywords_by_name.items(), start=1):
            if keyword_name_lower in disallowed_resource_keywords:
                continue

            resource_keyword_name = clean_text(str(resource_keyword.get("name", "")))
            approved_keyword = approved_keywords_by_name.get(keyword_name_lower, {})
            target_element = resolve_target_element(resource_keyword_name, str(approved_keyword.get("targetElement", "")))
            if not target_element:
                continue

            implementation = resource_keyword.get("body") or []
            implementation = [str(line).rstrip() for line in implementation if clean_text(str(line))]

            arguments = resource_keyword.get("args") or []
            arguments = [str(arg).replace("${", "").replace("}", "").strip() for arg in arguments if clean_text(str(arg))]

            action = clean_text(str(approved_keyword.get("action", "")))
            if not action:
                lowered_name = resource_keyword_name.lower()
                if lowered_name.startswith("click "):
                    action = "click"
                elif lowered_name.startswith("enter ") or lowered_name.startswith("input "):
                    action = "input"
                elif lowered_name.startswith("select "):
                    action = "select"
                elif lowered_name.startswith("verify "):
                    action = "verify"
                else:
                    action = "generic"

            normalized_keywords.append({
                "keywordId": clean_text(str(approved_keyword.get("keywordId", ""))) or f"KW_{idx:03d}",
                "keywordName": resource_keyword_name,
                "targetElement": target_element,
                "action": action,
                "arguments": arguments,
                "implementation": implementation,
                "approved": bool(approved_keyword.get("approved", True)),
            })
    else:
        for idx, keyword in enumerate(keywords, start=1):
            keyword_name = clean_text(str(keyword.get("keywordName", "")))
            if not keyword_name or keyword_name.lower() in disallowed_resource_keywords:
                continue

            target_element = resolve_target_element(keyword_name, str(keyword.get("targetElement", "")))
            if not target_element:
                continue

            implementation = keyword.get("implementation", [])
            if isinstance(implementation, str):
                implementation = [line.rstrip() for line in implementation.splitlines() if line.strip()]
            implementation = [str(line).rstrip() for line in implementation if clean_text(str(line))]

            arguments = keyword.get("arguments", [])
            if isinstance(arguments, str):
                arguments = [arg.strip() for arg in arguments.split(",") if arg.strip()]
            arguments = [str(arg).replace("${", "").replace("}", "").strip() for arg in arguments if clean_text(str(arg))]

            normalized_keywords.append({
                "keywordId": clean_text(str(keyword.get("keywordId", ""))) or f"KW_{idx:03d}",
                "keywordName": keyword_name,
                "targetElement": target_element,
                "action": clean_text(str(keyword.get("action", ""))) or "generic",
                "arguments": arguments,
                "implementation": implementation,
                "approved": bool(keyword.get("approved", True)),
            })

    payload = {
        "pageName": page_name,
        "keywords": normalized_keywords,
    }
    write_json(keywords_path, payload)

# -------------------------------------------------------------------
# AI-driven resource generation
# -------------------------------------------------------------------

def build_resource_generation_prompt(
    workflow: dict,
    approved_elements: list[dict],
    approved_keywords: list[dict],
    approved_manual_tests: list[dict] | None = None,
    common_resource_context: list[dict] | None = None,
    existing_page_resource: str = "",
) -> str:
    prompt_ready_workflow = clean_workflow_for_prompting(workflow)
    payload = {
        "workflow": prompt_ready_workflow,
        "approved_elements": approved_elements,
        "approved_keywords": approved_keywords,
        "approved_manual_tests": approved_manual_tests or [],
        "common_resource_context": common_resource_context or [],
        "existing_page_resource": existing_page_resource,
    }

    return (
        "You are an expert Robot Framework resource-file designer working on a maintainable enterprise UI automation framework.\n"
        "Generate exactly one valid page-specific Robot Framework .resource file.\n\n"
        "Primary objective:\n"
        "- Build a reusable page resource file that contains only page-specific locators, page-specific action keywords, page-specific validation keywords, and page-specific test-data variables inferred from approved workflow and approved manual tests.\n"
        "- You are also given common/shared resource context. Reuse that knowledge and avoid duplicating common keywords, browser lifecycle keywords, generic navigation keywords, and generic variables already suitable for shared resources.\n"
        "- If an existing page resource is provided, treat this as a review-and-repair task as well: preserve good page-specific content, remove duplicated common concerns, tighten formatting, and improve Robot syntax and maintainability.\n\n"
        "Mandatory output rules:\n"
        "- Return only Robot Framework resource code.\n"
        "- Do not include markdown fences.\n"
        "- Include only these sections if needed: *** Settings ***, *** Variables ***, *** Keywords ***.\n"
        "- Use SeleniumLibrary in Settings only if truly needed in this page resource.\n"
        "- Use the approved elements to create locator variables.\n"
        "- Use the approved keywords as the foundation for reusable keyword implementations.\n"
        "- Treat empty placeholder rows in workflow.fields as noise and ignore them.\n"
        "- Create reusable test-data variables based on approved manual tests, not just workflow.testData.\n"
        "- Valid business data should come from workflow.testData if present.\n"
        "- Use AI judgment to keep the Variables section minimal, semantic, and maintainable rather than exhaustively materializing every test-data variation.\n"
        "- Create explicit page-resource variables only for true reusable business data or semantically distinct data sets, such as ${VALID_USERNAME}, ${VALID_PASSWORD}, ${INVALID_USERNAME}, ${INVALID_PASSWORD}, locked-user credentials, role-specific credentials, or other clearly distinct business cases justified by approved manual tests.\n"
        "- Do NOT create unnecessary wrapper or alias variables for Robot built-ins or simple compositions. For blank input use ${EMPTY} directly in test/keyword usage, and for whitespace use ${SPACE} directly or inline composition such as ${SPACE}${SPACE}${VALID_USERNAME}${SPACE}.\n"
        "- Do NOT define explicit variables such as ${BLANK_USERNAME}, ${BLANK_PASSWORD}, ${SPACE_USERNAME}, ${SPACE_PASSWORD}, ${USERNAME_WITH_SPACES}, ${PASSWORD_WITH_SPACES}, or similar derived aliases when the same intent can be expressed directly with built-ins and existing semantic variables.\n"
        "- Avoid duplicate semantic variables. If one ${INVALID_USERNAME} and one ${INVALID_PASSWORD} are sufficient for negative authentication scenarios, reuse them across those scenarios instead of inventing variants such as _ALT, _SECONDARY, _NEGATIVE, or other duplicates unless the approved manual tests clearly require truly different invalid data classes.\n"
        "- Prefer inline composition over new variables for derived forms of existing data. Examples: use ${SPACE}${VALID_USERNAME}${SPACE} instead of creating ${USERNAME_WITH_SPACES}; use repeated semantic variables or built-ins inline rather than storing one-off composed aliases.\n"
        "- Avoid hardcoding dedicated LONG variables when the long input is only a derived repetition of an existing semantic value. If a long-value scenario can be represented by composing or repeating an existing semantic variable at usage time, prefer that over adding a separate page variable, unless a fixed boundary test value must be reused across multiple tests.\n"
        "- Do NOT define Robot Framework built-in variables like ${EMPTY}, ${SPACE}, ${True}, ${False}, or ${None}; reference them directly only where needed.\n"
        "- Keep naming clean and maintainable.\n"
        "- Prefer reusable validation keywords when expected results mention UI messages, masking, redirection, visibility, enabled/disabled state, or validation behavior.\n"
        "- Do not invent unnecessary variables or keywords.\n"
        "- Preserve a clean resource file structure with compact formatting: no blank lines between consecutive variable definitions, at most one blank line between major sections, and at most one blank line between keyword blocks.\n"
        "- Use modern Robot Framework syntax only. Do NOT use deprecated loop syntax such as ': FOR' or backslash-prefixed loop bodies. Use 'FOR ... END' syntax if a loop is truly necessary.\n"
        "- Use AI intelligence instead of hardcoded assumptions.\n\n"
        "Shared-vs-page resource rules:\n"
        "- Generic or common variables belong in resources/common_keywords.resource, not in the page resource. Examples include browser selection such as ${BROWSER}, generic timeout variables, generic environment/base-url variables, shared credential defaults used across suites, and other cross-page defaults.\n"
        "- Generic or common keywords belong in resources/common_keywords.resource, not in the page resource. Examples include Open Browser To Url, Go To Url, Open Login Page, Open Browser Session, Close Browser Session, Wait For Element To Be Ready, Click When Ready, Input Text When Ready, generic click/input wrappers, and other cross-page/browser lifecycle helpers.\n"
        "- If a common/shared keyword already exists or is strongly implied by common_resource_context, do not recreate it in the page resource. Instead, design the page resource to rely on the shared/common resource layer.\n"
        "- The page resource should contain only page-specific behavior such as entering credentials into this page, clicking page-specific buttons, and validating page-specific messages or field behavior.\n"
        "- The page resource must import ../../resources/common_keywords.resource in its *** Settings *** section whenever it uses shared/common helpers.\n"
        "- Page-specific action keywords should prefer shared/common helpers such as Input Text When Ready, Click When Ready, and Wait For Element To Be Ready whenever those helpers fit the action. Avoid raw SeleniumLibrary calls in page keywords when an appropriate common helper exists.\n"
        "- The page resource must import ../../resources/common_keywords.resource in *** Settings ***. Treat this import as mandatory for generated page resources in this framework.\n"
        "- If a page keyword uses a common helper or depends on a common variable, the page resource must reuse that helper or variable through the common resource import instead of inlining raw SeleniumLibrary behavior.\n"
        "- Insert exactly one blank line between major sections such as *** Settings ***, *** Variables ***, and *** Keywords ***. Do not leave extra blank lines inside the Settings section. There must be no blank line immediately before *** Keywords *** when it directly follows *** Variables ***; only a single section-separator blank line is allowed.\n"
        "- Do not leave blank lines between consecutive variable definitions.\n"
        "- Prefer atomic page-object keywords over workflow/business-flow orchestration. Good examples are Enter Username, Enter Password, Click Sign In Button, Verify Login Error Message, Verify Password Field Is Masked, Verify Login Page Loaded.\n"
        "- Avoid business-flow keywords that merely orchestrate a whole login scenario when they are not truly page-specific. Avoid keywords such as Login With Valid Credentials, Login With Credentials, Submit Login, Perform Successful Login, or other scenario wrappers unless there is a compelling page-specific reason.\n"
        "- Do not duplicate keywords that already exist in common/shared resources.\n\n"
        "Resource quality requirements:\n"
        "- The Variables section should centralize reusable page-level test data so generated .robot test suites do not hardcode those values.\n"
        "- Create reusable page-resource variables only for semantically distinct edge-case or business data that must remain stable and reusable across multiple tests. For blank values, whitespace-only values, padded values, and other simple derived forms, prefer Robot built-ins and inline composition instead of creating dedicated page variables unless a fixed reusable boundary value is genuinely required.\n"
        "- Keep the Variables section semantically clean: variable names must accurately match the actual values. For example, a variable named WITH_SPACES must really contain spaces; otherwise do not create it.\n"
        "- Remove unnecessary, duplicate, or weak variables if they are not clearly supported by approved manual tests.\n"
        "- Do not leave reusable edge-case or credential-like values inline in test suites; define them as page-resource variables so they are easier to maintain later.\n"
        "- The Keywords section should contain reusable business-friendly page actions and validations rather than low-level one-off steps only.\n"
        "- If approved manual tests mention password masking, create a reusable page-specific keyword to verify password masking behavior if feasible in the framework.\n"
        "- If approved manual tests mention validation messages, incorrect credentials, blocked login, rejection behavior, required-field behavior, whitespace handling, case sensitivity, duplicate submission behavior, copy-paste behavior, or successful navigation, create reusable page-specific validation/assertion keywords where feasible instead of relying only on page-loaded checks.\n"
        "- Prefer creating page validation keywords such as Verify Authentication Error Message, Verify Username Required Validation, Verify Password Required Validation, Verify Login Rejected, Verify Successful Login Redirect, Verify Duplicate Submission Prevented, or other grounded page-specific assertions when approved manual tests justify them.\n"
        "- Do not create generic browser open/close keywords here if those belong in common/shared resources.\n"
        "- Keep formatting compact with no excessive blank lines and use modern Robot syntax only.\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )

def normalize_resource_content(content: str) -> str:
    content = strip_markdown_fences(content)
    lines = content.splitlines()

    cleaned: list[str] = []
    blank_count = 0
    in_variables_section = False
    previous_was_variable = False

    for line in lines:
        normalized_line = line.rstrip()
        stripped = normalized_line.strip()
        lower = stripped.lower()

        if stripped.startswith("***"):
            while cleaned and cleaned[-1] == "":
                cleaned.pop()
            in_variables_section = lower == "*** variables ***"
            previous_was_variable = False
            blank_count = 0
            if cleaned:
                cleaned.append("")
            cleaned.append(stripped)
            continue

        if stripped == "":
            if in_variables_section:
                continue
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")
            continue

        blank_count = 0
        if in_variables_section:
            previous_was_variable = bool(re.match(r"^\$\{[^}]+\}\s{2,}.+", stripped))
        else:
            previous_was_variable = False
        cleaned.append(normalized_line)

    content = "\n".join(cleaned).strip() + "\n"
    content = re.sub(r"(?m)^\s*: FOR\b", "FOR", content)
    content = re.sub(r"(?m)^\s*\\\s+", "    ", content)

    if re.search(r"(?im)^\s*\*\*\*\s*settings\s*\*\*\*", content):
        if re.search(r"(?im)^\s*Resource\s+\.\./\.\./resources/common_keywords\.resource\s*$", content) is None:
            settings_match = re.search(r"(?is)(^\*\*\*\s*settings\s*\*\*\*\s*\n)(.*?)(?=^\*\*\*|\Z)", content, re.MULTILINE)
            if settings_match:
                settings_body = settings_match.group(2)
                new_settings_body = "Resource    ../../resources/common_keywords.resource\n" + settings_body.lstrip("\n")
                content = content[:settings_match.start(2)] + new_settings_body + content[settings_match.end(2):]
    else:
        content = "*** Settings ***\nResource    ../../resources/common_keywords.resource\n\n" + content

    return content


def build_resource_review_prompt(
    workflow: dict,
    approved_elements: list[dict],
    approved_keywords: list[dict],
    approved_manual_tests: list[dict],
    common_resource_context: list[dict],
    generated_resource: str,
) -> str:
    prompt_ready_workflow = clean_workflow_for_prompting(workflow)
    payload = {
        "workflow": prompt_ready_workflow,
        "approved_elements": approved_elements,
        "approved_keywords": approved_keywords,
        "approved_manual_tests": approved_manual_tests,
        "common_resource_context": common_resource_context,
        "generated_page_resource": generated_resource,
    }

    return (
        "You are a senior Robot Framework resource-file reviewer and repair specialist.\n"
        "Your task is to review an already generated page-specific .resource file and return a corrected version of the same file.\n\n"
        "Review objectives:\n"
        "- Keep only page-specific locators, page-specific actions, page-specific validations, and page-specific test-data variables.\n"
        "- Remove or avoid duplicated common/shared variables and keywords that belong in resources/common_keywords.resource.\n"
        "- Improve formatting, Robot syntax quality, and maintainability.\n"
        "- Preserve useful page-specific content grounded in approved elements, approved keywords, and approved manual tests.\n\n"
        "Mandatory repair rules:\n"
        "- Return only Robot Framework resource code with no markdown fences and no explanation.\n"
        "- Keep the file page-specific. Generic browser lifecycle, generic navigation, generic waits, generic click/input wrappers, ${BROWSER}, ${DEFAULT_TIMEOUT}, and other cross-page concerns belong in resources/common_keywords.resource, not here.\n"
        "- Page action keywords should reuse shared/common helpers such as Input Text When Ready, Click When Ready, and Wait For Element To Be Ready when applicable instead of directly repeating raw SeleniumLibrary interaction patterns.\n"
        "- If a common/shared keyword already exists or is implied by common_resource_context, do not recreate it here.\n"
        "- Remove business-flow keywords that are too generic or duplicate shared/common behavior.\n"
        "- Keep reusable page-specific actions and page-specific validations.\n"
        "- Prefer atomic page-object keywords and validations. Remove or simplify scenario-wrapper keywords such as Login With Credentials, Login With Valid Credentials, Submit Login, Perform Login Flow, or other business-flow orchestration if they are not clearly necessary as page-level abstractions.\n"
        "- Keep page-specific test-data variables only when they are clearly useful, reusable, and semantically accurate.\n"
        "- Remove unused, duplicate, overly noisy, or weak one-off variables when they are not justified by approved manual tests. Merge similar variables where appropriate.\n"
        "- Eliminate unnecessary alias variables for Robot built-ins and simple compositions. Replace variables such as ${BLANK_*} that only equal ${EMPTY}, ${SPACE_*} that only equal whitespace, ${*_WITH_SPACES}, and similar wrapper aliases with direct built-in usage or inline composition whenever possible.\n"
        "- Collapse duplicate negative data into a single semantic variable when the intent is the same. For example, keep one ${INVALID_USERNAME} and one ${INVALID_PASSWORD} unless the approved manual tests clearly require distinct invalid classes. Remove suffix variants such as _ALT or other duplicates when they do not add meaning.\n"
        "- Prefer inline composition over dedicated derived variables. If a value can be expressed by combining ${SPACE}, ${EMPTY}, and existing semantic variables such as ${VALID_USERNAME} or ${VALID_PASSWORD}, do that instead of keeping a separate page variable.\n"
        "- Avoid dedicated long-value aliases when they are just repeated forms of existing semantic variables unless a stable reusable boundary value is genuinely needed across multiple tests.\n"
        "- If a variable name implies spaces, blanks, long text, invalid credentials, or another property, ensure the value really matches that meaning; otherwise repair or remove it.\n"
        "- Ensure the page resource imports ../../resources/common_keywords.resource in *** Settings ***. Treat this import as mandatory for generated page resources in this framework.\n"
        "- Use compact formatting with minimal blank lines and no blank lines between consecutive variable definitions.\n"
        "- Keep exactly one blank line between major sections. Do not leave extra blank lines inside *** Settings ***. There must be no extra blank line immediately before *** Keywords *** beyond the single section separator.\n"
        "- Use modern Robot Framework syntax only. Do not use deprecated ': FOR' syntax or backslash-prefixed loop bodies.\n"
        "- Prefer page-specific validation keywords for incorrect credentials, validation messages, blocked login, and password masking when approved manual tests imply them.\n"
        "- Do not allow the page resource to stop at only generic validations such as Verify Login Failed or Verify Page Loaded if approved manual tests imply richer assertions. Add more specific page validation keywords for authentication error messages, required-field validation, successful login redirect, duplicate submission prevention, or other grounded outcomes whenever feasible.\n"
        "- Do not create generic browser open/close keywords here.\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )


def build_resource_alignment_prompt(
    workflow: dict,
    approved_elements: list[dict],
    approved_keywords: list[dict],
    parsed_resource_keywords: list[dict],
    parsed_resource_variables: list[dict],
) -> str:
    payload = {
        "workflow": clean_workflow_for_prompting(workflow),
        "approved_elements": approved_elements,
        "approved_keywords": approved_keywords,
        "parsed_resource_keywords": parsed_resource_keywords,
        "parsed_resource_variables": parsed_resource_variables,
        "goal": "Review the generated page resource artifacts for alignment. Use approved elements as the canonical source of truth for what element-backed variables and action keywords are allowed. Preserve practical, user-friendly keyword names when they remain semantically aligned to approved elements. Remove any variable or keyword that is not grounded in approved elements or approved keyword intent. Return only valid JSON with keys allowed_variables and allowed_keywords, where allowed_variables is a list of variable names and allowed_keywords is a list of keyword names that should remain in UI and derivative artifacts."
    }
    return (
        "You are AI Layer R1: a page-resource alignment reviewer for an end-to-end AI automation framework.\n"
        "Return only valid JSON.\n"
        "Use approved elements as the canonical page model.\n"
        "Use approved keyword intent to preserve practical business-friendly names where appropriate.\n"
        "Do not invent new variables or keywords.\n"
        "Remove anything not grounded in approved elements or approved keyword intent.\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )


def generate_resource_for_workflow(workflow: dict, approved_keywords: list[dict]):
    review_data = get_page_review_data(workflow)
    page_name = review_data["page_name"]
    approved_elements = load_approved_elements_for_workflow(workflow)

    approved_manual_tests = []
    workflow_name = slugify(str(workflow.get("workflowName", "")))
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    if manual_path.exists():
        try:
            approved_manual_tests = extract_manual_test_cases(read_json(manual_path))
        except Exception:
            approved_manual_tests = []

    common_resource_context = []
    resources_dir = BASE_DIR / "resources"
    if resources_dir.exists():
        for resource_path in sorted(resources_dir.glob("*.resource")):
            try:
                common_resource_context.append(parse_resource_file(resource_path))
            except Exception:
                continue

    config = validate_robot_config(load_robot_ai_json(CONFIG_PATH))
    ai_cfg = config["ai"]

    if not ai_cfg.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI is disabled in configuration.")

    endpoint = ai_cfg.get("endpoint", "").strip()
    token = get_robot_ai_token(ai_cfg)
    if not endpoint or not token:
        raise HTTPException(status_code=400, detail="AI endpoint/token missing for resource generation.")

    resource_path = get_resource_path(page_name)
    existing_page_resource = read_text(resource_path)

    prompt = build_resource_generation_prompt(
        workflow,
        approved_elements,
        approved_keywords,
        approved_manual_tests,
        common_resource_context,
        existing_page_resource,
    )
    resource_content = call_ai_with_workflow_session(
        workflow_name=page_name,
        stage="resource_generation",
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )

    resource_content = normalize_resource_content(resource_content)

    resource_context_preview = parse_resource_file(resource_path) if resource_path.exists() else {"variables": [], "keywords": [], "source": existing_page_resource[:12000]}
    ai_payload = {
        "workflow": clean_workflow_for_prompting(workflow),
        "approved_elements": approved_elements,
        "approved_keywords": approved_keywords,
        "approved_manual_tests": approved_manual_tests,
        "common_resource_context": common_resource_context,
        "generated_page_resource": resource_content,
        "existing_page_resource": existing_page_resource,
        "parsed_resource_context": resource_context_preview,
        "goal": "Review and refine the generated page resource so it stays fully aligned with the approved elements and approved keywords, preserves readable user-friendly keyword names when appropriate, uses only approved-element-backed variables and keywords, and removes anything not grounded in approved elements. Return only valid Robot Framework resource code."
    }
    alignment_prompt = (
        "You are AI Layer R0: a resource alignment reviewer for an AI-first automation framework.\n"
        "Return only Robot Framework resource code with no markdown fences.\n"
        "Use approved elements and approved keywords as the canonical source of truth.\n"
        "Preserve practical, user-friendly keyword naming where appropriate, such as 'Enter User Name' instead of mechanically verbose names, while keeping strong locator-variable alignment.\n"
        "Remove any variable or keyword not grounded in approved elements.\n\n"
        f"Input JSON:\n{json.dumps(ai_payload, indent=2)}"
    )
    aligned_resource_content = call_ai_with_workflow_session(
        workflow_name=page_name,
        stage="resource_alignment_review",
        endpoint=endpoint,
        token=token,
        prompt=alignment_prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )
    aligned_resource_content = normalize_resource_content(aligned_resource_content)
    if aligned_resource_content:
        resource_content = aligned_resource_content

    review_prompt = build_resource_review_prompt(
        workflow,
        approved_elements,
        approved_keywords,
        approved_manual_tests,
        common_resource_context,
        resource_content,
    )
    reviewed_resource_content = call_ai_with_workflow_session(
        workflow_name=page_name,
        stage="resource_review",
        endpoint=endpoint,
        token=token,
        prompt=review_prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )
    reviewed_resource_content = normalize_resource_content(reviewed_resource_content)
    if reviewed_resource_content:
        resource_content = reviewed_resource_content

    is_valid, validation_message = validate_resource_content(resource_content, common_resource_context)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    resource_path.write_text(resource_content, encoding="utf-8")

    refreshed_resource_context = parse_resource_file(resource_path)
    allowed_variable_names = {clean_text(str(item.get("approvedName", ""))).upper() for item in approved_elements if clean_text(str(item.get("approvedName", "")))}
    alignment_allowed_keywords: set[str] = set()

    try:
        alignment_prompt = build_resource_alignment_prompt(
            workflow,
            approved_elements,
            approved_keywords,
            refreshed_resource_context.get("keywords", []),
            refreshed_resource_context.get("variables", []),
        )
        alignment_response = call_ai_with_workflow_session(
            workflow_name=page_name,
            stage="resource_keyword_alignment",
            endpoint=endpoint,
            token=token,
            prompt=alignment_prompt,
            timeout_seconds=ai_cfg.get("timeout_seconds", 120),
            verify_ssl=ai_cfg.get("verify_ssl", False),
        )
        alignment_json = json.loads(strip_markdown_fences(alignment_response))
        if isinstance(alignment_json, dict):
            raw_allowed_variables = alignment_json.get("allowed_variables", [])
            raw_allowed_keywords = alignment_json.get("allowed_keywords", [])
            if isinstance(raw_allowed_variables, list):
                ai_allowed_variables = {
                    clean_text(str(item)).upper() for item in raw_allowed_variables if clean_text(str(item))
                }
                if ai_allowed_variables:
                    allowed_variable_names = allowed_variable_names.intersection(ai_allowed_variables) or allowed_variable_names
            if isinstance(raw_allowed_keywords, list):
                alignment_allowed_keywords = {
                    clean_text(str(item)).lower() for item in raw_allowed_keywords if clean_text(str(item))
                }
    except Exception:
        pass

    refreshed_keywords = []
    seen_keyword_names = set()
    for idx, resource_keyword in enumerate(refreshed_resource_context.get("keywords", []), start=1):
        resource_keyword_name = clean_text(str(resource_keyword.get("name", "")))
        if not resource_keyword_name:
            continue
        lowered_name = resource_keyword_name.lower()
        if alignment_allowed_keywords and lowered_name not in alignment_allowed_keywords:
            continue

        implementation_lines = [str(line).rstrip() for line in resource_keyword.get("body", []) if clean_text(str(line))]
        referenced_vars = {
            match.upper()
            for line in implementation_lines
            for match in re.findall(r"\$\{([A-Z0-9_]+)\}", line)
        }
        referenced_vars.update(arg.replace("${", "").replace("}", "").strip().upper() for arg in resource_keyword.get("args", []) if clean_text(str(arg)))
        referenced_vars.discard("")

        element_backed_reference = bool(referenced_vars.intersection(allowed_variable_names)) if referenced_vars else False
        verification_keyword = lowered_name.startswith("verify ")
        if not element_backed_reference and not verification_keyword:
            continue
        if lowered_name in seen_keyword_names:
            continue
        seen_keyword_names.add(lowered_name)

        action = "generic"
        if lowered_name.startswith("click "):
            action = "click"
        elif lowered_name.startswith("enter ") or lowered_name.startswith("input "):
            action = "input"
        elif lowered_name.startswith("select "):
            action = "select"
        elif lowered_name.startswith("verify "):
            action = "verify"

        refreshed_keywords.append({
            "keywordId": f"KW_{idx:03d}",
            "keywordName": resource_keyword_name,
            "targetElement": "",
            "action": action,
            "arguments": [arg.replace("${", "").replace("}", "") for arg in resource_keyword.get("args", [])],
            "implementation": implementation_lines,
            "approved": True,
        })

    save_keywords_for_workflow(workflow, refreshed_keywords)

# -------------------------------------------------------------------
# Manual tests handling
# -------------------------------------------------------------------

def generate_manual_tests_for_workflow(workflow_name: str) -> dict:
    ensure_workflow_run(workflow_name)
    workflow_input = load_workflow_or_404(workflow_name)
    config = validate_manual_config(load_manual_config())
    ai_cfg = config["ai"]

    if not ai_cfg.get("enabled", False):
        raise HTTPException(status_code=400, detail="AI is disabled in configuration.")

    endpoint = ai_cfg.get("endpoint", "").strip()
    token = get_manual_ai_token(ai_cfg)
    if not endpoint or not token:
        raise HTTPException(status_code=400, detail="Manual test AI endpoint/token missing in configuration.")

    prompt = build_manual_prompt(workflow_input)
    generated = call_manual_ai_with_workflow_session(
        workflow_name=workflow_name,
        stage="manual_generation",
        endpoint=endpoint,
        token=token,
        prompt=prompt,
    )
    reviewed_manual = call_manual_ai_with_workflow_session(
        workflow_name=workflow_name,
        stage="manual_review",
        endpoint=endpoint,
        token=token,
        prompt=build_manual_review_prompt(generated),
    )
    final_json = normalize_manual_test(reviewed_manual or generated, workflow_input)
    is_valid, validation_message = validate_manual_content(final_json)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    write_json(MANUAL_DIR / f"{workflow_name}.json", final_json)
    return final_json

def extract_manual_test_cases(manual: dict) -> list[dict]:
    if not manual:
        return []

    candidates = []
    for key in ("manualTests", "testCases", "tests", "cases"):
        value = manual.get(key)
        if isinstance(value, list):
            candidates = value
            break

    normalized = []
    for idx, case in enumerate(candidates, start=1):
        if not isinstance(case, dict):
            continue

        preconditions = case.get("preconditions", [])
        if isinstance(preconditions, str):
            preconditions = [preconditions]

        steps = case.get("steps", [])
        if isinstance(steps, list):
            step_lines = []
            for step in steps:
                if isinstance(step, dict):
                    text = step.get("step") or step.get("action") or step.get("description") or ""
                    if text:
                        step_lines.append(str(text))
                else:
                    step_lines.append(str(step))
            steps = step_lines
        elif isinstance(steps, str):
            steps = [steps]
        else:
            steps = []

        expected_result = (
            case.get("expectedResult")
            or case.get("expected")
            or case.get("expectedOutcome")
            or ""
        )

        normalized.append({
            "id": case.get("id") or case.get("testCaseId") or f"TC_{idx:03d}",
            "title": case.get("title") or case.get("name") or f"Test Case {idx}",
            "type": case.get("type") or case.get("scenarioType") or "General",
            "priority": case.get("priority") or "Medium",
            "preconditions": preconditions,
            "steps": steps,
            "expectedResult": expected_result,
            "approved": True,
        })
    return normalized

def update_manual_with_ui_cases(original: dict, cases: list[dict]) -> dict:
    target_key = None
    for key in ("manualTests", "testCases", "tests", "cases"):
        if isinstance(original.get(key), list):
            target_key = key
            break

    if target_key is None:
        target_key = "manualTests"

    original[target_key] = [
        {
            "id": case["id"],
            "title": case["title"],
            "type": case["type"],
            "priority": case["priority"],
            "preconditions": case["preconditions"],
            "steps": case["steps"],
            "expectedResult": case["expectedResult"],
        }
        for case in cases
    ]
    return original

# -------------------------------------------------------------------
# Automation handling
# -------------------------------------------------------------------

def strip_markdown_fences(content: str) -> str:
    content = content.strip()

    fenced_pattern = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n(.*?)\n```$", re.DOTALL)
    match = fenced_pattern.match(content)
    if match:
        return match.group(1).strip()

    content = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n```$", "", content, flags=re.MULTILINE)
    return content.strip()

def normalize_robot_content_spacing(content: str) -> str:
    lines = content.splitlines()

    cleaned: list[str] = []
    blank_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line.rstrip())

    result: list[str] = []
    in_settings = False
    in_test_cases = False
    first_test_case_seen = False

    for line in cleaned:
        stripped = line.strip()
        lower = stripped.lower()

        if stripped.startswith("***"):
            while result and result[-1] == "":
                result.pop()
            if result:
                result.append("")
            result.append(stripped)
            in_settings = lower == "*** settings ***"
            in_test_cases = lower == "*** test cases ***"
            first_test_case_seen = False if in_test_cases else first_test_case_seen
            continue

        if in_settings and stripped == "":
            continue

        if in_test_cases:
            is_test_name = bool(stripped) and not line.startswith((" ", "\t"))
            if is_test_name:
                while result and result[-1] == "":
                    result.pop()
                if first_test_case_seen:
                    result.append("")
                result.append(stripped)
                first_test_case_seen = True
                continue

        if stripped == "":
            if result and result[-1] == "":
                continue
            result.append("")
            continue

        result.append(line.rstrip())

    normalized = "\n".join(result).strip() + "\n"
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"(?im)(\*\*\* test cases \*\*\*\n)(\n+)", r"\1\n", normalized)
    normalized = re.sub(r"(?m)^\*\*\* Variables \*\*\*\n(\$\{.*?\}\s{2,}.*\n)(\*\*\* Keywords \*\*\*)", r"*** Variables ***\n\1\n\2", normalized)
    return normalized

def normalize_robot_blank_and_space_arguments(content: str) -> str:
    lines = content.splitlines()
    normalized = []

    keyword_patterns = [
        r"^\s*Enter\s+.*",
        r"^\s*Input\s+.*",
        r"^\s*Type\s+.*"
    ]

    blank_case_patterns = [
        r"(\s{2,})''(\s*)$",
        r'(\s{2,})""(\s*)$',
        r"(\s{2,})blank(\s*)$",
        r"(\s{2,})none(\s*)$"
    ]

    space_case_patterns = [
        r"(\s{2,})space(\s*)$",
        r"(\s{2,})whitespace(\s*)$",
        r"(\s{2,})whitespace_only(\s*)$",
        r"(\s{2,})' '(\s*)$",
        r'(\s{2,})" "(\s*)$'
    ]

    for line in lines:
        line = line.replace("${Empty}", "${EMPTY}").replace("${Space}", "${SPACE}")

        if any(re.match(pattern, line) for pattern in keyword_patterns):
            if re.search(r"\s{2,}$", line):
                line = re.sub(r"\s{2,}$", "    ${EMPTY}", line)
            for pattern in blank_case_patterns:
                line = re.sub(pattern, r"\1${EMPTY}\2", line, flags=re.IGNORECASE)
            for pattern in space_case_patterns:
                line = re.sub(pattern, r"\1${SPACE}\2", line, flags=re.IGNORECASE)

        normalized.append(line)

    return "\n".join(normalized)

def apply_robot_test_naming_and_tags(content: str, workflow: dict | None, workflow_name: str) -> str:
    app_code = derive_app_code(workflow, workflow_name)
    feature_code = derive_feature_code(workflow, workflow_name)

    lines = content.splitlines()
    result: list[str] = []
    in_test_cases = False
    current_index = 0

    def build_codes(existing_name: str, sequence: int) -> tuple[str, str]:
        match = re.search(r"([A-Z]+)_TC_(\d+)", existing_name.upper())
        if match:
            number = int(match.group(2))
        else:
            match = re.search(r"(\d+)", existing_name)
            number = int(match.group(1)) if match else sequence
        nn = f"{number:02d}"
        testcase_id = f"{app_code}-{feature_code}{nn}"
        return testcase_id, testcase_id

    def detect_scenario_type(title: str, existing_tags: list[str]) -> str:
        for tag in existing_tags:
            normalized = clean_text(tag).lower()
            if normalized in {"positive", "negative", "edge"}:
                return normalized

        title_lower = clean_text(title).lower()
        if any(token in title_lower for token in ["invalid", "error", "fail", "reject", "required", "blank", "empty", "incorrect", "unauthorized", "denied"]):
            return "negative"
        if any(token in title_lower for token in ["edge", "boundary", "max", "min", "length", "whitespace", "spaces", "special character", "copy paste", "case sensitivity"]):
            return "edge"
        return "positive"

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        lower = stripped.lower()

        if stripped.startswith("***"):
            in_test_cases = lower == "*** test cases ***"
            result.append(stripped)
            i += 1
            continue

        if in_test_cases and stripped and not line.startswith((" ", "\t")):
            current_index += 1
            testcase_id, primary_tag = build_codes(stripped, current_index)
            title = stripped
            title = re.sub(r"^[A-Z]+_TC_\d+\s*", "", title)
            title = re.sub(r"^AUT-[A-Z0-9]+-[A-Z0-9]+\s*:\s*", "", title)
            title = re.sub(r"^AUT-[A-Z0-9]+\s*:\s*", "", title)
            title = re.sub(r"^[A-Z0-9]+-[A-Z0-9]+\s*:\s*", "", title)
            title = clean_text(title)

            existing_tags: list[str] = []
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("[Tags]"):
                existing_tags_line = lines[i + 1].strip()
                tag_tokens = re.split(r"\s{2,}|\t+", existing_tags_line)
                existing_tags = [t for t in tag_tokens[1:] if t.strip()]

            scenario_type = detect_scenario_type(title, existing_tags)
            result.append(f"AUT-{testcase_id}: {title}")
            result.append(f"    [Tags]    {primary_tag}    {scenario_type}")

            if existing_tags:
                i += 2
                continue

            i += 1
            continue

        result.append(line.rstrip())
        i += 1

    return "\n".join(result)


def normalize_robot_content(content: str, workflow: dict | None = None, workflow_name: str = "") -> str:
    content = strip_markdown_fences(content)
    content = normalize_robot_blank_and_space_arguments(content)
    content = normalize_robot_content_spacing(content)
    if workflow_name:
        content = apply_robot_test_naming_and_tags(content, workflow, workflow_name)
        content = normalize_robot_content_spacing(content)
    return content


def generate_automation_for_workflow(workflow_name: str) -> str:
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    if not manual_path.exists():
        raise HTTPException(status_code=404, detail=f"Manual tests not found for workflow: {workflow_name}")

    config = validate_robot_config(load_robot_ai_json(CONFIG_PATH))
    ai_cfg = config["ai"]
    if not ai_cfg.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI is disabled in configuration.")

    endpoint = ai_cfg.get("endpoint", "").strip()
    token = get_robot_ai_token(ai_cfg)
    if not endpoint or not token:
        raise HTTPException(status_code=400, detail="Automation AI endpoint/token missing in configuration.")

    manual_data = load_robot_ai_json(manual_path)
    resource_files = manual_data.get("resourceFiles", [])
    if not isinstance(resource_files, list) or not resource_files:
        raise HTTPException(status_code=400, detail="Manual tests do not contain valid resourceFiles.")

    pom_root = BASE_DIR / config["pom_output_dir"]
    resource_context = []
    for rel_path in resource_files:
        resource_path = pom_root / str(rel_path).replace("\\", "/")
        if not resource_path.exists():
            raise HTTPException(status_code=400, detail=f"Resource file not found: {resource_path}")
        resource_context.append(parse_resource_file(resource_path))

    resources_dir = BASE_DIR / "resources"
    if resources_dir.exists():
        for common_resource_path in sorted(resources_dir.glob("*.resource")):
            try:
                resource_context.append(parse_resource_file(common_resource_path))
            except Exception:
                continue

    prompt = build_robot_prompt(manual_data, resource_context)
    robot_content = call_ai_with_workflow_session(
        workflow_name=workflow_name,
        stage="robot_generation",
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )

    workflow = load_workflow_or_404(workflow_name)
    robot_content = normalize_robot_content(robot_content, workflow, workflow_name)

    review_prompt = build_review_prompt(manual_data, resource_context, robot_content)
    reviewed_robot_content = call_ai_with_workflow_session(
        workflow_name=workflow_name,
        stage="robot_review",
        endpoint=endpoint,
        token=token,
        prompt=review_prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )
    reviewed_robot_content = normalize_robot_content(reviewed_robot_content, workflow, workflow_name)
    if reviewed_robot_content:
        robot_content = reviewed_robot_content

    validation_review_prompt = build_validation_review_prompt(manual_data, resource_context, robot_content)
    validated_robot_content = call_ai_with_workflow_session(
        workflow_name=workflow_name,
        stage="robot_validation_review",
        endpoint=endpoint,
        token=token,
        prompt=validation_review_prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )
    validated_robot_content = normalize_robot_content(validated_robot_content, workflow, workflow_name)
    if validated_robot_content:
        robot_content = validated_robot_content

    is_valid, validation_message = validate_robot_content(robot_content, resource_files)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)

    target = TESTS_DIR / f"{workflow_name}_tests.robot"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(robot_content, encoding="utf-8")
    return robot_content

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/")
def home(request: Request):
    workflows = sorted([p.stem for p in WORKFLOW_DIR.glob("*.json") if not p.name.endswith(".status.json")])
    manuals = sorted([p.stem for p in MANUAL_DIR.glob("*.json")])
    tests = sorted([p.name for p in TESTS_DIR.glob("*.robot")])

    workflow_rows = []
    for workflow_name in workflows:
        workflow_rows.append({
            "name": workflow_name,
            "status": get_workflow_status(workflow_name)
        })

    return render_template(request, "index.html", {
        "workflow_rows": workflow_rows,
        "manuals": manuals,
        "tests": tests,
    })

@app.get("/workflow/new")
def workflow_form(request: Request):
    existing = WORKFLOW_DIR / "login.json"
    data = read_json(existing) if existing.exists() else {}
    return render_template(request, "workflow_form.html", {
        "data": data,
        "edit_mode": False,
        "workflow_slug": ""
    })

@app.get("/workflow/edit/{workflow_name}")
def edit_workflow(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    return render_template(request, "workflow_form.html", {
        "data": workflow,
        "edit_mode": True,
        "workflow_slug": workflow_name
    })

@app.post("/workflow/save")
def save_workflow(
    workflow_name: str = Form(...),
    module: str = Form("Authentication"),
    feature: str = Form("Login"),
    page_name: str = Form(...),
    page_url: str = Form(...),
    resource_file: str = Form(...),
    preconditions_text: str = Form(""),
    steps_text: str = Form(""),
    expected_result: str = Form(""),
    fields_text: str = Form(""),
    validations_text: str = Form(""),
    scenario_intent_text: str = Form("positive,negative,edge,ui"),
    valid_username: str = Form(""),
    valid_password: str = Form(""),
    existing_workflow_slug: str = Form(""),
):
    payload = clean_workflow_for_prompting(build_workflow_payload(
        workflow_name,
        module,
        feature,
        page_name,
        page_url,
        resource_file,
        preconditions_text,
        steps_text,
        expected_result,
        fields_text,
        validations_text,
        scenario_intent_text,
        valid_username,
        valid_password,
        str(CONFIG.get("application_code", "")),
    ))

    target_slug = existing_workflow_slug.strip() or slugify(workflow_name)
    target = WORKFLOW_DIR / f"{target_slug}.json"
    write_json(target, payload)

    return RedirectResponse(url=f"/page-review/{target_slug}", status_code=303)

@app.get("/page-review/{workflow_name}")
def page_review(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    review_data = get_page_review_data(workflow)
    return render_template(request, "page_review.html", {
        "workflow_name": workflow_name,
        "workflow": workflow,
        "page_name": review_data["page_name"],
        "page_url": review_data["page_url"],
        "elements": review_data["elements"],
        "screenshot_web_path": review_data["screenshot_web_path"],
        "raw_elements_count": review_data["raw_elements_count"],
    })

@app.post("/page-review/{workflow_name}/extract")
def run_page_review_extraction(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    review_data = get_page_review_data(workflow)
    try:
        run_page_extraction(review_data["page_name"], review_data["page_url"])
        updated_review_data = get_page_review_data(workflow)
        return render_template(request, "page_review.html", {
            "workflow_name": workflow_name,
            "workflow": workflow,
            "page_name": updated_review_data["page_name"],
            "page_url": updated_review_data["page_url"],
            "elements": updated_review_data["elements"],
            "screenshot_web_path": updated_review_data["screenshot_web_path"],
            "raw_elements_count": updated_review_data["raw_elements_count"],
            "success_message": "Page extraction completed successfully. Review the extracted elements below.",
        })
    except Exception as exc:
        updated_review_data = get_page_review_data(workflow)
        return render_template(request, "page_review.html", {
            "workflow_name": workflow_name,
            "workflow": workflow,
            "page_name": updated_review_data["page_name"],
            "page_url": updated_review_data["page_url"],
            "elements": updated_review_data["elements"],
            "screenshot_web_path": updated_review_data["screenshot_web_path"],
            "raw_elements_count": updated_review_data["raw_elements_count"],
            "error_message": f"Page extraction failed: {str(exc)}",
        }, status_code=400)

@app.post("/page-review/{workflow_name}/save")
async def save_page_review(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    review_data = get_page_review_data(workflow)
    form = await request.form()

    count = int(form.get("element_count", "0"))
    manual_count = int(form.get("manual_count", "0"))

    approved_elements = []

    for i in range(count):
        approved = form.get(f"element_{i}_approved") == "on"
        if not approved:
            continue

        approved_name = str(form.get(f"element_{i}_approved_name", "")).strip()
        element_type = str(form.get(f"element_{i}_type", "")).strip()
        locator = str(form.get(f"element_{i}_locator", "")).strip()

        if approved_name and locator:
            approved_elements.append({
                "approvedName": approved_name,
                "type": element_type,
                "locator": locator,
                "approved": True,
            })

    for i in range(manual_count):
        approved = form.get(f"manual_{i}_approved") == "on"
        if not approved:
            continue

        approved_name = str(form.get(f"manual_{i}_approved_name", "")).strip()
        element_type = str(form.get(f"manual_{i}_type", "")).strip()
        locator = str(form.get(f"manual_{i}_locator", "")).strip()

        if approved_name and locator:
            approved_elements.append({
                "approvedName": approved_name,
                "type": element_type,
                "locator": locator,
                "approved": True,
            })

    payload = {
        "pageName": review_data["page_name"],
        "pageUrl": review_data["page_url"],
        "rawElements": review_data.get("raw_elements", []),
        "elements": approved_elements,
    }
    write_json(review_data["elements_path"], payload)

    return RedirectResponse(url=f"/keywords/{workflow_name}", status_code=HTTP_303_SEE_OTHER)

@app.get("/keywords/{workflow_name}")
def keyword_review(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    keyword_data = get_keyword_review_data(workflow)
    return render_template(request, "keyword_review.html", {
        "workflow_name": workflow_name,
        "page_name": keyword_data["page_name"],
        "keywords": keyword_data["keywords"],
    })

@app.post("/keywords/{workflow_name}/save")
async def save_keyword_review(request: Request, workflow_name: str):
    workflow = load_workflow_or_404(workflow_name)
    form = await request.form()
    count = int(form.get("keyword_count", "0"))
    approved_keywords = []

    for i in range(count):
        approved = form.get(f"keyword_{i}_approved") == "on"
        if not approved:
            continue

        implementation_text = str(form.get(f"keyword_{i}_implementation", "")).strip()
        implementation_lines = [line.rstrip() for line in implementation_text.splitlines() if line.strip()]
        arguments_text = str(form.get(f"keyword_{i}_arguments", "")).strip()
        arguments = [arg.strip() for arg in arguments_text.split(",") if arg.strip()]

        approved_keywords.append({
            "keywordId": str(form.get(f"keyword_{i}_id", "")).strip() or f"KW_{i+1:03d}",
            "keywordName": str(form.get(f"keyword_{i}_name", "")).strip(),
            "targetElement": str(form.get(f"keyword_{i}_target", "")).strip(),
            "action": str(form.get(f"keyword_{i}_action", "")).strip(),
            "arguments": arguments,
            "implementation": implementation_lines,
            "approved": True,
        })

    save_keywords_for_workflow(workflow, approved_keywords)
    generate_resource_for_workflow(workflow, approved_keywords)

    return RedirectResponse(url=f"/manual-tests/{workflow_name}", status_code=HTTP_303_SEE_OTHER)

@app.get("/manual-tests/{workflow_name}")
def manual_tests_page(request: Request, workflow_name: str):
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    workflow = read_json(workflow_path) if workflow_path.exists() else None
    manual = read_json(manual_path) if manual_path.exists() else None
    test_cases = extract_manual_test_cases(manual) if manual else []

    return render_template(request, "manual_tests.html", {
        "workflow_name": workflow_name,
        "workflow": workflow,
        "manual": manual,
        "test_cases": test_cases,
    })

@app.post("/manual-tests/{workflow_name}/generate")
def generate_manual_tests_route(request: Request, workflow_name: str):
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    workflow = read_json(workflow_path) if workflow_path.exists() else None
    begin_workflow_run(workflow_name)
    try:
        generated = generate_manual_tests_for_workflow(workflow_name)
        test_cases = extract_manual_test_cases(generated)
        return render_template(request, "manual_tests.html", {
            "workflow_name": workflow_name,
            "workflow": workflow,
            "manual": generated,
            "test_cases": test_cases,
            "success_message": "Manual tests generated successfully. Review and approve the relevant tests.",
        })
    except Exception as exc:
        existing_manual = read_json(manual_path) if manual_path.exists() else None
        return render_template(request, "manual_tests.html", {
            "workflow_name": workflow_name,
            "workflow": workflow,
            "manual": existing_manual,
            "test_cases": extract_manual_test_cases(existing_manual) if existing_manual else [],
            "error_message": f"Manual test generation failed: {str(exc)}",
        }, status_code=400)

@app.post("/manual-tests/{workflow_name}/save")
async def save_manual_tests(request: Request, workflow_name: str):
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    workflow = read_json(workflow_path) if workflow_path.exists() else None
    manual_path = MANUAL_DIR / f"{workflow_name}.json"

    try:
        form = await request.form()

        original = read_json(manual_path) if manual_path.exists() else {
            "workflowName": workflow_name,
            "resourceFiles": workflow.get("resourceFiles", []) if workflow else [],
            "manualTests": [],
        }

        count = int(form.get("case_count", "0"))
        cases = []

        for i in range(count):
            approved = form.get(f"case_{i}_approved") == "on"
            if not approved:
                continue

            case_id = str(form.get(f"case_{i}_id", "")).strip()
            title = str(form.get(f"case_{i}_title", "")).strip()
            case_type = str(form.get(f"case_{i}_type", "General")).strip()
            priority = str(form.get(f"case_{i}_priority", "Medium")).strip()
            preconditions_text = str(form.get(f"case_{i}_preconditions", "")).strip()
            steps_text = str(form.get(f"case_{i}_steps", "")).strip()
            expected_result = str(form.get(f"case_{i}_expected", "")).strip()

            preconditions = [line.strip().removeprefix("- ").strip() for line in preconditions_text.splitlines() if line.strip()]
            steps = []
            for line in steps_text.splitlines():
                value = line.strip()
                if not value:
                    continue
                value = re.sub(r"^\d+\.\s*", "", value)
                steps.append(value)

            cases.append({
                "id": case_id or f"TC_{i+1:03d}",
                "title": title or f"Test Case {i+1}",
                "type": case_type.title() or "General",
                "priority": priority or "Medium",
                "preconditions": preconditions,
                "steps": steps,
                "expectedResult": expected_result,
            })

        if not cases:
            existing_manual = read_json(manual_path) if manual_path.exists() else None
            return render_template(request, "manual_tests.html", {
                "workflow_name": workflow_name,
                "workflow": workflow,
                "manual": existing_manual,
                "test_cases": extract_manual_test_cases(existing_manual) if existing_manual else [],
                "error_message": "Please select at least one test case to approve.",
            }, status_code=400)

        updated = update_manual_with_ui_cases(original, cases)
        write_json(manual_path, updated)
        export_manual_tests_to_excel(workflow_name, workflow, updated)

        try:
            if workflow:
                approved_keywords = get_keyword_review_data(workflow).get("keywords", [])
                generate_resource_for_workflow(workflow, approved_keywords)
        except Exception:
            pass

        return RedirectResponse(url=f"/automation/{workflow_name}", status_code=HTTP_303_SEE_OTHER)

    except Exception as exc:
        existing_manual = read_json(manual_path) if manual_path.exists() else None
        return render_template(request, "manual_tests.html", {
            "workflow_name": workflow_name,
            "workflow": workflow,
            "manual": existing_manual,
            "test_cases": extract_manual_test_cases(existing_manual) if existing_manual else [],
            "error_message": f"Failed to approve manual tests: {str(exc)}",
        }, status_code=400)

@app.get("/automation/{workflow_name}")
def automation_page(request: Request, workflow_name: str):
    robot_path = TESTS_DIR / f"{workflow_name}_tests.robot"
    robot_content = read_text(robot_path)
    return render_template(request, "automation.html", {
        "workflow_name": workflow_name,
        "robot_content": robot_content,
    })

@app.post("/automation/{workflow_name}/generate")
def generate_automation_route(request: Request, workflow_name: str):
    existing_content = read_text(TESTS_DIR / f"{workflow_name}_tests.robot")
    ensure_workflow_run(workflow_name)
    try:
        robot_content = generate_automation_for_workflow(workflow_name)
        return render_template(request, "automation.html", {
            "workflow_name": workflow_name,
            "robot_content": robot_content,
            "success_message": "Automation script generated successfully. Review and save the approved version.",
        })
    except Exception as exc:
        return render_template(request, "automation.html", {
            "workflow_name": workflow_name,
            "robot_content": existing_content,
            "error_message": f"Automation generation failed: {str(exc)}",
        }, status_code=400)

@app.post("/automation/{workflow_name}/save")
def save_automation(request: Request, workflow_name: str, robot_content: str = Form(...)):
    try:
        target = TESTS_DIR / f"{workflow_name}_tests.robot"
        target.parent.mkdir(parents=True, exist_ok=True)
        workflow = read_json(WORKFLOW_DIR / f"{workflow_name}.json") if (WORKFLOW_DIR / f"{workflow_name}.json").exists() else None
        robot_content = normalize_robot_content(robot_content, workflow, workflow_name)
        target.write_text(robot_content, encoding="utf-8")
        return render_template(request, "automation.html", {
            "workflow_name": workflow_name,
            "robot_content": robot_content,
            "success_message": "Automation script saved successfully.",
        })
    except Exception as exc:
        return render_template(request, "automation.html", {
            "workflow_name": workflow_name,
            "robot_content": robot_content,
            "error_message": f"Failed to save automation script: {str(exc)}",
        }, status_code=400)

@app.get("/static-artifacts/{page_name}/{file_name}")
def static_artifact(page_name: str, file_name: str):
    from fastapi.responses import FileResponse
    target = POM_DIR / page_name / file_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)