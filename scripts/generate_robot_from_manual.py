import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "page_model_config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("generate_robot_from_manual")

def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def slugify(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "module"


def compact_code(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", clean_text(text)).upper()

def get_ai_token(ai_cfg: dict) -> str:
    token = str(ai_cfg.get("token", "")).strip()
    if token:
        return token

    token_env_var = str(ai_cfg.get("token_env_var", "")).strip()
    if token_env_var:
        return os.getenv(token_env_var, "").strip()

    return ""

def validate_config(config: dict) -> dict:
    config["pom_output_dir"] = str(config.get("pom_output_dir", "pom_pages"))
    config["manual_tests_output_dir"] = str(config.get("manual_tests_output_dir", "manual_tests"))
    config["robot_tests_output_dir"] = str(config.get("robot_tests_output_dir", "tests"))

    if "generation_control" not in config:
        config["generation_control"] = {}

    gc = config["generation_control"]
    gc["overwrite_robot_tests"] = bool(gc.get("overwrite_robot_tests", False))
    gc["excluded_modules"] = [slugify(x) for x in gc.get("excluded_modules", []) if str(x).strip()]
    gc["excluded_manual_files"] = [str(x).strip().lower() for x in gc.get("excluded_manual_files", []) if str(x).strip()]

    if "ai" not in config:
        config["ai"] = {}

    ai = config["ai"]
    ai["enabled"] = bool(ai.get("enabled", True))
    ai["endpoint"] = str(ai.get("endpoint", "")).strip()
    ai["temperature"] = float(ai.get("temperature", 0.2))
    ai["timeout_seconds"] = int(ai.get("timeout_seconds", 120))
    ai["verify_ssl"] = bool(ai.get("verify_ssl", False))

    return config

def extract_keywords_from_resource(resource_text: str) -> List[Dict]:
    lines = resource_text.splitlines()
    in_keywords = False
    keywords = []
    current = None

    for line in lines:
        stripped = line.strip()

        if stripped.lower() == "*** keywords ***":
            in_keywords = True
            current = None
            continue

        if stripped.startswith("***") and stripped.lower() != "*** keywords ***":
            in_keywords = False
            current = None
            continue

        if not in_keywords or not stripped:
            continue

        if not line.startswith((" ", "\t")):
            current = {"name": stripped, "args": []}
            keywords.append(current)
            continue

        if current and stripped.startswith("[Arguments]"):
            parts = re.split(r"\s{2,}|\t+", stripped)
            current["args"] = parts[1:] if len(parts) > 1 else []

    return keywords

def parse_resource_file(resource_path: Path) -> Dict:
    text = resource_path.read_text(encoding="utf-8")
    return {
        "file": str(resource_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "keywords": extract_keywords_from_resource(text),
        "source": text[:12000]
    }

def build_prompt(manual_data: dict, resource_context: List[Dict]) -> str:
    prompt_manual_data = json.loads(json.dumps(manual_data))
    if isinstance(prompt_manual_data.get("fields"), list):
        prompt_manual_data["fields"] = [
            field for field in prompt_manual_data["fields"]
            if isinstance(field, dict) and any(clean_text(str(field.get(k, ""))) for k in ("name", "label", "type"))
        ]

    payload = {
        "manual_test": prompt_manual_data,
        "resource_context": resource_context,
        "resource_import_prefix": "../pom_pages/",
        "common_resource_hint": "../resources/common_keywords.resource"
    }

    return (
        "You are an expert Robot Framework automation engineer working in a strict POM-based framework.\n"
        "Generate exactly one valid Robot Framework .robot test suite file.\n\n"
        "Framework architecture rules:\n"
        "- Page object resource files are the single source of truth for locators, reusable UI action keywords, page-open keywords, setup/teardown keywords, validation keywords, and reusable test data variables.\n"
        "- Shared framework behavior belongs in common resources such as ../resources/common_keywords.resource. This includes browser lifecycle, generic navigation, generic waits, and generic interaction wrappers.\n"
        "- The generated .robot suite must remain thin and contain only suite-level settings and executable test cases.\n"
        "- Any navigation/open-page/wait-for-page-ready keyword already belongs in the resource layer and must be reused from there.\n"
        "- Any reusable test data such as usernames, passwords, long strings, invalid variants, SQL injection payloads, whitespace variants, and boundary values belongs in the resource layer, not in the test suite.\n"
        "- Every generated test must align with the manual test title, steps, and expectedResult; do not skip the expected validation.\n"
        "- Prefer resource validation keywords and resource variables whenever the resource file suggests they exist or should be reused.\n\n"
        "Mandatory output rules:\n"
        "- Use only the provided resource files and the shared common resource hint.\n"
        "- Always import ../resources/common_keywords.resource in the suite Settings section.\n"
        "- Also import the page resource files listed in manual_test.resourceFiles.\n"
        "- Use provided keyword names and variable names from resource_context wherever possible.\n"
        "- Prefer existing keywords from resource_context over inventing new ones.\n"
        "- Treat resource_context as including both page-specific resources and shared/common resources. Use common/shared keywords for generic browser lifecycle, navigation, and waiting behaviors, and avoid duplicating them in suite logic.\n"
        "- Include *** Settings *** and *** Test Cases *** sections.\n"
        "- Do NOT include a *** Variables *** section in the generated .robot file.\n"
        "- Use compact formatting: no blank lines inside the Settings section, exactly one blank line after *** Test Cases *** before the first test case, exactly one blank line between major sections, and exactly one blank line between test cases.\n"
        "- Every generated test case name must start with AUT- and follow the pattern AUT-<APPCODE>-<FEATURECODE><NN>: <Title>. Example: AUT-WT-LOGIN01: Verify login page loads successfully.\n"
        "- <FEATURECODE> should be derived from the feature name in the input (uppercase alphanumeric, no spaces), and <NN> should be a two-digit sequence aligned to the test order or test case id when possible.\n"
        "- Every generated test case must include a [Tags] line immediately after the test case name. Keep tags minimal: only the testcase id tag and the scenario type tag. Example: [Tags]    WT-LOGIN01    positive.\n"
        "- <APPCODE> should be the uppercase abbreviated application code derived from the module if available, otherwise from the workflow/module context. Use a short stable abbreviation.\n"
        "- Do not add extra tags such as AUT, ui, validation, security, accessibility, or feature-name tags.\n"
        "- Do NOT include a *** Keywords *** section in the generated .robot file unless a test-specific helper is absolutely unavoidable; navigation/page-open/page-ready/data keywords must never be defined in the suite.\n"
        "- Do NOT define keywords such as Open Browser To Login Page, Open Browser To Page, Open Page, Wait Until Login Page Loads, or any equivalent wrapper if the resource layer already provides page-open/navigation capability.\n"
        "- Prefer shared/common resource keywords such as Open Browser Session, Close Browser Session, Open Browser To Url, Open Login Page, Go To Url, Wait For Element To Be Ready, Click When Ready, and Input Text When Ready whenever they fit the intent. Raw SeleniumLibrary keywords in the suite should be a last resort, not the default.\n"
        "- If the resource layer provides browser/page setup or teardown keywords, use them as Test Setup, Suite Setup, Test Teardown, or Suite Teardown as appropriate.\n"
        "- Prefer reusable setup/teardown from shared/common resources for opening and closing browser or preparing generic page state.\n"
        "- If the resource layer appears to provide page-open, page-ready, browser-open, browser-close, or cleanup keywords, use them intelligently in suite/test setup and teardown rather than repeating those actions inside every test.\n"
        "- If test data is reused across test cases, reference a variable from the resource file rather than declaring suite variables.\n"
        "- Use resource variables only for semantically meaningful reusable data such as valid credentials, one canonical invalid credential set, role-specific users, locked users, or other clearly distinct business data supported by the resource context.\n"
        "- Do not create or rely on unnecessary wrapper variables for blank, whitespace-only, padded, or trivially derived values when Robot built-ins and inline composition are sufficient.\n"
        "- For intentionally blank input use Robot built-in ${EMPTY}; for a single blank space use ${SPACE}; do not leave argument positions visually empty.\n"
        "- For values with leading/trailing spaces or other simple compositions, prefer inline expressions such as ${SPACE}${VALID_USERNAME}${SPACE} instead of expecting separate resource aliases like ${USERNAME_WITH_SPACES}.\n"
        "- Reuse canonical semantic variables consistently. If one ${INVALID_USERNAME} or ${INVALID_PASSWORD} already captures the invalid-login intent, reuse it across negative scenarios instead of expecting duplicate variants.\n"
        "- Never hardcode reusable credential and negative/edge data values directly in tests when a meaningful resource variable is available or clearly implied by the resource context. If the approved manual tests clearly require an edge-case value, prefer a semantic resource variable or built-in composition over ad hoc literals in the suite.\n"
        "- For masking, visibility, error message, disabled state, enabled state, page navigation, redirection, and UI behavior expectations, include explicit assertion/verification steps that satisfy expectedResult.\n"
        "- Keep the suite focused on calling resource keywords and assertions only.\n"
        "- Do not include markdown fences.\n"
        "- Return only Robot Framework code.\n"
        "- Use resource import paths with prefix ../pom_pages/ for page resources and import ../resources/common_keywords.resource explicitly for shared resources.\n"
        "- Do not add explanation text before or after the Robot code.\n\n"
        "Robot quality requirements:\n"
        "- Use valid Robot Framework syntax with two-or-more-space separation between keyword and arguments.\n"
        "- Use built-in variables correctly: ${EMPTY}, ${SPACE}, ${True}, ${False}, ${None} only when semantically correct.\n"
        "- Do not leave missing data arguments blank in a keyword call; use an explicit built-in or resource variable.\n"
        "- Each test case should have a clear final verification aligned to its expectedResult.\n"
        "- If a manual test is about password masking, generate an explicit verification for masking behavior instead of only entering data.\n"
        "- If a manual test expects an error message, validation message, rejection, blocked login, or failed authentication, generate an explicit verification for that result, not only a page-loaded check. Prefer dedicated page validation keywords such as Verify Login Error Message, Verify Authentication Error Message, Verify Username Required Validation, Verify Password Required Validation, or Verify Validation Message if the resource context supports them or clearly implies them.\n"
        "- For negative authentication scenarios, do not rely solely on Verify Login Page Loaded. Include at least one stronger observable assertion such as an error message check, validation message check, no-navigation check, or protected-area-not-visible check.\n"
        "- If a manual test expects successful navigation or successful login, generate an explicit verification for landing page, URL change, success state, dashboard/home visibility, or another observable post-condition. Prefer page validation keywords such as Verify Successful Login Redirect when available.\n"
        "- If a manual test expects field-level behavior such as required validation, character masking, disabled state, visibility, duplicate submission prevention, copy-paste behavior, keyboard submission behavior, or no duplicate request behavior, include a corresponding verification step and do not stop at action steps only.\n"
        "- Preserve specialized manual intent. If the approved manual test is specifically about copy-paste, Enter key submission, repeated clicking, whitespace handling, case sensitivity, or duplicate prevention, the generated automation should reflect that interaction intent instead of collapsing it into a generic login flow.\n"
        "- Prefer business-readable test cases that call reusable resource keywords over low-level keyword chains when the resource context supports that style.\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )

def extract_response_text(resp: requests.Response) -> str:
    content_type = resp.headers.get("Content-Type", "").lower()

    if "application/json" in content_type:
        data = resp.json()

        if isinstance(data, dict):
            if data.get("choices"):
                return str(data["choices"][0]["message"]["content"]).strip()
            if "content" in data:
                return str(data["content"]).strip()
            if "response" in data:
                return str(data["response"]).strip()
            if "answer" in data:
                return str(data["answer"]).strip()
            if "detail" in data:
                return str(data["detail"]).strip()

        return json.dumps(data, indent=2)

    return resp.text.strip()


def build_review_prompt(manual_data: dict, resource_context: List[Dict], generated_robot: str) -> str:
    prompt_manual_data = json.loads(json.dumps(manual_data))
    if isinstance(prompt_manual_data.get("fields"), list):
        prompt_manual_data["fields"] = [
            field for field in prompt_manual_data["fields"]
            if isinstance(field, dict) and any(clean_text(str(field.get(k, ""))) for k in ("name", "label", "type"))
        ]

    payload = {
        "manual_test": prompt_manual_data,
        "resource_context": resource_context,
        "generated_robot": generated_robot,
        "resource_import_prefix": "../pom_pages/",
        "common_resource_hint": "../resources/common_keywords.resource"
    }

    return (
        "You are a senior Robot Framework reviewer and repair specialist.\n"
        "Your task is to review an already generated Robot Framework test suite and return a corrected version of the same suite.\n\n"
        "Review objectives:\n"
        "- Preserve the intent and coverage of the approved manual tests.\n"
        "- Correct Robot Framework syntax and framework alignment issues.\n"
        "- Improve reuse of resource keywords, resource variables, setup/teardown, and validation steps.\n"
        "- Ensure the output remains a thin suite that relies on the provided page resource files and the shared common resource layer.\n\n"
        "Mandatory repair rules:\n"
        "- Return only Robot Framework code, with no markdown fences and no explanation.\n"
        "- Preserve compact formatting: no blank lines inside the Settings section, exactly one blank line after *** Test Cases *** before the first test case, exactly one blank line between major sections, and exactly one blank line between test cases.\n"
        "- Ensure every test case name starts with AUT- and follows the pattern AUT-<APPCODE>-<FEATURECODE><NN>: <Title>. Example: AUT-WT-LOGIN01: Verify login page loads successfully.\n"
        "- Ensure every test case includes a [Tags] line immediately after the test case name. Keep tags minimal: only the testcase id tag and the scenario type tag. Example: [Tags]    WT-LOGIN01    positive.\n"
        "- Preserve or repair the numbering so it is stable and aligned to the approved manual test order or id when possible.\n"
        "- Do not add extra tags such as AUT, ui, validation, security, accessibility, or feature-name tags.\n"
        "- Keep only the suite file; do not generate resource content.\n"
        "- Use only the provided resource files from manual_test.resourceFiles plus ../resources/common_keywords.resource as the shared common layer.\n"
        "- Ensure ../resources/common_keywords.resource is imported in the suite Settings section.\n"
        "- Do not add a *** Variables *** section.\n"
        "- Do not add a *** Keywords *** section unless a tiny test-specific helper is absolutely unavoidable; prefer resource keywords instead.\n"
        "- Replace bad blank handling with ${EMPTY} and single-space handling with ${SPACE}. Never leave input arguments visually empty.\n"
        "- Replace hardcoded reusable test data with semantic resource variables whenever the resource context supports it or clearly implies it. Do not leave reusable usernames, passwords, role-specific credentials, or other meaningful business data inline in the suite when a page-resource variable should be used instead.\n"
        "- Eliminate unnecessary dependence on noisy derived variables. If the suite uses aliases that merely duplicate ${EMPTY}, ${SPACE}, padded forms of valid credentials, duplicate invalid credential variants, or other simple compositions, rewrite the suite to use built-ins, canonical semantic variables, and inline composition instead.\n"
        "- Reuse one canonical invalid username/password pair across similar negative scenarios unless the approved manual tests clearly require distinct invalid data classes.\n"
        "- Prefer common/shared resource keywords for generic browser lifecycle, page opening, navigation, waiting, clicking, and text entry when suitable. Raw SeleniumLibrary keywords in the suite should be replaced by shared/common resource keywords whenever a suitable helper exists.\n"
        "- If resource keywords suggest page lifecycle operations, use Suite/Test Setup and Teardown intelligently.\n"
        "- Every test must contain explicit validation aligned to expectedResult.\n"
        "- Prefer page-resource validation keywords over generic visibility checks when the expected result mentions authentication errors, validation messages, redirect behavior, blocked login, duplicate submission prevention, or success outcomes.\n"
        "- If a test is about password masking, ensure there is an explicit masking verification.\n"
        "- If a test is about validation messages, blocked login, rejection behavior, or failed authentication, ensure there is an explicit assertion for that behavior and not only a page-loaded check. For negative authentication scenarios, include at least one stronger observable assertion such as an error message check, validation message check, no-navigation check, or protected-area-not-visible check.\n"
        "- If a test is about successful login or navigation, ensure there is an explicit post-condition verification such as dashboard/home visibility, URL change, success state, or a dedicated page validation keyword.\n"
        "- Preserve specialized interaction intent such as copy-paste, Enter key submission, repeated clicking, whitespace handling, or duplicate submission prevention; do not simplify these into a generic login-only sequence.\n"
        "- Prefer business-readable resource keyword calls over low-level one-off steps.\n"
        "- Do not compensate for duplicated common/page keywords by creating additional duplicates; prefer the shared/common resource keyword when the intent is generic.\n\n"
        "Repair focus areas:\n"
        "- common resource import and reuse\n"
        "- built-in variables (${EMPTY}, ${SPACE})\n"
        "- resource variable reuse instead of hardcoded inline data\n"
        "- setup and teardown usage\n"
        "- validation/assertion coverage from expectedResult\n"
        "- Robot syntax correctness and maintainability\n\n"
        f"Input JSON:\n{json.dumps(payload, indent=2)}"
    )

def call_ai_chat(
    endpoint: str,
    token: str,
    prompt: str,
    timeout_seconds: int = 120,
    verify_ssl: bool = False
) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
    }

    resp = requests.post(
        endpoint,
        headers=headers,
        data={"query": prompt},
        files=[],
        timeout=timeout_seconds,
        verify=verify_ssl,
    )

    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        error_body = ""
        try:
            error_body = extract_response_text(resp)
        except Exception:
            error_body = resp.text.strip()
        raise requests.HTTPError(
            f"{exc}. Response body: {error_body}",
            response=resp
        ) from exc

    return extract_response_text(resp)

def validate_resource_content(content: str, common_resource_context: List[Dict] | None = None) -> tuple[bool, str]:
    errors: list[str] = []
    warnings: list[str] = []

    if "*** Keywords ***" not in content:
        warnings.append("Generated resource does not include a *** Keywords *** section")

    if re.search(r"(?im)^\s*: FOR\b", content):
        errors.append("Generated resource uses deprecated ': FOR' syntax; use modern FOR/END syntax")

    if re.search(r"(?im)^\s*\\\s+", content):
        errors.append("Generated resource uses deprecated backslash loop-body syntax; use modern FOR/END syntax")

    if re.search(r"\n{3,}", content):
        warnings.append("Generated resource contains excessive blank lines; keep formatting compact")

    variables_match = re.search(r"(?is)\*\*\*\s*variables\s*\*\*\*(.*?)(?:\n\*\*\*|\Z)", content)
    if variables_match and re.search(r"\n\s*\n\s*\$\{", variables_match.group(1)):
        errors.append("Generated resource contains blank lines between consecutive variable definitions; keep variable blocks compact")

    if re.search(r"(?im)^\s*Resource\s+\.\./\.\./resources/common_keywords\.resource\s*$", content) is None:
        errors.append("Generated page resource must import ../../resources/common_keywords.resource")

    common_keyword_names = set()
    for item in common_resource_context or []:
        for kw in item.get("keywords", []):
            name = clean_text(str(kw.get("name", "")))
            if name:
                common_keyword_names.add(name.lower())

    for common_name in sorted(common_keyword_names):
        if re.search(rf"(?im)^\s*{re.escape(common_name)}\s*$", content):
            warnings.append(f"Generated resource appears to duplicate shared/common keyword: {common_name}")

    discouraged_page_keywords = [
        "Login With Credentials",
        "Login With Valid Credentials",
        "Submit Login",
        "Perform Successful Login",
        "Perform Login Flow",
    ]
    for keyword_name in discouraged_page_keywords:
        if re.search(rf"(?im)^\s*{re.escape(keyword_name)}\s*$", content):
            warnings.append(
                f"Generated resource contains a broad scenario-wrapper keyword '{keyword_name}'; prefer atomic page-object actions and validations"
            )

    variable_names = re.findall(r"(?im)^\s*\$\{([A-Z0-9_]+)\}\s{2,}(.+?)\s*$", content)
    for var_name, var_value in variable_names:
        upper_name = var_name.upper()
        normalized_value = var_value.strip()
        if "WITH_SPACES" in upper_name and " " not in normalized_value:
            warnings.append(f"Variable ${{{var_name}}} implies spaces but its value does not contain spaces")
        if "SPACE_" in upper_name and "${SPACE}" not in normalized_value and " " not in normalized_value:
            warnings.append(f"Variable ${{{var_name}}} implies a space-oriented value but its value does not contain spaces")
        if "BLANK" in upper_name and "${EMPTY}" not in normalized_value and normalized_value != "":
            warnings.append(f"Variable ${{{var_name}}} implies a blank value but is not blank/${{EMPTY}}")
        if "LONG" in upper_name and len(normalized_value.replace("${SPACE}", " ")) < 16:
            warnings.append(f"Variable ${{{var_name}}} implies a long value but appears short")

    is_valid = len(errors) == 0
    message_parts = []
    if errors:
        message_parts.append("\n".join(errors))
    if warnings:
        message_parts.append("Warnings:\n" + "\n".join(warnings))
    return is_valid, "\n\n".join(part for part in message_parts if part)


def validate_robot_content(content: str, allowed_resources: list[str]) -> tuple[bool, str]:
    errors: list[str] = []
    warnings: list[str] = []

    if "*** Settings ***" not in content:
        errors.append("Missing *** Settings *** section")
    if "*** Test Cases ***" not in content:
        errors.append("Missing *** Test Cases *** section")

    if "*** Variables ***" in content:
        errors.append("Suite-level *** Variables *** section is not allowed; move reusable test data into the POM resource file")
    if "*** Keywords ***" in content:
        errors.append("Suite-level *** Keywords *** section is not allowed for generated automation; use POM resource keywords instead")

    resource_lines = re.findall(r"(?im)^\s*Resource\s+(.+?)\s*$", content)
    normalized_allowed = {f"../pom_pages/{name}" for name in allowed_resources}
    normalized_allowed.add("../resources/common_keywords.resource")

    for resource in resource_lines:
        cleaned = resource.strip()
        if cleaned not in normalized_allowed:
            errors.append(f"Unauthorized resource import: {cleaned}")

    if "../resources/common_keywords.resource" not in {line.strip() for line in resource_lines}:
        warnings.append("Generated suite does not import ../resources/common_keywords.resource; prefer the shared common layer for browser lifecycle and generic helpers")

    forbidden_keyword_patterns = [
        r"(?im)^\s*Open Browser To Login Page\s*$",
        r"(?im)^\s*Open Browser To Page\s*$",
        r"(?im)^\s*Open Page\s*$",
        r"(?im)^\s*Wait Until .* (?:Page|Textbox|Field) .*Visible\s*$",
    ]
    for pattern in forbidden_keyword_patterns:
        if re.search(pattern, content):
            errors.append("Generated suite contains navigation/wait helper definitions that should live in the POM resource file")
            break

    if re.search(r"(?im)^\s*(?:Input|Enter|Type)\b.*\s{2,}$", content):
        errors.append("Generated suite contains an input keyword call with an empty trailing argument; use ${EMPTY} or ${SPACE} explicitly")

    if re.search(r"\$\{Empty\}", content):
        errors.append("Use Robot built-in ${EMPTY} instead of ${Empty}")

    if re.search(r"\$\{Space\}", content):
        errors.append("Use Robot built-in ${SPACE} instead of ${Space}")

    if not re.search(r"(?im)^\s*(?:Suite Setup|Test Setup)\s+.+$", content):
        warnings.append("Generated suite does not include Suite Setup or Test Setup; prefer reusable setup keywords when resource context supports them")

    if not re.search(r"(?im)^\s*(?:Suite Teardown|Test Teardown)\s+.+$", content):
        warnings.append("Generated suite does not include Suite Teardown or Test Teardown; prefer reusable teardown keywords when resource context supports them")

    if re.search(r"(?is)\*\*\*\s*settings\s*\*\*\*.*?\n\s*\n\s*(?:Test Setup|Suite Setup|Test Teardown|Suite Teardown|Resource)", content):
        warnings.append("Generated suite contains unnecessary blank lines inside the Settings section; keep Settings compact")

    if not re.search(r"(?im)^AUT-[A-Z0-9]+-[A-Z0-9]+\d{2}:\s+.+$", content):
        warnings.append("Generated suite test case names should follow the format AUT-<APPCODE>-<FEATURECODE><NN>: <Title>")

    if re.search(r"(?im)^(AUT.*)\n(?!\s+\[Tags\])", content):
        warnings.append("Each generated test case should include a [Tags] line immediately after the test case name")

    if not re.search(r"\$\{[A-Z0-9_]+\}", content):
        warnings.append("Generated suite does not appear to use reusable resource variables; prefer resource-file test data over hardcoded inline data")

    likely_inline_literals = [
        r"(?im)^\s{4,}(?:Enter|Input|Type)\b.*\s{2,}(?!\$\{)(?!xpath=)(?!css=)(?!id=)(?!name=)(?!//)([^\n]+)$",
    ]
    for pattern in likely_inline_literals:
        if re.search(pattern, content):
            warnings.append("Generated suite appears to contain inline literal test data; prefer page-resource variables instead of direct values in test cases")
            break

    is_valid = len(errors) == 0
    message_parts = []
    if errors:
        message_parts.append("\n".join(errors))
    if warnings:
        message_parts.append("Warnings:\n" + "\n".join(warnings))
    return is_valid, "\n\n".join(part for part in message_parts if part)

def derive_module_name(manual_data: dict, manual_json_path: Path) -> str:
    if manual_data.get("workflowName"):
        return slugify(manual_data["workflowName"])
    return slugify(manual_json_path.stem)

def should_exclude_manual(
    manual_json_path: Path,
    manual_data: dict,
    excluded_modules: Set[str],
    excluded_files: Set[str]
) -> bool:
    if manual_json_path.name.lower() in excluded_files:
        return True

    keys = {slugify(manual_json_path.stem)}
    if manual_data.get("workflowName"):
        keys.add(slugify(manual_data["workflowName"]))

    return any(k in excluded_modules for k in keys)

def process_manual_file(config: dict, manual_json_path: Path):
    gc = config["generation_control"]
    ai = config["ai"]

    manual_data = load_json(manual_json_path)

    excluded_modules = set(gc.get("excluded_modules", []))
    excluded_files = set(gc.get("excluded_manual_files", []))
    if should_exclude_manual(manual_json_path, manual_data, excluded_modules, excluded_files):
        logger.info("Excluded manual file: %s", manual_json_path.name)
        return

    resource_files = manual_data.get("resourceFiles", [])
    if not isinstance(resource_files, list) or not resource_files:
        raise ValueError(f"{manual_json_path.name}: 'resourceFiles' must be a non-empty list")

    resource_files = [str(x).replace("\\", "/").strip() for x in resource_files if str(x).strip()]
    if not resource_files:
        raise ValueError(f"{manual_json_path.name}: 'resourceFiles' must contain valid entries")

    module_name = derive_module_name(manual_data, manual_json_path)
    tests_output_dir = BASE_DIR / config["robot_tests_output_dir"]
    output_path = tests_output_dir / f"{module_name}_tests.robot"

    if output_path.exists() and not gc.get("overwrite_robot_tests", False):
        logger.info("Skipped existing robot test (overwrite disabled): %s", output_path.name)
        return

    pom_root = BASE_DIR / config["pom_output_dir"]
    resource_context = []
    for rel_path in resource_files:
        resource_path = pom_root / rel_path
        if not resource_path.exists():
            raise FileNotFoundError(f"{manual_json_path.name}: resource not found -> {resource_path}")
        resource_context.append(parse_resource_file(resource_path))

    resources_dir = BASE_DIR / "resources"
    if resources_dir.exists():
        for common_resource_path in sorted(resources_dir.glob("*.resource")):
            try:
                resource_context.append(parse_resource_file(common_resource_path))
            except Exception:
                continue

    if not ai.get("enabled", True):
        raise ValueError("AI is disabled in config.")

    endpoint = ai.get("endpoint", "")
    token = get_ai_token(ai)
    if not endpoint or not token:
        raise ValueError("AI endpoint/token missing in config.")

    prompt = build_prompt(manual_data, resource_context)
    robot_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=prompt,
        timeout_seconds=ai.get("timeout_seconds", 120),
        verify_ssl=ai.get("verify_ssl", False),
    )

    robot_content = robot_content.strip()
    robot_content = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n", "", robot_content)
    robot_content = re.sub(r"\n```$", "", robot_content)

    review_prompt = build_review_prompt(manual_data, resource_context, robot_content)
    reviewed_robot_content = call_ai_chat(
        endpoint=endpoint,
        token=token,
        prompt=review_prompt,
        timeout_seconds=ai.get("timeout_seconds", 120),
        verify_ssl=ai.get("verify_ssl", False),
    )
    reviewed_robot_content = reviewed_robot_content.strip()
    reviewed_robot_content = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n", "", reviewed_robot_content)
    reviewed_robot_content = re.sub(r"\n```$", "", reviewed_robot_content)
    robot_content = reviewed_robot_content or robot_content

    is_valid, validation_message = validate_robot_content(robot_content, resource_files)
    if not is_valid:
        raise ValueError(
            f"Generated invalid robot content for {manual_json_path.name}: {validation_message}"
        )
    
    ensure_dir(tests_output_dir)
    output_path.write_text(robot_content, encoding="utf-8")
    logger.info("Generated robot test: %s", output_path)

def main():
    config = validate_config(load_json(CONFIG_PATH))

    manual_tests_dir = BASE_DIR / config["manual_tests_output_dir"]
    if not manual_tests_dir.exists():
        raise FileNotFoundError(f"manual_tests directory not found: {manual_tests_dir}")

    manual_files = sorted(manual_tests_dir.glob("*.json"))
    if not manual_files:
        logger.info("No manual test JSON files found in: %s", manual_tests_dir)
        return

    logger.info("Found %d manual files", len(manual_files))
    for mf in manual_files:
        try:
            process_manual_file(config, mf)
        except Exception as exc:
            logger.error("Failed for %s: %s", mf.name, exc)

if __name__ == "__main__":
    main()