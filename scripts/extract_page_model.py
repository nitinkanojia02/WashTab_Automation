import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "page_model_config.json"

SUPPORTED_BROWSERS = {"chromium", "chrome", "edge", "firefox", "webkit"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("extract_page_model")

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def slugify(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "element"

def title_case(text: str) -> str:
    return " ".join(word.capitalize() for word in re.split(r"[_\-\s]+", clean_text(text)) if word)

def xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f"\"{value}\""
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

def get_ai_token(ai_cfg: dict) -> str:
    token = str(ai_cfg.get("token", "")).strip()
    if token:
        return token

    token_env_var = str(ai_cfg.get("token_env_var", "")).strip()
    if token_env_var:
        return os.getenv(token_env_var, "").strip()

    return ""

def validate_config(config: dict) -> dict:
    pages = config.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("'pages' must be a list.")

    browser = str(config.get("browser", "chromium")).lower()
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported browser '{browser}'. Supported: {sorted(SUPPORTED_BROWSERS)}")

    config["browser"] = browser
    config["pom_output_dir"] = str(config.get("pom_output_dir", "pom_pages"))
    config["headless"] = bool(config.get("headless", True))
    config["wait_seconds"] = int(config.get("wait_seconds", 3))
    config["accept_cookies"] = bool(config.get("accept_cookies", False))
    config["cookie_button_text"] = str(config.get("cookie_button_text", "Accept"))

    if "generation_control" not in config:
        config["generation_control"] = {}

    gc = config["generation_control"]
    gc["regenerate_pom_pages"] = bool(gc.get("regenerate_pom_pages", True))
    gc["overwrite_pom_pages"] = bool(gc.get("overwrite_pom_pages", False))
    gc["excluded_pom_modules"] = [slugify(x) for x in gc.get("excluded_pom_modules", []) if str(x).strip()]

    if "ai" not in config:
        config["ai"] = {}

    ai = config["ai"]
    ai["enabled"] = bool(ai.get("enabled", False))
    ai["endpoint"] = str(ai.get("endpoint", "")).strip()
    ai["temperature"] = float(ai.get("temperature", 0.2))

    return config

def is_meaningless_label(text: str) -> bool:
    return slugify(text) in {
        "input", "button", "link", "textbox", "password",
        "select", "dropdown", "element", "ion_input", "ion_button"
    }

def infer_role(item: dict) -> str:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}
    input_type = (attrs.get("type") or "").lower()

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
            return "password"
        if input_type == "checkbox":
            return "checkbox"
        if input_type == "radio":
            return "radio"
        return "textbox"
    return "element"

def infer_label(item: dict) -> str:
    attrs = item.get("attributes", {}) or {}
    candidates = [
        item.get("label", ""),
        attrs.get("aria-label", ""),
        attrs.get("placeholder", ""),
        attrs.get("name", ""),
        attrs.get("id", ""),
        attrs.get("data-testid", ""),
        item.get("text", "")
    ]
    for c in candidates:
        c = clean_text(c)
        if c and not is_meaningless_label(c):
            return c
    return clean_text(item.get("tag", "element")) or "element"

def best_identity(item: dict) -> Tuple[str, str, str, str]:
    attrs = item.get("attributes", {}) or {}
    return (
        infer_role(item),
        clean_text(attrs.get("id", "")),
        clean_text(attrs.get("name", "")),
        clean_text(attrs.get("placeholder", "")),
    )

def make_var_name(label: str, role: str, used_names: set) -> str:
    base = slugify(label)
    if is_meaningless_label(base):
        base = role
    if not base.endswith(role):
        base = f"{base}_{role}"

    name = base.upper()
    i = 2
    while name in used_names:
        name = f"{base.upper()}_{i}"
        i += 1
    used_names.add(name)
    return name

def build_best_locator(item: dict) -> str:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}

    text = clean_text(item.get("text", ""))
    placeholder = clean_text(attrs.get("placeholder", ""))
    aria = clean_text(attrs.get("aria-label", ""))
    name = clean_text(attrs.get("name", ""))
    el_id = clean_text(attrs.get("id", ""))
    data_testid = clean_text(attrs.get("data-testid", "") or attrs.get("testid", ""))
    formcontrolname = clean_text(attrs.get("formcontrolname", ""))

    if data_testid:
        return f"xpath=//*[@data-testid={xpath_literal(data_testid)}]"
    if el_id:
        return f"id={el_id}"
    if formcontrolname:
        return f"xpath=//*[@formcontrolname={xpath_literal(formcontrolname)}]"
    if tag == "ion-input":
        if placeholder:
            return f"xpath=//input[@placeholder={xpath_literal(placeholder)}]"
        if name:
            return f"xpath=//input[@name={xpath_literal(name)}]"
        if aria:
            return f"xpath=//input[@aria-label={xpath_literal(aria)}]"
        return "xpath=//ion-input"
    if tag == "ion-button":
        if text:
            return f"xpath=//ion-button[normalize-space(.)={xpath_literal(text)}]"
        if aria:
            return f"xpath=//ion-button[@aria-label={xpath_literal(aria)}]"
        if name:
            return f"xpath=//ion-button[@name={xpath_literal(name)}]"
        return "xpath=//ion-button"
    if name and tag in {"input", "textarea", "select"}:
        return f"xpath=//{tag}[@name={xpath_literal(name)}]"
    if placeholder and tag in {"input", "textarea"}:
        return f"xpath=//{tag}[@placeholder={xpath_literal(placeholder)}]"
    if aria:
        return f"xpath=//{tag}[@aria-label={xpath_literal(aria)}]"
    if text and tag in {"button", "a"}:
        return f"xpath=//{tag}[normalize-space(.)={xpath_literal(text)}]"
    return f"xpath=//{tag}"

def should_skip_item(item: dict) -> bool:
    tag = (item.get("tag") or "").lower()
    attrs = item.get("attributes", {}) or {}
    text = clean_text(item.get("text", ""))
    label = clean_text(item.get("label", ""))
    placeholder = clean_text(attrs.get("placeholder", ""))
    aria = clean_text(attrs.get("aria-label", ""))
    name = clean_text(attrs.get("name", ""))
    el_id = clean_text(attrs.get("id", ""))
    formcontrolname = clean_text(attrs.get("formcontrolname", ""))
    data_testid = clean_text(attrs.get("data-testid", ""))

    allowed = {
        "input", "textarea", "select", "button", "a",
        "ion-button", "ion-input", "ion-select"
    }
    if tag not in allowed:
        return True

    meaningful_content = any([
        text, label, placeholder, aria, name, el_id, formcontrolname, data_testid
    ])

    if not meaningful_content:
        return True

    if tag == "a" and not text and not aria:
        return True

    if tag == "ion-button" and not text and not aria and not name and not el_id:
        return True

    return False

def is_duplicate_item(item: dict, seen_identity: set, seen_locator: set) -> bool:
    identity = best_identity(item)
    locator = build_best_locator(item).lower()
    if identity in seen_identity or locator in seen_locator:
        return True
    seen_identity.add(identity)
    seen_locator.add(locator)
    return False

def collect_elements(page) -> List[dict]:
    js = """
    () => {
      const isVisible = (el) => {
        const s = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        const hiddenByAttr = el.hasAttribute('hidden') || el.getAttribute('aria-hidden') === 'true';
        return s &&
               s.visibility !== 'hidden' &&
               s.display !== 'none' &&
               s.opacity !== '0' &&
               !hiddenByAttr &&
               r.width > 0 &&
               r.height > 0;
      };

      const getText = (el) => {
        const direct = (el.innerText || el.textContent || '').trim();
        if (direct) return direct;

        const child = el.querySelector('button, span, div, label');
        if (child) {
          const childText = (child.innerText || child.textContent || '').trim();
          if (childText) return childText;
        }

        const aria = (el.getAttribute('aria-label') || '').trim();
        if (aria) return aria;

        return '';
      };

      const tags = [
        'input',
        'textarea',
        'select',
        'button',
        'a',
        'ion-button',
        'ion-input',
        'ion-select'
      ];

      const nodes = Array.from(document.querySelectorAll(tags.join(',')));

      return nodes
        .filter(isVisible)
        .map(el => {
          const attrs = {};
          for (const a of el.attributes) attrs[a.name] = a.value;

          let label = '';
          const id = el.getAttribute('id');
          if (id) {
            const linked = document.querySelector(`label[for="${id}"]`);
            if (linked) label = (linked.innerText || linked.textContent || '').trim();
          }
          if (!label) {
            const parent = el.closest('label');
            if (parent) label = (parent.innerText || parent.textContent || '').trim();
          }

          return {
            tag: (el.tagName || '').toLowerCase(),
            text: getText(el),
            attributes: attrs,
            label: label
          };
        });
    }
    """
    raw = page.evaluate(js)
    logger.info("Raw extracted nodes count: %s", len(raw))

    out, seen_id, seen_loc = [], set(), set()
    for item in raw:
        if should_skip_item(item):
            continue
        if is_duplicate_item(item, seen_id, seen_loc):
            continue
        out.append(item)

    logger.info("Filtered extracted elements count: %s", len(out))
    if out:
        tags_summary = {}
        for item in out:
            tag = item.get("tag", "unknown")
            tags_summary[tag] = tags_summary.get(tag, 0) + 1
        logger.info("Element tags after filtering: %s", tags_summary)

    return out

def keyword_doc(action: str, label_title: str, role: str) -> str:
    return f"{action} action for {label_title} ({role}) using page object locator."

def generate_keyword(var_name: str, label: str, role: str) -> str:
    label_title = title_case(label)

    if role in {"button", "link", "radio", "element"}:
        return f"""Click {label_title}
    [Documentation]    {keyword_doc("Click", label_title, role)}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Click Element    ${{{var_name}}}"""

    if role == "textbox":
        return f"""Enter {label_title}
    [Documentation]    {keyword_doc("Enter text", label_title, role)}
    [Arguments]    ${{text}}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Input Text    ${{{var_name}}}    ${{text}}"""

    if role == "password":
        return f"""Enter {label_title}
    [Documentation]    {keyword_doc("Enter password", label_title, role)}
    [Arguments]    ${{password}}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Input Password    ${{{var_name}}}    ${{password}}"""

    if role == "dropdown":
        return f"""Select {label_title}
    [Documentation]    {keyword_doc("Select dropdown value", label_title, role)}
    [Arguments]    ${{value}}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Select From List By Label    ${{{var_name}}}    ${{value}}"""

    if role == "checkbox":
        return f"""Select {label_title}
    [Documentation]    {keyword_doc("Select checkbox", label_title, role)}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Select Checkbox    ${{{var_name}}}"""

    return f"""Click {label_title}
    [Documentation]    {keyword_doc("Click", label_title, role)}
    Wait Until Element Is Visible    ${{{var_name}}}    10s
    Click Element    ${{{var_name}}}"""

def generate_resource(url: str, elements: List[dict]) -> str:
    used_names, variables, keywords = set(), [], []

    for item in elements:
        role = infer_role(item)
        label = infer_label(item)
        locator = build_best_locator(item)
        var_name = make_var_name(label, role, used_names)

        variables.append(f"${{{var_name}}}    {locator}")
        keywords.append(generate_keyword(var_name, label, role))

    settings_block = """*** Settings ***
Library    SeleniumLibrary"""

    variables_block = "*** Variables ***"
    if variables:
        variables_block += "\n" + "\n".join(variables)

    keywords_block = f"""*** Keywords ***
Open Page
    [Documentation]    Navigates current browser session to page URL.
    Go To    {url}

Open Browser To Page
    [Documentation]    Opens browser, maximizes window, and navigates to page URL.
    [Arguments]    ${{browser}}=chrome
    Open Browser    about:blank    ${{browser}}
    Maximize Browser Window
    Open Page"""

    if keywords:
        keywords_block += "\n\n" + "\n\n".join(keywords)

    return f"{settings_block}\n\n{variables_block}\n\n{keywords_block}\n"

def call_ai_chat(endpoint: str, token: str, messages: List[dict], temperature: float = 0.2) -> str:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"messages": messages, "temperature": temperature}
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {"content": resp.text}

    if isinstance(data, dict):
        if data.get("choices"):
            return data["choices"][0]["message"]["content"].strip()
        if "content" in data:
            return str(data["content"]).strip()
        if "response" in data:
            return str(data["response"]).strip()
        if "answer" in data:
            return str(data["answer"]).strip()

    return json.dumps(data, indent=2)

def is_valid_ai_resource(content: str) -> bool:
    if not content.strip():
        return False
    if "```" in content:
        return False
    return "*** Keywords ***" in content and "*** Variables ***" in content

def maybe_ai_generate_keywords(config: dict, page_name: str, url: str, elements: List[dict], resource_path: Path):
    ai = config.get("ai", {})
    if not ai.get("enabled", False):
        return

    endpoint = ai.get("endpoint", "")
    token = get_ai_token(ai)
    temperature = ai.get("temperature", 0.2)

    if not endpoint or not token:
        logger.warning("AI enabled but endpoint/token missing. Skipping AI keyword generation.")
        return

    system_prompt = (
        "You are an expert Robot Framework engineer. "
        "Generate a single valid .resource file with *** Settings ***, *** Variables ***, *** Keywords ***. "
        "Use SeleniumLibrary. Include [Documentation] for every keyword. "
        "Prefer reliable locators from provided elements. Return only Robot code."
    )
    user_payload = {
        "page_name": page_name,
        "url": url,
        "elements": elements
    }

    try:
        ai_content = call_ai_chat(
            endpoint,
            token,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, indent=2)}
            ],
            temperature=temperature
        )
        if is_valid_ai_resource(ai_content):
            resource_path.write_text(ai_content, encoding="utf-8")
            logger.info("AI-enhanced resource generated: %s", resource_path)
        else:
            logger.warning("AI response not in expected Robot format. Kept deterministic resource.")
    except Exception as exc:
        logger.warning("AI keyword generation failed for %s: %s", page_name, exc)

def get_browser_engine(playwright, browser_name: str):
    if browser_name in {"chromium", "chrome", "edge"}:
        return playwright.chromium
    if browser_name == "firefox":
        return playwright.firefox
    if browser_name == "webkit":
        return playwright.webkit
    raise ValueError(f"Unsupported browser: {browser_name}")

def maybe_accept_cookies(page, enabled: bool, button_text: str):
    if not enabled:
        return
    xpath = f"//button[normalize-space(.)={xpath_literal(button_text)}] | //ion-button[normalize-space(.)={xpath_literal(button_text)}]"
    try:
        loc = page.locator(xpath)
        if loc.count() > 0:
            loc.first.click(timeout=3000)
            logger.info("Clicked cookie button: %s", button_text)
    except Exception:
        logger.info("Cookie button not found/click failed. Continuing.")

def wait_for_meaningful_page_content(page, wait_seconds: int):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        logger.info("Networkidle wait timed out; continuing with additional waits.")

    selectors_to_try = [
        "input",
        "button",
        "textarea",
        "select",
        "ion-input",
        "ion-button"
    ]

    found_selector = None
    for selector in selectors_to_try:
        try:
            page.wait_for_selector(selector, state="visible", timeout=5000)
            found_selector = selector
            break
        except Exception:
            continue

    if found_selector:
        logger.info("Meaningful visible selector found: %s", found_selector)
    else:
        logger.warning("No meaningful visible selector found during wait stage.")

    page.wait_for_timeout(wait_seconds * 1000)

    try:
        page.wait_for_function(
            """
            () => {
              const meaningful = Array.from(document.querySelectorAll('input, textarea, select, button, a, ion-input, ion-button, ion-select'))
                .filter(el => {
                  const s = window.getComputedStyle(el);
                  const r = el.getBoundingClientRect();
                  return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
                });
              return meaningful.length >= 2;
            }
            """,
            timeout=8000
        )
        logger.info("Meaningful control count reached expected threshold.")
    except Exception:
        logger.warning("Meaningful control count threshold was not reached before timeout.")

def process_page(playwright, config: dict, page_entry: Dict[str, str]):
    gc = config["generation_control"]
    page_name_raw = page_entry["page_name"]
    page_name = slugify(page_name_raw)
    url = page_entry["url"]

    if page_name in set(gc.get("excluded_pom_modules", [])):
        logger.warning(
            "Page '%s' is listed in generation_control.excluded_pom_modules; extraction will be skipped.",
            page_name_raw,
        )
        return

    root_pom_dir = BASE_DIR / config["pom_output_dir"]
    page_output_dir = root_pom_dir / page_name
    ensure_dir(page_output_dir)

    json_path = page_output_dir / f"{page_name}.elements.json"
    resource_path = page_output_dir / f"{page_name}.resource"
    screenshot_path = page_output_dir / f"{page_name}.png"
    html_path = page_output_dir / f"{page_name}.debug.html"

    if resource_path.exists() and not gc.get("overwrite_pom_pages", False):
        logger.info("Skipped existing POM resource (overwrite disabled): %s", resource_path)
        return

    engine = get_browser_engine(playwright, config["browser"])
    browser = engine.launch(headless=config["headless"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    try:
        logger.info("Opening URL: %s", url)
        page.goto(url, wait_until="domcontentloaded", timeout=120000)

        wait_for_meaningful_page_content(page, config["wait_seconds"])

        logger.info("Final page URL after load: %s", page.url)
        try:
            logger.info("Page title: %s", page.title())
        except Exception:
            logger.info("Unable to fetch page title.")

        maybe_accept_cookies(page, config["accept_cookies"], config["cookie_button_text"])

        try:
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as exc:
            logger.warning("Screenshot failed for %s: %s", page_name, exc)

        try:
            html_path.write_text(page.content(), encoding="utf-8")
        except Exception as exc:
            logger.warning("HTML save failed for %s: %s", page_name, exc)

        elements = collect_elements(page)

        if not elements:
            logger.warning("No meaningful elements extracted for page: %s", page_name)

        json_path.write_text(json.dumps(elements, indent=2, ensure_ascii=False), encoding="utf-8")

        resource_content = generate_resource(url, elements)
        resource_path.write_text(resource_content, encoding="utf-8")
        logger.info("Generated deterministic resource: %s", resource_path)

        maybe_ai_generate_keywords(config, page_name, url, elements, resource_path)

        logger.info("Generated: %s", json_path)
        logger.info("Generated: %s", screenshot_path)
        logger.info("Generated: %s", html_path)

    except PlaywrightTimeoutError as exc:
        logger.error("Timeout while processing %s: %s", url, exc)
        raise
    finally:
        browser.close()

def build_single_page_config(config: dict, page_name: str, url: str) -> dict:
    single_config = dict(config)
    single_config["pages"] = [{
        "page_name": page_name,
        "url": url
    }]
    return single_config

def parse_args():
    parser = argparse.ArgumentParser(description="Extract page model(s) and generate POM resources.")
    parser.add_argument("--page-name", help="Extract only this page name.")
    parser.add_argument("--url", help="Extract only this page URL.")
    return parser.parse_args()

def main():
    args = parse_args()
    config = validate_config(load_config())
    gc = config["generation_control"]

    if not gc.get("regenerate_pom_pages", True):
        logger.info("POM generation is disabled via config (regenerate_pom_pages=false). Exiting.")
        return

    if args.page_name or args.url:
        if not args.page_name or not args.url:
            raise ValueError("Both --page-name and --url must be provided for single-page extraction.")
        config = build_single_page_config(config, args.page_name, args.url)

    pages = config.get("pages", [])
    if not pages:
        raise ValueError("No pages available for extraction.")

    ensure_dir(BASE_DIR / config["pom_output_dir"])

    with sync_playwright() as playwright:
        for page_entry in pages:
            try:
                process_page(playwright, config, page_entry)
            except Exception as exc:
                logger.error("Failed page '%s': %s", page_entry.get("page_name"), exc)
                raise

if __name__ == "__main__":
    main()