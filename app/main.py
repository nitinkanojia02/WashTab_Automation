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
    call_ai_chat,
    get_ai_token as get_robot_ai_token,
    load_json as load_robot_json,
    parse_resource_file,
    validate_config as validate_robot_config,
    validate_robot_content,
)

BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = BASE_DIR / "workflow_inputs"
MANUAL_DIR = BASE_DIR / "manual_tests"
TESTS_DIR = BASE_DIR / "tests"
POM_DIR = BASE_DIR / "pom_pages"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

app = FastAPI(title="WashTab Automation MVP")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    payload = {"success_message": None, "error_message": None}
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

def slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "workflow"

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())

def title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in re.split(r"[_\-\s]+", clean_text(value)) if word)

def to_keyword_title(element_name: str) -> str:
    base = clean_text(element_name).replace("_", " ")
    return " ".join(word.capitalize() for word in base.split())

def load_workflow_or_404(workflow_name: str) -> dict:
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_name}")
    return read_json(workflow_path)

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

def generate_automation_for_workflow(workflow_name: str) -> str:
    manual_path = MANUAL_DIR / f"{workflow_name}.json"
    if not manual_path.exists():
        raise HTTPException(status_code=404, detail=f"Manual tests not found for workflow: {workflow_name}")

    config = validate_robot_config(load_robot_json(Path("config/page_model_config.json")))
    ai_cfg = config["ai"]
    if not ai_cfg.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI is disabled in configuration.")

    endpoint = ai_cfg.get("endpoint", "").strip()
    token = get_robot_ai_token(ai_cfg)
    if not endpoint or not token:
        raise HTTPException(status_code=400, detail="Automation AI endpoint/token missing in configuration.")

    manual_data = load_robot_json(manual_path)
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

    prompt = build_robot_prompt(manual_data, resource_context)
    robot_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai_cfg.get("timeout_seconds", 120),
        verify_ssl=ai_cfg.get("verify_ssl", False),
    )

    errors = validate_robot_content(robot_content, resource_files)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    target = TESTS_DIR / f"{workflow_name}_tests.robot"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(robot_content, encoding="utf-8")
    return robot_content

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
        "testDataRefs": {},
        "scenarioIntent": scenario_intent,
    }

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
    approved_path = page_dir / f"{page_name}.approved.json"

    raw_elements = []
    if elements_path.exists():
        try:
            data = read_json(elements_path)
            if isinstance(data, list):
                raw_elements = data
            elif isinstance(data, dict):
                raw_elements = data.get("elements", [])
        except Exception:
            raw_elements = []

    normalized_elements = []
    for idx, item in enumerate(raw_elements):
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

    approved_elements = []
    if approved_path.exists():
        try:
            approved_data = read_json(approved_path)
            approved_elements = approved_data.get("elements", [])
        except Exception:
            approved_elements = []

    return {
        "page_name": page_name,
        "page_url": page_url,
        "elements": approved_elements if approved_elements else normalized_elements,
        "screenshot_web_path": screenshot_web_path,
        "raw_elements_count": len(normalized_elements),
        "approved_path": approved_path,
    }

def get_keywords_path(page_name: str) -> Path:
    return POM_DIR / page_name / f"{page_name}.keywords.json"

def load_approved_elements_for_workflow(workflow: dict) -> list[dict]:
    review_data = get_page_review_data(workflow)
    approved_path = review_data["approved_path"]
    if not approved_path.exists():
        return []
    approved_data = read_json(approved_path)
    return approved_data.get("elements", [])

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
                f"Wait Until Element Is Visible    ${{{element_name.upper()}}}    10s",
                f"Input Text    ${{{element_name.upper()}}}    ${{text}}"
            ]
            arguments = ["text"]
            action = "input"

        elif element_type == "button":
            keyword_name = f"Click {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{element_name.upper()}}}    10s",
                f"Click Element    ${{{element_name.upper()}}}"
            ]
            arguments = []
            action = "click"

        elif element_type == "dropdown":
            keyword_name = f"Select {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{element_name.upper()}}}    10s",
                f"Select From List By Label    ${{{element_name.upper()}}}    ${{value}}"
            ]
            arguments = ["value"]
            action = "select"

        elif element_type == "link":
            keyword_name = f"Click {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{element_name.upper()}}}    10s",
                f"Click Element    ${{{element_name.upper()}}}"
            ]
            arguments = []
            action = "click"

        else:
            keyword_name = f"Use {keyword_title}"
            implementation = [
                f"Wait Until Element Is Visible    ${{{element_name.upper()}}}    10s",
                f"Click Element    ${{{element_name.upper()}}}"
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

def get_workflow_status(workflow_name: str) -> dict:
    workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
    workflow = read_json(workflow_path) if workflow_path.exists() else {}
    pages = workflow.get("pages", [])
    page_name = pages[0].get("name") if pages else ""

    page_reviewed = False
    keywords_reviewed = False

    if page_name:
        approved_page_path = POM_DIR / page_name / f"{page_name}.approved.json"
        page_reviewed = approved_page_path.exists()

        keywords_path = POM_DIR / page_name / f"{page_name}.keywords.json"
        keywords_reviewed = keywords_path.exists()

    manual_approved = (MANUAL_DIR / f"{workflow_name}.json").exists()
    automation_generated = (TESTS_DIR / f"{workflow_name}_tests.robot").exists()

    return {
        "page_reviewed": page_reviewed,
        "keywords_reviewed": keywords_reviewed,
        "manual_approved": manual_approved,
        "automation_generated": automation_generated,
    }

@app.get("/")
def home(request: Request):
    workflows = sorted([p.stem for p in WORKFLOW_DIR.glob("*.json")])
    manuals = sorted([p.stem for p in MANUAL_DIR.glob("*.json")])
    tests = sorted([p.name for p in TESTS_DIR.glob("*.robot")])

    workflow_rows = []
    for workflow_name in workflows:
        workflow_rows.append({
            "name": workflow_name,
            "status": get_workflow_status(workflow_name)
        })

    return render_template(request, "index.html", {
        "workflows": workflows,
        "workflow_rows": workflow_rows,
        "manuals": manuals,
        "tests": tests,
    })

@app.get("/workflow/new")
def workflow_form(request: Request):
    existing = WORKFLOW_DIR / "login.json"
    data = read_json(existing) if existing.exists() else {}
    return render_template(request, "workflow_form.html", {"data": data})

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
    )
    target = WORKFLOW_DIR / f"{slugify(workflow_name)}.json"
    write_json(target, payload)
    return RedirectResponse(url=f"/page-review/{target.stem}", status_code=303)

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
    write_json(review_data["approved_path"], payload)

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