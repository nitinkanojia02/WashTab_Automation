import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_message(test_node: ET.Element) -> str:
    status_node = test_node.find("status")
    if status_node is not None:
        direct_text = (status_node.text or "").strip()
        if direct_text:
            return " ".join(direct_text.split())

    messages = [
        (msg.text or "").strip()
        for msg in test_node.findall('.//msg')
        if (msg.text or '').strip()
    ]
    if messages:
        return " ".join(messages[-1].split())

    return "No failure reason captured in output.xml"


def build_summary(output_xml_path: Path) -> list[str]:
    tree = ET.parse(output_xml_path)
    root = tree.getroot()
    tests = root.findall('.//test')

    total_count = len(tests)
    passed_tests = []
    failed_tests = []

    for test in tests:
        status_node = test.find('status')
        status = (status_node.get('status') if status_node is not None else 'UNKNOWN').upper()
        test_name = test.get('name', 'Unnamed Test')
        if status == 'PASS':
            passed_tests.append(test_name)
        elif status == 'FAIL':
            failed_tests.append((test_name, extract_message(test)))

    lines = [
        f"TOTAL={total_count}",
        f"PASSED={len(passed_tests)}",
        f"FAILED={len(failed_tests)}",
        "ERROR_MESSAGES_START",
    ]

    for test_name, message in failed_tests:
        lines.append(test_name)
        lines.append(message)

    lines.append("ERROR_MESSAGES_END")
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/robot_results_summary.py <path-to-output.xml>", file=sys.stderr)
        return 1

    output_xml_path = Path(sys.argv[1])
    if not output_xml_path.exists():
        print(f"Results file not found: {output_xml_path}", file=sys.stderr)
        return 1

    try:
        for line in build_summary(output_xml_path):
            print(line)
    except Exception as exc:
        print(f"Failed to parse results file '{output_xml_path}': {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
