#!/usr/bin/env python3
"""Run the fixed-version behavior suites and record only allowlisted CI metadata."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SUITES = [("test-config-data.py", 15), ("test-no-warnings.py", 9),
          ("test-list-files.py", 16), ("test-combinations.py", 3)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=("1.37.1", "1.38.0"), required=True)
    parser.add_argument("--python-version", choices=("3.13", "3.14"), required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--local", action="store_true", help="Supplementary host run; never CI completion evidence")
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    actual = metadata.version("yamllint")
    if actual != args.version:
        raise SystemExit(f"Expected yamllint {args.version}, got {actual}")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not args.local:
        if os.environ.get("CIRCLECI") != "true" or os.environ.get("CIRCLE_SHA1") != commit:
            raise SystemExit("A matching CircleCI checkout is required; use --local for supplemental checks")
        if ".".join(map(str, sys.version_info[:2])) != args.python_version:
            raise SystemExit("Actual Python does not match the configured matrix image")
        subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=ROOT, check=True)
    suites = list(SUITES)
    # Argument-only and unchanged Phase 1 shim checks are version/environment independent.
    if args.version == "1.38.0" and args.python_version == "3.14":
        suites.insert(0, ("test-target-boundaries.py", 14))
    manifest = json.loads((ROOT / ".circleci/compatibility-contract.json").read_text())
    for name, sha in manifest["feature_suite_sha256"].items():
        if hashlib.sha256((ROOT / ".circleci" / name).read_bytes()).hexdigest() != sha:
            raise SystemExit("Feature-owned verifier changed: " + name)
    fields = ("CIRCLE_SHA1", "CIRCLE_JOB", "CIRCLE_BUILD_URL", "CIRCLE_BUILD_NUM",
              "CIRCLE_WORKFLOW_ID", "CIRCLE_PIPELINE_ID", "CIRCLE_BRANCH", "CIRCLE_TAG")
    record = dict(kind="local-supplementary" if args.local else "CircleCI",
                  commit=commit, requested_yamllint=args.version, yamllint=actual,
                  configured_image=f"cimg/python:{args.python_version}",
                  configured_image_executed=not args.local, python=platform.python_version(),
                  architecture=platform.machine(),
                  packages={d.metadata["Name"]: d.version for d in metadata.distributions()},
                  ci={key: os.environ.get(key, "") for key in fields},
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for folder in (ROOT / "src", ROOT / ".circleci")
                                 for p in sorted(folder.rglob("*"))
                                 if p.is_file() and p.suffix in (".py", ".sh", ".yml", ".json")}, results=[])
    output = args.evidence_dir / "results.json"
    output.write_text(json.dumps(record, indent=2) + "\n")
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("PARAM_") or name in ("BASH_ENV", "ENV", "CDPATH", "YAMLLINT_CONFIG_FILE"):
            environment.pop(name, None)
    for name, count in suites:
        start = time.monotonic()
        result = subprocess.run([sys.executable, str(ROOT / ".circleci" / name), "-v"],
                                cwd=ROOT, env=environment, text=True, capture_output=True,
                                timeout=240, check=False)
        log = result.stdout + result.stderr
        (args.evidence_dir / (name + ".log")).write_text(log)
        passed = result.returncode == 0 and f"Ran {count} tests" in log and log.rstrip().endswith("OK")
        record["results"].append(dict(suite=name, expected_test_methods=count, exit_code=result.returncode,
                                      passed=passed, seconds=round(time.monotonic() - start, 3)))
        output.write_text(json.dumps(record, indent=2) + "\n")
        print(log, flush=True)
        if not passed:
            raise SystemExit("Compatibility suite failed or did not complete: " + name)
    record["all_suites_passed"] = True
    record["inline_default_execute"] = "separate following CircleCI step; use job status as its result"
    output.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
