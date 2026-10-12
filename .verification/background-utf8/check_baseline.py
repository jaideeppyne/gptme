"""Reject infrastructure failures masquerading as an expected behavioral red."""

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree


def main() -> None:
    proof = Path(sys.argv[1])
    cases = list(ElementTree.parse(proof / "baseline.xml").iter("testcase"))
    assert len(cases) == 11, f"Unexpected collected case count: {len(cases)}"
    failures = []
    passed = []
    for case in cases:
        name = case.attrib["name"]
        assert case.find("error") is None, f"Fixture error: {name}"
        assert case.find("skipped") is None, f"Skipped control: {name}"
        failure = case.find("failure")
        if name.startswith("test_split_utf8_pipe_output["):
            assert failure is not None, f"Regression unexpectedly passed: {name}"
            detail = failure.text or ""
            assert "AssertionError" in detail, detail
            assert "\ufffd" in detail or "\\ufffd" in detail, detail
            assert "fixture did not capture" not in detail, detail
            assert "TimeoutExpired" not in detail, detail
            failures.append(name)
        else:
            assert failure is None, f"Healthy control failed: {name}"
            passed.append(name)
    assert len(failures) == 6 and len(passed) == 5
    tracked = [Path("tests/test_shell_background.py"), Path("gptme/tools/shell_background.py")]
    record = {
        "production_base": "0ddbb90f50aab961feed8188041febf2345cee8d",
        "tests_only_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": platform.python_version(),
        "exit_code": int(sys.argv[2]),
        "timed_out": False,
        "failed_split_cases": failures,
        "passed_controls": passed,
        "sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*tracked, proof / "baseline.xml", proof / "baseline.log"]
        },
    }
    (proof / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
