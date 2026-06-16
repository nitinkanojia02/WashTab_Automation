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
    payload = {
        "manual_test": manual_data,
        "resource_context": resource_context,
        "resource_import_prefix": "../pom_pages/",
        "common_resource_hint": "../resources/common_keywords.resource"
    }

    return (
        "You are an expert Robot Framework automation engineer working in a strict POM-based framework.\n"
        "Generate exactly one valid Robot Framework .robot test suite file.\n\n"
        "Framework architecture rules:\n"
        "- Page object resource files are the single source of truth for locators, reusable UI action keywords, page-open keywords, and reusable test data variables.\n"
        "- The generated .robot suite must remain thin and contain only suite-level settings and executable test cases.\n"
        "- Any navigation/open-page/wait-for-page-ready keyword already belongs in the resource file and must be reused from there.\n"
        "- Any reusable test data such as usernames, passwords, long strings, SQL injection payloads, or whitespace variants belongs in the resource file, not in the test suite.\n\n"
        "Mandatory output rules:\n"
        "- Use only the provided resource files.\n"
        "- Import only the resource files listed in manual_test.resourceFiles.\n"
        "- Use provided keyword names from resource_context wherever possible.\n"
        "- Prefer existing keywords from resource_context over inventing new ones.\n"
        "- Include *** Settings *** and *** Test Cases *** sections.\n"
        "- Do NOT include a *** Variables *** section in the generated .robot file.\n"
        "- Do NOT include a *** Keywords *** section in the generated .robot file unless a test-specific helper is absolutely unavoidable; navigation/page-open/page-ready/data keywords must never be defined in the suite.\n"
        "- Do NOT define keywords such as Open Browser To Login Page, Open Browser To Page, Open Page, Wait Until Login Page Loads, or any equivalent wrapper if the resource file already provides page-open/navigation capability.\n"
        "- If test data is reused across test cases, reference a variable from the resource file rather than declaring suite variables.\n"
        "- Keep the suite focused on calling resource keywords and assertions only.\n"
        "- Do not include markdown fences.\n"
        "- Return only Robot Framework code.\n"
        "- Use resource import paths with prefix ../pom_pages/.\n"
        "- Do not add explanation text before or after the Robot code.\n\n"
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

def validate_robot_content(content: str, allowed_resources: list[str]) -> tuple[bool, str]:
    errors: list[str] = []

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

    for resource in resource_lines:
        cleaned = resource.strip()
        if cleaned not in normalized_allowed:
            errors.append(f"Unauthorized resource import: {cleaned}")

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

    is_valid = len(errors) == 0
    return is_valid, "\n".join(errors)

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

    errors = validate_robot_content(robot_content, resource_files)
    if errors:
        raise ValueError(
            f"Generated invalid robot content for {manual_json_path.name}: "
            + "; ".join(str(error) for error in errors)
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