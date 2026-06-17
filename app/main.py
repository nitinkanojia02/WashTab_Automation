from pathlib import Path
import json
import re
import subprocess
import sys

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
    build_prompt as build_robot_prompt,
    build_review_prompt,
    call_ai_chat,
    get_ai_token as get_robot_ai_token,
    load_json as load_robot_ai_json,
    parse_resource_file,
    validate_config as validate_robot_config,
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

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def get_workflow_status(workflow_name: str) -> str:
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    robot_path = TESTS_DIR / f"{workflow_name}_tests.robot"

    if robot_path.exists():
        return "automation_generated"
    if manual_path.exists():
        return "manual_tests_generated"
    if workflow_path.exists():
        return "workflow_saved"
    return "not_started"

def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "workflow"

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())

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
        fields.append({
            "name": parts[0] if len(parts) > 0 else "",
            "label": parts[1] if len(parts) > 1 else parts[0] if parts else "",
            "type": parts[2] if len(parts) > 2 else "textbox",
            "required": (parts[3].lower() == "true") if len(parts) > 3 else False,
        })

    return {
        "inputType": "exploratory_workflow",
        "workflowId": f"{slugify(workflow_name).upper()}_001",
        "workflowName": workflow_name,
        "module": module,
        "feature": feature,
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

    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "Unknown extraction error."
        raise HTTPException(status_code=500, detail=f"Page extraction failed: {error_message}")

    return result.stdout.strip()

def infer_type_from_raw_item(item: dict) -> str:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}
    input_type = clean_text(attrs.get("type", "")).lower()

    if tag in {"button", "ion-button"}:
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

def infer_name_from_raw_item(item: dict, index: int) -> str:
    role = infer_type_from_raw_item(item)
    label = infer_label_from_raw_item(item)

    if label:
        base = slugify(label)
    else:
        base = f"element_{index+1}"

    if role == "textbox":
        return f"{base}_textbox"
    if role == "password_textbox":
        return f"{base}_textbox"
    if role == "button":
        return f"{base}_button"
    if role == "dropdown":
        return f"{base}_dropdown"
    if role == "link":
        return f"{base}_link"
    return base

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
    if placeholder and tag in {"input", "textarea"}:
        return f"xpath=//{tag}[@placeholder={xpath_literal(placeholder)}]"
    if name and tag in {"input", "textarea", "select"}:
        return f"xpath=//{tag}[@name={xpath_literal(name)}]"
    if aria:
        return f"xpath=//{tag}[@aria-label={xpath_literal(aria)}]"
    if text and tag in {"button", "a", "ion-button"}:
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

    page_dir = POM_DIR / page_name
    elements_path = page_dir / f"{page_name}.elements.json"
    screenshot_path = page_dir / f"{page_name}.png"

    elements_data = []
    if elements_path.exists():
        try:
            data = read_json(elements_path)
            if isinstance(data, list):
                elements_data = data
            elif isinstance(data, dict):
                elements_data = data.get("elements", [])
        except Exception:
            elements_data = []

    normalized_elements = []
    for idx, item in enumerate(elements_data):
        if not isinstance(item, dict):
            continue
        if "approvedName" in item and "locator" in item and "type" in item:
            normalized_elements.append({
                "approvedName": item.get("approvedName") or f"element_{idx+1}",
                "type": item.get("type", "element"),
                "locator": item.get("locator", ""),
                "approved": item.get("approved", True),
            })
        else:
            normalized_elements.append(normalize_extracted_element(item, idx))

    screenshot_web_path = None
    if screenshot_path.exists():
        screenshot_web_path = f"/static-artifacts/{page_name}/{page_name}.png"

    return {
        "page_name": page_name,
        "page_url": page_url,
        "elements": normalized_elements,
        "screenshot_web_path": screenshot_web_path,
        "raw_elements_count": len(normalized_elements),
        "elements_path": elements_path,
    }

# -------------------------------------------------------------------
# Keyword handling
# -------------------------------------------------------------------

def get_keywords_path(page_name: str) -> Path:
    return POM_DIR / page_name / f"{page_name}.keywords.json"

def get_resource_path(page_name: str) -> Path:
    return POM_DIR / page_name / f"{page_name}.resource"

def load_approved_elements_for_workflow(workflow: dict) -> list[dict]:
    review_data = get_page_review_data(workflow)
    elements_path = review_data["elements_path"]
    if not elements_path.exists():
        return []
    data = read_json(elements_path)
    if isinstance(data, dict):
        return data.get("elements", [])
    if isinstance(data, list):
        return data
    return []

def build_keywords_from_elements(elements: list[dict]) -> list[dict]:
    keywords = []
    for idx, element in enumerate(elements, start=1):
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

    keywords = []
    if keywords_path.exists():
        try:
            payload = read_json(keywords_path)
            keywords = payload.get("keywords", [])
        except Exception:
            keywords = []

    if not keywords:
        approved_elements = load_approved_elements_for_workflow(workflow)
        keywords = build_keywords_from_elements(approved_elements)

    return {
        "page_name": page_name,
        "keywords_path": keywords_path,
        "keywords": keywords,
    }

def save_keywords_for_workflow(workflow: dict, keywords: list[dict]):
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else "page"
    payload = {
        "pageName": page_name,
        "keywords": keywords,
    }
    write_json(get_keywords_path(page_name), payload)

# -------------------------------------------------------------------
# AI-driven resource generation
# -------------------------------------------------------------------

def build_resource_generation_prompt(
    workflow: dict,
    approved_elements: list[dict],
    approved_keywords: list[dict],
    approved_manual_tests: list[dict] | None = None,
    common_resource_context: list[dict] | None = None,
) -> str:
    payload = {
        "workflow": workflow,
        "approved_elements": approved_elements,
        "approved_keywords": approved_keywords,
        "approved_manual_tests": approved_manual_tests or [],
        "common_resource_context": common_resource_context or [],
    }

    return (
        "You are an expert Robot Framework resource-file designer working on a maintainable enterprise UI automation framework.\n"
        "Generate exactly one valid page-specific Robot Framework .resource file.\n\n"
        "Primary objective:\n"
        "- Build a reusable page resource file that contains only page-specific locators, page-specific action keywords, page-specific validation keywords, and page-specific test-data variables inferred from approved workflow and approved manual tests.\n"
        "- You are also given common/shared resource context. Reuse that knowledge and avoid duplicating common keywords, browser lifecycle keywords, and generic variables already suitable for shared resources.\n\n"
        "Mandatory output rules:\n"
        "- Return only Robot Framework resource code.\n"
        "- Do not include markdown fences.\n"
        "- Include only these sections if needed: *** Settings ***, *** Variables ***, *** Keywords ***.\n"
        "- Use SeleniumLibrary in Settings only if truly needed in this page resource.\n"
        "- Use the approved elements to create locator variables.\n"
        "- Use the approved keywords as the foundation for reusable keyword implementations.\n"
        "- Create reusable test-data variables based on approved manual tests, not just workflow.testData.\n"
        "- If approved manual tests imply data such as invalid username, invalid password, blank username, blank password, whitespace-only username, whitespace-only password, long username, long password, special-character inputs, or boundary-value inputs, define them as page-resource variables when useful for this page.\n"
        "- Valid business data should come from workflow.testData if present.\n"
        "- Invalid, edge, or long input variables should be created in the page resource file whenever the approved manual tests suggest they are relevant.\n"
        "- Do NOT define Robot Framework built-in variables like ${EMPTY}, ${SPACE}, ${True}, ${False}, or ${None}; reference them directly only where needed.\n"
        "- Keep naming clean and maintainable.\n"
        "- Prefer clear reusable variable names such as ${VALID_USERNAME}, ${INVALID_USERNAME}, ${BLANK_USERNAME}, ${SPACE_USERNAME}, ${LONG_USERNAME}, and similar names for passwords or other fields where justified by approved manual tests.\n"
        "- Prefer reusable validation keywords when expected results mention UI messages, masking, redirection, visibility, enabled/disabled state, or validation behavior.\n"
        "- Do not invent unnecessary variables or keywords.\n"
        "- Preserve a clean resource file structure with minimal blank lines: at most one blank line between variables and at most one blank line between keyword blocks.\n"
        "- Use modern Robot Framework syntax only. Do NOT use deprecated loop syntax such as ': FOR' or backslash-prefixed loop bodies. Use 'FOR ... END' syntax if a loop is truly necessary.\n"
        "- Use AI intelligence instead of hardcoded assumptions.\n\n"
        "Shared-vs-page resource rules:\n"
        "- Generic or common variables belong in resources/common_keywords.resource, not in the page resource. Examples include browser selection such as ${BROWSER}, generic timeout variables, generic environment/base-url variables, and other cross-page defaults.\n"
        "- Generic or common keywords belong in resources/common_keywords.resource, not in the page resource. Examples include Open Browser To Url, Go To Url, Open Login Page, Open Browser Session, Close Browser Session, Wait For Element To Be Ready, generic click/input wrappers, and other cross-page/browser lifecycle helpers.\n"
        "- If a common/shared keyword already exists or is strongly implied by common_resource_context, do not recreate it in the page resource. Instead, design the page resource to rely on the shared/common resource layer.\n"
        "- The page resource should contain only page-specific behavior such as entering credentials, clicking page-specific buttons, and validating page-specific messages or field behavior.\n"
        "- Do not duplicate keywords that already exist in common/shared resources.\n\n"
        "Resource quality requirements:\n"
        "- The Variables section should centralize reusable page-level test data so generated .robot test suites do not hardcode those values.\n"
        "- The Keywords section should contain reusable business-friendly page actions and validations rather than low-level one-off steps only.\n"
        "- If approved manual tests mention password masking, create a reusable page-specific keyword to verify password masking behavior if feasible in the framework.\n"
        "- If approved manual tests mention validation messages or rejection behavior, create reusable page-specific validation/assertion keywords where feasible.\n"
        "- Do not create generic browser open/close keywords here if those belong in common/shared resources.\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )

def normalize_resource_content(content: str) -> str:
    content = strip_markdown_fences(content)
    lines = content.splitlines()

    cleaned: list[str] = []
    blank_count = 0
    for line in lines:
        normalized_line = line.rstrip()
        if normalized_line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(normalized_line)

    content = "\n".join(cleaned).strip() + "\n"
    content = re.sub(r"(?m)^\s*: FOR\b", "FOR", content)
    content = re.sub(r"(?m)^\s*\\\s+", "    ", content)
    return content


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

    prompt = build_resource_generation_prompt(
        workflow,
        approved_elements,
        approved_keywords,
        approved_manual_tests,
        common_resource_context,
    )
    resource_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )

    resource_content = normalize_resource_content(resource_content)

    resource_path = get_resource_path(page_name)
    is_valid, validation_message = validate_resource_content(resource_content, common_resource_context)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    resource_path.write_text(resource_content, encoding="utf-8")

# -------------------------------------------------------------------
# Manual tests handling
# -------------------------------------------------------------------

def generate_manual_tests_for_workflow(workflow_name: str) -> dict:
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
    generated = call_devex_ai(endpoint=endpoint, token=token, prompt=prompt)
    final_json = normalize_manual_test(generated, workflow_input)
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

    cleaned = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line.rstrip())

    section_indices = [i for i, line in enumerate(cleaned) if line.strip().startswith("*** ")]
    result = []
    for idx, line in enumerate(cleaned):
        if idx in section_indices and result:
            if result[-1] != "":
                result.append("")
        result.append(line)

    return "\n".join(result).strip() + "\n"

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

def normalize_robot_content(content: str) -> str:
    content = strip_markdown_fences(content)
    content = normalize_robot_blank_and_space_arguments(content)
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
    robot_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )

    robot_content = normalize_robot_content(robot_content)

    review_prompt = build_review_prompt(manual_data, resource_context, robot_content)
    reviewed_robot_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=review_prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )
    reviewed_robot_content = normalize_robot_content(reviewed_robot_content)
    if reviewed_robot_content:
        robot_content = reviewed_robot_content

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
    payload = build_workflow_payload(
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
    )

    target_slug = existing_workflow_slug.strip() or slugify(workflow_name)
    target = WORKFLOW_DIR / f"{target_slug}.json"
    write_json(target, payload)

    if not existing_workflow_slug.strip():
        update_workflow_status(
            target_slug,
            page_reviewed=False,
            keywords_reviewed=False,
            manual_approved=False,
            automation_generated=False
        )

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
        "elements": approved_elements,
    }
    write_json(review_data["elements_path"], payload)

    update_workflow_status(workflow_name, page_reviewed=True)

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

    update_workflow_status(workflow_name, keywords_reviewed=True)

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

        try:
            if workflow:
                approved_keywords = get_keyword_review_data(workflow).get("keywords", [])
                generate_resource_for_workflow(workflow, approved_keywords)
        except Exception:
            pass

        update_workflow_status(workflow_name, manual_approved=True)
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
    try:
        robot_content = generate_automation_for_workflow(workflow_name)
        update_workflow_status(workflow_name, automation_generated=True)
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
        robot_content = normalize_robot_content(robot_content)
        target.write_text(robot_content, encoding="utf-8")
        update_workflow_status(workflow_name, automation_generated=True)
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