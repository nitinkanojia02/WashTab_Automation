#!/usr/bin/env python3
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.generate_robot_from_manual import build_manual_review_prompt, validate_manual_content

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "page_model_config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("generate_manual_tests_json")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "workflow"


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_list_of_strings(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


def get_ai_token(ai_cfg: dict) -> str:
    token = str(ai_cfg.get("token", "")).strip()
    if token:
        return token

    token_env_var = str(ai_cfg.get("token_env_var", "")).strip()
    if token_env_var:
        return os.getenv(token_env_var, "").strip()

    return ""


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return load_json(CONFIG_PATH)


def load_prompt_registry() -> Dict[str, Any]:
    prompt_registry_path = BASE_DIR / "config" / "ai_prompt_registry.json"
    if not prompt_registry_path.exists():
        return {"manual_generation_prompt_version": "1.0"}
    try:
        return load_json(prompt_registry_path)
    except Exception:
        return {"manual_generation_prompt_version": "1.0"}


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    config["workflow_input_dir"] = str(config.get("workflow_input_dir", "workflow_inputs"))
    config["manual_tests_output_dir"] = str(config.get("manual_tests_output_dir", "manual_tests"))

    if "generation_control" not in config:
        config["generation_control"] = {}

    gc = config["generation_control"]
    gc["overwrite_manual_tests"] = bool(gc.get("overwrite_manual_tests", False))
    gc["excluded_workflows"] = [slugify(x) for x in gc.get("excluded_workflows", []) if str(x).strip()]

    if "ai" not in config:
        config["ai"] = {}

    ai = config["ai"]
    ai["enabled"] = bool(ai.get("enabled", False))
    ai["endpoint"] = str(ai.get("endpoint", "")).strip()

    return config


def make_test_id_prefix(workflow_name: str) -> str:
    letters = re.findall(r"[A-Za-z0-9]+", workflow_name.upper())
    if not letters:
        return "TST"
    if len(letters) == 1:
        token = letters[0]
        return (token[:3] if len(token) >= 3 else token.ljust(3, "X"))
    prefix = "".join(x[0] for x in letters[:3])
    return prefix[:3].ljust(3, "X")


def build_prompt(workflow_input: Dict[str, Any]) -> str:
    prompt_version = load_prompt_registry().get("manual_generation_prompt_version", "1.0")
    return f"""
You are AI Layer 1: a senior QA test designer operating inside a multi-layer AI-assisted automation framework. Prompt version: {prompt_version}.
Your output is a reviewable manual-test artifact that will feed downstream Robot generation plus additional AI review and governance layers.

Your goal is not just to list tests, but to produce high-signal manual tests with explicit observable outcomes so later AI layers can generate strong assertions instead of action-only automation.

Analyze the workflow input and generate a practical manual test suite JSON.

Return ONLY a valid JSON object with exactly these top-level keys:
- workflowName
- resourceFiles
- preconditions
- testCases

Return ONLY test cases in JSON form. Do not include commentary, markdown, notes, headings, or explanations.

Mandatory coverage requirements:
1. testCases must be a non-empty array.
2. Generate as many meaningful and distinct test cases as reasonably possible for the workflow.
3. Do not artificially limit the number of test cases.
4. Cover all relevant scenarios you can infer from the workflow input.
5. The generated suite must include all of the following categories wherever applicable:
   - Positive test cases
   - Negative test cases
   - UI test cases
   - Field validation test cases
   - Suggested additional edge test cases
6. Use workflow steps, fields, observedValidations, preconditions, resourceFiles, and expectedResult to infer additional scenarios.
7. Convert every explicit validation into one or more concrete test cases.
8. If fields imply likely validations, generate those test cases too even if not explicitly listed.
9. Prefer high coverage and realistic manual execution scenarios over minimal output.
10. Avoid duplicate or redundant test cases.

Schema rules:
1. Every test case object must contain exactly these keys:
   - id
   - title
   - type
   - steps
   - expectedResult
   - fields
2. type must be one of:
   - positive
   - negative
   - edge
3. Preserve resourceFiles exactly if provided in input.
4. Keep steps actionable, UI-focused, and executable manually.
5. Do not include any extra keys.
6. Do not group test cases under separate headings. Place all cases inside testCases.

Coverage guidance:
- Positive cases:
  - valid end-to-end flow
  - valid alternate user actions
  - valid combinations of input
- Negative cases:
  - invalid input
  - incorrect values
  - missing values
  - invalid sequence
  - rejection/error handling
- UI cases:
  - page or form element visibility
  - labels, placeholders, buttons, links, controls
  - control state such as enabled/disabled
  - navigation behavior
  - messages shown on screen
  - focus behavior where relevant
- Field validation cases:
  - required field validation
  - invalid format
  - min length
  - max length
  - boundary values
  - whitespace-only input
  - leading/trailing whitespace
  - special characters
  - unsupported characters
  - numeric/alphanumeric constraints
  - field-specific business validation
- Additional edge cases:
  - unusual but valid input
  - repeated clicks/submissions
  - very long input
  - empty state behavior
  - case sensitivity
  - copy-paste behavior where relevant
  - browser/UI interaction anomalies inferable from workflow
  - alternate but valid navigation path

Important behavior:
- Generate all practical tests the workflow supports on its own.
- Do not stop after a minimum number of cases.
- Infer as many useful UI, validation, negative, and edge scenarios as possible.
- If the workflow is form-based, expand test cases heavily around each field.
- If multiple fields exist, include combination-based validation scenarios where useful.
- If observedValidations exist, transform them into concrete manual test cases, not summary text.
- Write expectedResult values so downstream automation can create observable assertions, not vague outcomes.
- For positive authentication/navigation cases, expectedResult should explicitly mention authenticated state, landing page, redirect, dashboard/home visibility, URL change, or equivalent observable outcome.
- For negative authentication or validation cases, expectedResult should explicitly mention observable rejection, validation messaging, no navigation, protected-area denial, or continued presence of the login/form state where applicable.
- For edge interaction scenarios such as Enter key, repeated clicking, whitespace handling, and long input, expectedResult should describe the exact observable behavior that automation must verify.
- Avoid producing shallow variants that differ only in wording but not in observable intent.
- Prefer tests whose expectedResult can be validated by visible UI state, message, field behavior, redirect behavior, enabled/disabled state, or other observable outcomes.
- Do not write weak expected results like 'system works correctly', 'login should happen', or 'validation should appear' without specifying what exactly must be observed.
- When generating authentication tests, ensure at least one positive case explicitly expects successful login state and at least one negative case explicitly expects failed login state with an observable rejection condition.

Workflow Input:
{pretty_json(workflow_input)}
""".strip()


def call_devex_ai(
    endpoint: str,
    token: str,
    prompt: str,
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
    }

    resp = requests.post(
        endpoint,
        headers=headers,
        data={"query": prompt},
        files=[],
        timeout=timeout_sec,
        verify=False,
    )

    if resp.status_code >= 400:
        raise RuntimeError(f"Devex AI request failed ({resp.status_code}): {resp.text[:500]}")

    content = resp.text.strip()
    parsed = extract_json_block(content)
    if not parsed:
        raise ValueError(f"Devex AI returned non-JSON content: {content[:500]}")

    return parsed


def map_test_type(title: str, expected_result: str, raw_type: str) -> str:
    raw = str(raw_type).strip().lower()
    if raw in {"positive", "negative", "edge"}:
        return raw

    combined = f"{title} {expected_result} {raw}".lower()

    edge_keywords = {
        "edge", "boundary", "limit", "max", "min", "length", "special character",
        "whitespace", "trim", "case sensitivity", "repeated", "duplicate click",
        "copy paste", "long input"
    }
    negative_keywords = {
        "invalid", "error", "reject", "required", "blank", "missing", "incorrect",
        "fail", "not allowed", "unsupported", "validation", "disabled", "warning"
    }

    if any(keyword in combined for keyword in edge_keywords):
        return "edge"
    if any(keyword in combined for keyword in negative_keywords):
        return "negative"
    return "positive"


def normalize_test_case(
    test_case: Dict[str, Any],
    idx: int,
    id_prefix: str,
    fallback_fields: List[str],
    fallback_steps: List[str],
    fallback_expected: str,
) -> Dict[str, Any]:
    title = str(test_case.get("title", "")).strip() or f"Test Case {idx}"
    expected = str(test_case.get("expectedResult", fallback_expected)).strip()
    tc_type = map_test_type(title, expected, str(test_case.get("type", "")))

    tc_id = str(test_case.get("id", "")).strip() or f"{id_prefix}-{idx:03d}"
    steps = ensure_list_of_strings(test_case.get("steps", fallback_steps))
    fields = ensure_list_of_strings(test_case.get("fields", fallback_fields))

    if not steps:
        steps = ["Open the relevant page", "Perform the workflow action"]
    if not expected:
        expected = "System behaves as expected"

    return {
        "id": tc_id,
        "title": title,
        "type": tc_type,
        "steps": steps,
        "expectedResult": expected,
        "fields": fields,
    }


def generate_fallback_test_cases(workflow_input: Dict[str, Any], workflow_name: str) -> List[Dict[str, Any]]:
    fields = ensure_list_of_strings(workflow_input.get("fields", []))
    steps = ensure_list_of_strings(workflow_input.get("steps", []))
    expected = str(workflow_input.get("expectedResult", "")).strip()
    validations = ensure_list_of_strings(workflow_input.get("observedValidations", []))
    id_prefix = make_test_id_prefix(workflow_name)

    base_steps = steps or ["Open the relevant page", "Perform the workflow action"]
    base_expected = expected or "Workflow completes successfully"

    fallback_cases: List[Dict[str, Any]] = [
        {
            "id": f"{id_prefix}-001",
            "title": f"Verify {workflow_name} with valid input",
            "type": "positive",
            "steps": base_steps,
            "expectedResult": base_expected,
            "fields": fields,
        },
        {
            "id": f"{id_prefix}-002",
            "title": f"Verify UI elements are visible and usable for {workflow_name}",
            "type": "positive",
            "steps": ["Open the relevant page", "Observe all relevant UI elements for the workflow"],
            "expectedResult": "All expected UI elements, labels, fields, and action controls are visible and usable",
            "fields": fields,
        },
        {
            "id": f"{id_prefix}-003",
            "title": f"Verify required field validation for {workflow_name}",
            "type": "negative",
            "steps": ["Open the relevant page", "Leave required fields blank", "Attempt to submit the workflow"],
            "expectedResult": "System shows appropriate validation messages for required fields",
            "fields": fields,
        },
        {
            "id": f"{id_prefix}-004",
            "title": f"Verify invalid field input handling for {workflow_name}",
            "type": "negative",
            "steps": base_steps,
            "expectedResult": "System rejects invalid field values and shows appropriate validation or error messages",
            "fields": fields,
        },
        {
            "id": f"{id_prefix}-005",
            "title": f"Verify edge input behavior for {workflow_name}",
            "type": "edge",
            "steps": base_steps,
            "expectedResult": "System handles boundary and unusual inputs correctly without crashing or allowing invalid behavior",
            "fields": fields,
        },
    ]

    next_idx = 6
    for validation in validations:
        fallback_cases.append(
            {
                "id": f"{id_prefix}-{next_idx:03d}",
                "title": f"Verify validation scenario for {workflow_name} - {next_idx - 5}",
                "type": "negative",
                "steps": base_steps,
                "expectedResult": validation,
                "fields": fields,
            }
        )
        next_idx += 1

    return fallback_cases


def normalize_manual_test(generated: Dict[str, Any], workflow_input: Dict[str, Any]) -> Dict[str, Any]:
    workflow_name = str(
        generated.get("workflowName")
        or workflow_input.get("workflowName")
        or "Workflow"
    ).strip()

    resource_files = generated.get("resourceFiles")
    if not isinstance(resource_files, list) or not resource_files:
        resource_files = workflow_input.get("resourceFiles", [])

    preconditions = ensure_list_of_strings(
        generated.get("preconditions", workflow_input.get("preconditions", []))
    )

    fallback_fields = ensure_list_of_strings(workflow_input.get("fields", []))
    fallback_steps = ensure_list_of_strings(workflow_input.get("steps", []))
    fallback_expected = str(workflow_input.get("expectedResult", "")).strip()
    id_prefix = make_test_id_prefix(workflow_name)

    raw_cases = generated.get("testCases")
    normalized_cases: List[Dict[str, Any]] = []

    if isinstance(raw_cases, list):
        for idx, tc in enumerate(raw_cases, start=1):
            if not isinstance(tc, dict):
                continue
            normalized_cases.append(
                normalize_test_case(
                    test_case=tc,
                    idx=idx,
                    id_prefix=id_prefix,
                    fallback_fields=fallback_fields,
                    fallback_steps=fallback_steps,
                    fallback_expected=fallback_expected,
                )
            )

    if not normalized_cases:
        normalized_cases = generate_fallback_test_cases(workflow_input, workflow_name)

    seen_ids = set()
    deduped_cases: List[Dict[str, Any]] = []
    seen_signatures = set()

    for idx, tc in enumerate(normalized_cases, start=1):
        tc_id = str(tc.get("id", "")).strip()
        if not tc_id or tc_id in seen_ids:
            tc["id"] = f"{id_prefix}-{idx:03d}"
        seen_ids.add(tc["id"])

        signature = (
            tc["title"].strip().lower(),
            tc["type"].strip().lower(),
            tuple(s.strip().lower() for s in tc["steps"]),
            tc["expectedResult"].strip().lower(),
            tuple(f.strip().lower() for f in tc["fields"]),
        )

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            deduped_cases.append(tc)

    return {
        "workflowName": workflow_name,
        "resourceFiles": [str(x).strip() for x in resource_files if str(x).strip()],
        "preconditions": preconditions,
        "testCases": deduped_cases,
    }


def process_workflow_file(config: Dict[str, Any], input_path: Path) -> None:
    workflow_input = load_json(input_path)
    gc = config["generation_control"]
    ai_cfg = config["ai"]

    wf_name = str(workflow_input.get("workflowName", input_path.stem))
    wf_slug = slugify(wf_name)

    if wf_slug in set(gc.get("excluded_workflows", [])):
        logger.info("Skipped excluded workflow: %s", wf_name)
        return

    output_dir = BASE_DIR / config["manual_tests_output_dir"]
    output_path = output_dir / f"{wf_slug}.json"

    if output_path.exists() and not gc.get("overwrite_manual_tests", False):
        logger.info("Manual test already exists (overwrite=false): %s", output_path)
        return

    if not ai_cfg.get("enabled", False):
        raise RuntimeError("AI is disabled in page_model_config.json.")

    endpoint = ai_cfg.get("endpoint", "").strip()
    token = get_ai_token(ai_cfg)

    if not endpoint or not token:
        raise RuntimeError("Missing ai.endpoint or AI token.")

    prompt = build_prompt(workflow_input)
    generated = call_devex_ai(
        endpoint=endpoint,
        token=token,
        prompt=prompt,
    )
    reviewed = call_devex_ai(
        endpoint=endpoint,
        token=token,
        prompt=build_manual_review_prompt(generated),
    )
    final_json = normalize_manual_test(reviewed or generated, workflow_input)
    is_valid, validation_message = validate_manual_content(final_json)
    if not is_valid:
        raise ValueError(f"Generated invalid manual content for {input_path.name}: {validation_message}")
    if validation_message:
        logger.warning("Manual content review warnings for %s: %s", input_path.name, validation_message)
    save_json(output_path, final_json)

    logger.info("Manual test JSON generated: %s", output_path)


def main():
    config = validate_config(load_config())

    workflow_input_dir = BASE_DIR / config["workflow_input_dir"]
    if not workflow_input_dir.exists():
        raise FileNotFoundError(f"workflow_inputs directory not found: {workflow_input_dir}")

    workflow_files = sorted(workflow_input_dir.glob("*.json"))
    if not workflow_files:
        logger.info("No workflow input JSON files found in: %s", workflow_input_dir)
        return

    logger.info("Found %d workflow input files", len(workflow_files))
    for wf in workflow_files:
        try:
            process_workflow_file(config, wf)
        except Exception as exc:
            logger.error("Failed for %s: %s", wf.name, exc)


if __name__ == "__main__":
    main()