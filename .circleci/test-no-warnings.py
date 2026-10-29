#!/usr/bin/env python3
"""Phase 3 checks: python3 .circleci/test-no-warnings.py -v.

Requires Python 3.8+, Bash, PyYAML and real yamllint in this Python environment.
Expected failures are checked by a shim that calls the real linter and only
returns success after exact argument, status and output comparisons. A second
pass uses the upstream CLI entry point to check the Orb's actual exit status.
Missing dependencies fail the suite. This does not establish a CircleCI run.
"""

import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXECUTE = ROOT / "src/scripts/execute.sh"
CONFIG = (
    "extends: default\nrules:\n  line-length:\n"
    "    max: 20\n    level: warning\n"
)
VERIFIER = r'''import json, os, subprocess, sys
from pathlib import Path
result = subprocess.run([sys.executable, '-m', 'yamllint', *sys.argv[1:]],
                        text=True, capture_output=True, check=False)
actual = dict(argv=sys.argv[1:], status=result.returncode,
              stdout=result.stdout, stderr=result.stderr)
with open(os.environ['CALL_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps(actual) + '\n')
expected = json.loads(Path(os.environ['EXPECTED_FILE']).read_text())
if actual != expected:
    print('yamllint verifier: arguments, status or output did not match', file=sys.stderr)
    sys.exit(1)
Path(os.environ['VERIFIED_FILE']).write_text('verified\n')
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(0)
'''
UPSTREAM_ENTRY_POINT = "from yamllint.cli import run\nrun()\n"


class NoWarnings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        version = importlib.metadata.version("yamllint")
        print(f"Real upstream: yamllint {version}; Python {sys.version.split()[0]}",
              flush=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="yamllint-no-warnings-")
        self.addCleanup(temporary.cleanup)
        self.cwd = Path(temporary.name)
        self.bin = self.cwd / "verifier-bin"
        self.raw_bin = self.cwd / "upstream-bin"
        for directory, source in ((self.bin, VERIFIER),
                                  (self.raw_bin, UPSTREAM_ENTRY_POINT)):
            directory.mkdir()
            executable = directory / "yamllint"
            executable.write_text(f"#!{sys.executable}\n" + source, encoding="utf-8")
            executable.chmod(0o755)
        self.expected = self.cwd / "expected.json"
        self.calls = self.cwd / "calls.jsonl"
        self.verified = self.cwd / "verified"
        (self.cwd / "settings.yml").write_text(CONFIG)
        long_line = 'message: "' + "word " * 10 + '"'
        (self.cwd / "warning.yml").write_text("---\n" + long_line + "\n")
        # Both warning and error: hiding warnings must not also hide errors.
        (self.cwd / "error.yml").write_text("---\n" + long_line + "  \n")
        self.env = os.environ.copy()
        for name in ("BASH_ENV", "ENV", "CDPATH", "YAMLLINT_CONFIG_FILE",
                     "PARAM_NO_WARNINGS"):
            self.env.pop(name, None)
        self.env.update(
            PATH=f"{self.bin}{os.pathsep}{self.env['PATH']}",
            HOME=str(self.cwd), XDG_CONFIG_HOME=str(self.cwd / "xdg"),
            EXPECTED_FILE=str(self.expected), CALL_LOG=str(self.calls),
            VERIFIED_FILE=str(self.verified), PARAM_TARGETS="warning.yml",
            PARAM_CONFIG_FILE="settings.yml", PARAM_CONFIG_DATA="",
            PARAM_STRICT="false", PARAM_FORMAT="parsable",
        )

    def run_process(self, argv, **environment):
        return subprocess.run(
            argv, cwd=self.cwd, env={**self.env, **environment}, input="",
            text=True, capture_output=True, timeout=20, check=False,
        )

    def observe(self, argv):
        result = self.run_process([sys.executable, "-m", "yamllint", *argv])
        return dict(argv=argv, status=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)

    def clear_calls(self):
        self.calls.unlink(missing_ok=True)
        self.verified.unlink(missing_ok=True)

    def require_verified(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.verified.exists(), "Verifier did not complete")
        self.assertTrue(self.calls.exists(), "yamllint was not invoked")
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 1, "Expected exactly one body invocation")
        self.assertEqual(calls[0], json.loads(self.expected.read_text()))

    def check_case(self, target, strict, no_warnings, status, warning, error,
                   config_data=False):
        options = ["--config-data", CONFIG] if config_data else [
            "--config-file", "settings.yml"]
        if strict:
            options += ["--strict"]
        if no_warnings in ("true", "1"):
            options += ["--no-warnings"]
        argv = [*options, "--format", "parsable", "--", *target.split("\n")]
        expected = self.observe(argv)
        # Assert behavior independently of the shim's exact-result comparison.
        self.assertEqual(expected["status"], status, expected)
        self.assertEqual("[warning]" in expected["stdout"], warning, expected)
        self.assertEqual("[error]" in expected["stdout"], error, expected)
        if not warning and not error:
            self.assertEqual(expected["stdout"], "")
        if warning:
            self.assertIn("line-length", expected["stdout"])
        if error:
            self.assertIn("trailing-spaces", expected["stdout"])
        self.assertEqual(expected["stderr"], "")
        self.expected.write_text(json.dumps(expected))
        self.clear_calls()
        parameters = dict(PARAM_TARGETS=target, PARAM_STRICT=str(strict).lower())
        if config_data:
            parameters.update(PARAM_CONFIG_FILE="", PARAM_CONFIG_DATA=CONFIG)
        if no_warnings is not None:
            parameters["PARAM_NO_WARNINGS"] = no_warnings
        verified = self.run_process(["bash", str(EXECUTE)], **parameters)
        self.require_verified(verified)
        self.assertEqual((verified.stdout, verified.stderr),
                         (expected["stdout"], expected["stderr"]))
        # Do not let the verifier's success conversion mask an Orb status change.
        raw = self.run_process(["bash", str(EXECUTE)], **parameters,
                               PATH=f"{self.raw_bin}{os.pathsep}{os.environ['PATH']}")
        self.assertEqual((raw.returncode, raw.stdout, raw.stderr),
                         (expected["status"], expected["stdout"], expected["stderr"]))
        return expected

    def test_public_parameter_and_source_wiring(self):
        command = yaml.safe_load((ROOT / "src/commands/execute.yml").read_text())
        parameter = command["parameters"]["no_warnings"]
        self.assertEqual(parameter["type"], "boolean")
        self.assertIs(parameter["default"], False)
        steps = [step["run"] for step in command["steps"] if "run" in step]
        execution = [step for step in steps
                     if step["command"] == "<<include(scripts/execute.sh)>>"]
        self.assertEqual(len(execution), 1)
        self.assertEqual(execution[0]["environment"]["PARAM_NO_WARNINGS"],
                         "<< parameters.no_warnings >>")

    def test_warning_hidden_without_strict_exits_zero(self):
        for value in ("true", "1"):
            with self.subTest(value=value):
                self.check_case("warning.yml", False, value, 0, False, False)

    def test_warning_hidden_with_strict_still_exits_two(self):
        for value in ("true", "1"):
            with self.subTest(value=value):
                self.check_case("warning.yml", True, value, 2, False, False)

    def test_errors_remain_visible_with_both_strict_values(self):
        for strict in (False, True):
            for value in ("true", "1"):
                with self.subTest(strict=strict, value=value):
                    self.check_case("error.yml", strict, value, 1, False, True)

    def test_unset_and_false_preserve_output_and_status(self):
        for target in ("warning.yml", "error.yml"):
            for strict in (False, True):
                status = 1 if target == "error.yml" else (2 if strict else 0)
                with self.subTest(target=target, strict=strict):
                    unspecified = self.check_case(target, strict, None, status,
                                                  True, target == "error.yml")
                    for value in ("false", "0"):
                        disabled = self.check_case(target, strict, value, status,
                                                   True, target == "error.yml")
                        self.assertEqual(unspecified, disabled)

    def test_no_warnings_also_works_with_config_data(self):
        self.check_case("warning.yml", True, "true", 2, False, False, config_data=True)

    def test_multiple_targets_preserve_error_precedence(self):
        self.check_case("warning.yml\nerror.yml", True, "true", 1, False, True)

    def test_verifier_detects_wrong_status_output_and_arguments(self):
        cases = [
            ("warning.yml", True, "true", 2, False, False),
            ("error.yml", True, "true", 1, False, True),
            ("warning.yml", False, "false", 0, True, False),
        ]
        for case in cases:
            observed = self.check_case(*case)
            faults = {
                "wrong status": dict(observed, status=17),
                "unexpected stdout": dict(observed, stdout=observed["stdout"] + "unexpected\n"),
                "unexpected stderr": dict(observed, stderr="unexpected\n"),
                "extra argument": dict(observed, argv=[*observed["argv"], "extra.yml"]),
            }
            if observed["status"]:
                faults["unexpected success"] = dict(observed, status=0)
            if observed["stdout"]:
                faults["missing diagnostic"] = dict(observed, stdout="")
            for name, expected in faults.items():
                with self.subTest(target=case[0], fault=name):
                    self.expected.write_text(json.dumps(expected))
                    self.clear_calls()
                    result = self.run_process([str(self.bin / "yamllint"),
                                               *observed["argv"]])
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("yamllint verifier:", result.stderr)
                    self.assertFalse(self.verified.exists())
                    self.assertTrue(self.calls.exists())

    def test_invocation_guard_detects_an_orb_that_does_not_call_yamllint(self):
        self.check_case("warning.yml", True, "true", 2, False, False)
        self.clear_calls()
        source = EXECUTE.read_text()
        invocation = 'yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[@]}"'
        self.assertEqual(source.count(invocation), 1)
        mutated = self.cwd / "without-invocation.sh"
        mutated.write_text(source.replace(invocation, "true", 1))
        result = self.run_process(["bash", str(mutated)], PARAM_STRICT="true",
                                  PARAM_NO_WARNINGS="true")
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(AssertionError):
            self.require_verified(result)


if __name__ == "__main__":
    unittest.main()
