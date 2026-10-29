#!/usr/bin/env python3
"""Phase 2 checks: python3 .circleci/test-config-data.py -v.

Requires Bash, PyYAML and yamllint in the running Python environment. No
dependencies are installed by this suite. Real-upstream tests are mandatory;
their absence fails the suite rather than silently skipping acceptance checks.
This is local evidence, not a CircleCI run or the Phase 5 release matrix.
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
DIAGNOSTIC = "yamllint Orb: config_file and config_data cannot both be non-empty."
CONFIG = 'extends: "default"\nrules:\n  line-length: disable\n'
WARNING_CONFIG = (
    'extends: "default"\nrules:\n  line-length:\n'
    '    max: 20\n    level: warning\n'
)
RECORDER = r'''import json, os, subprocess, sys
with open(os.environ['ARGV_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps(sys.argv[1:]) + '\n')
if os.environ['USE_REAL_YAMLLINT'] == '1':
    sys.exit(subprocess.run([sys.executable, '-m', 'yamllint', *sys.argv[1:]],
                           check=False).returncode)
sys.stdout.write(os.environ.get('RECORDER_STDOUT', ''))
sys.stderr.write(os.environ.get('RECORDER_STDERR', ''))
sys.exit(int(os.environ.get('RECORDER_STATUS', '0')))
'''


def require_refusal(result, calls):
    """Require the complete refusal contract, including no body invocation."""
    if result.returncode != 2:
        raise AssertionError(f"Expected exit 2, got {result.returncode}")
    if DIAGNOSTIC not in result.stderr:
        raise AssertionError("Missing Orb diagnostic on stderr")
    if calls:
        raise AssertionError(f"yamllint body was called: {calls!r}")


class Sandbox(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="yamllint-config-data-")
        self.addCleanup(temporary.cleanup)
        self.cwd = Path(temporary.name)
        binary = self.cwd / "bin"
        binary.mkdir()
        recorder = binary / "yamllint"
        recorder.write_text(f"#!{sys.executable}\n" + RECORDER, encoding="utf-8")
        recorder.chmod(0o755)
        self.log = self.cwd / "argv.jsonl"
        self.env = os.environ.copy()
        for name in ("BASH_ENV", "ENV", "CDPATH", "YAMLLINT_CONFIG_FILE"):
            self.env.pop(name, None)
        self.env.update(
            PATH=f"{binary}{os.pathsep}{self.env['PATH']}",
            HOME=str(self.cwd), XDG_CONFIG_HOME=str(self.cwd / "xdg"),
            ARGV_LOG=str(self.log), USE_REAL_YAMLLINT="0",
            RECORDER_STATUS="0", RECORDER_STDOUT="", RECORDER_STDERR="",
            PARAM_TARGETS="sample.yml", PARAM_CONFIG_FILE="", PARAM_CONFIG_DATA="",
            PARAM_STRICT="false", PARAM_FORMAT="",
        )

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def run_process(self, argv, **environment):
        return subprocess.run(
            argv, cwd=self.cwd, env={**self.env, **environment}, input="",
            text=True, capture_output=True, timeout=15, check=False,
        )

    def execute(self, script=EXECUTE, **environment):
        self.log.unlink(missing_ok=True)
        return self.run_process(["bash", str(script)], **environment)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ArgumentContract(Sandbox):
    def test_public_parameter_and_source_wiring(self):
        command = yaml.safe_load((ROOT / "src/commands/execute.yml").read_text())
        parameter = command["parameters"]["config_data"]
        self.assertEqual(parameter["type"], "string")
        self.assertEqual(parameter["default"], "")
        steps = [step["run"] for step in command["steps"] if "run" in step]
        execution = [step for step in steps
                     if step["command"] == "<<include(scripts/execute.sh)>>"]
        self.assertEqual(len(execution), 1)
        self.assertEqual(execution[0]["environment"]["PARAM_CONFIG_DATA"],
                         "<< parameters.config_data >>")

    def test_empty_and_unset_preserve_discovery_and_config_file(self):
        for unset in (False, True):
            for filename in ("", "config with spaces.yml"):
                with self.subTest(unset=unset, config_file=filename):
                    if unset:
                        self.env.pop("PARAM_CONFIG_DATA", None)
                    else:
                        self.env["PARAM_CONFIG_DATA"] = ""
                    result = self.execute(PARAM_CONFIG_FILE=filename)
                    self.assert_success(result)
                    options = ["--config-file", filename] if filename else []
                    self.assertEqual(self.calls(), [[*options, "--", "sample.yml"]])

    def test_nonempty_data_is_one_exact_argument_without_normalization(self):
        for value in (CONFIG, "relaxed", " ", "\n", "\t\n", "null", "[", "--help"):
            with self.subTest(value=value):
                self.assert_success(self.execute(PARAM_CONFIG_DATA=value))
                self.assertEqual(self.calls(), [
                    ["--config-data", value, "--", "sample.yml"]])

    def test_data_combines_with_existing_options_and_literal_targets(self):
        result = self.execute(PARAM_CONFIG_DATA=CONFIG, PARAM_STRICT="true",
                              PARAM_FORMAT="parsable",
                              PARAM_TARGETS='first file.yml\n\n--help\n"quoted".yml')
        self.assert_success(result)
        self.assertEqual(self.calls(), [[
            "--config-data", CONFIG, "--strict", "--format", "parsable",
            "--", "first file.yml", "--help", '"quoted".yml',
        ]])

    def test_shell_metacharacters_are_not_evaluated(self):
        value = CONFIG + (
            '# "quotes" \'quotes\' $HOME ${HOME} $(touch injected-dollar)\n'
            '# `touch injected-backtick`; touch injected-semicolon\n'
            '# back\\slash *.yml [ab]? & | > <\n'
        )
        self.assert_success(self.execute(PARAM_CONFIG_DATA=value))
        self.assertEqual(self.calls(), [["--config-data", value, "--", "sample.yml"]])
        self.assertEqual(list(self.cwd.glob("injected-*")), [])

    def test_upstream_status_stdout_and_stderr_are_preserved(self):
        for status in (0, 1, 2, 17):
            with self.subTest(status=status):
                result = self.execute(PARAM_CONFIG_DATA="relaxed",
                                      RECORDER_STATUS=str(status),
                                      RECORDER_STDOUT="body output\n",
                                      RECORDER_STDERR="body diagnostic\n")
                self.assertEqual(result.returncode, status)
                self.assertEqual(result.stdout, "body output\n")
                self.assertEqual(result.stderr, "body diagnostic\n")
                self.assertEqual(self.calls(), [
                    ["--config-data", "relaxed", "--", "sample.yml"]])


class ConflictRefusal(Sandbox):
    def test_conflict_is_rejected_before_body_invocation(self):
        for filename, data in (("missing.yml", CONFIG), (" ", "\n"),
                               ("settings.yml", "relaxed")):
            with self.subTest(config_file=filename, config_data=data):
                result = self.execute(PARAM_CONFIG_FILE=filename, PARAM_CONFIG_DATA=data)
                require_refusal(result, self.calls())

    def test_verifier_detects_each_broken_condition_in_executed_mutants(self):
        source = EXECUTE.read_text()
        lines = [line for line in source.splitlines(keepends=True) if DIAGNOSTIC in line]
        self.assertEqual(len(lines), 1, "Locate the actual refusal to mutate")
        line = lines[0]
        indent = line[:len(line) - len(line.lstrip())]
        refusal = line + indent + "exit 2\n"
        self.assertEqual(source.count(refusal), 1)
        mutants = {
            "unexpected success": refusal.replace("exit 2", "exit 0"),
            "wrong failure status": refusal.replace("exit 2", "exit 1"),
            "missing diagnostic": indent + "exit 2\n",
            "diagnostic only on stdout": refusal.replace(" >&2", ""),
            "body invoked": indent + "yamllint -- sample.yml\n" + refusal,
        }
        mutated = self.cwd / "mutated-execute.sh"
        for name, replacement in mutants.items():
            with self.subTest(mutant=name):
                mutated.write_text(source.replace(refusal, replacement, 1))
                result = self.execute(mutated, PARAM_CONFIG_FILE="settings.yml",
                                      PARAM_CONFIG_DATA=CONFIG)
                with self.assertRaises(AssertionError):
                    require_refusal(result, self.calls())


class RealYamllint(Sandbox):
    @classmethod
    def setUpClass(cls):
        cls.version = importlib.metadata.version("yamllint")
        print(f"Real upstream: yamllint {cls.version}; Python {sys.version.split()[0]}",
              flush=True)

    def setUp(self):
        super().setUp()
        self.env["USE_REAL_YAMLLINT"] = "1"
        (self.cwd / "sample.yml").write_text('---\nmessage: "' + "word " * 30 + '"\n')

    def compare(self, options, expected_status=None, **parameters):
        direct = self.run_process([sys.executable, "-m", "yamllint", *options,
                                   "--", "sample.yml"])
        actual = self.execute(**parameters)
        self.assertEqual(self.calls(), [[*options, "--", "sample.yml"]])
        self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                         (direct.returncode, direct.stdout, direct.stderr))
        if expected_status is not None:
            self.assertEqual(actual.returncode, expected_status,
                             actual.stdout + actual.stderr)
        return actual

    def test_multiline_config_changes_real_lint_result(self):
        control = self.compare([], expected_status=1)
        self.assertIn("line-length", control.stdout)
        accepted = self.compare(["--config-data", CONFIG], expected_status=0,
                                PARAM_CONFIG_DATA=CONFIG)
        self.assertEqual(accepted.stdout, "")

    def test_empty_config_data_uses_discovery(self):
        (self.cwd / ".yamllint").write_text(CONFIG)
        self.compare([], expected_status=0, PARAM_CONFIG_DATA="")

    def test_config_file_only_still_overrides_discovery(self):
        (self.cwd / ".yamllint").write_text("extends: default\n")
        (self.cwd / "config file.yml").write_text(CONFIG)
        self.compare(["--config-file", "config file.yml"], expected_status=0,
                     PARAM_CONFIG_FILE="config file.yml")

    def test_config_data_overrides_discovery_without_merge(self):
        (self.cwd / ".yamllint").write_text("extends: default\n")
        self.compare(["--config-data", CONFIG], expected_status=0, PARAM_CONFIG_DATA=CONFIG)

    def test_nonempty_settings_are_delegated_without_fallback(self):
        cases = (
            ("relaxed", False), ("[", True),
            ("rules:\n  nonexistent-orb-rule: enable\n", True),
            (" ", False), ("\n", False), ("null", False), ("--help", False),
        )
        for value, must_fail in cases:
            with self.subTest(config_data=value):
                result = self.compare(["--config-data", value], PARAM_CONFIG_DATA=value)
                if must_fail:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr)

    def test_strict_and_format_preserve_warning_result(self):
        result = self.compare(
            ["--config-data", WARNING_CONFIG, "--strict", "--format", "parsable"],
            expected_status=2, PARAM_CONFIG_DATA=WARNING_CONFIG, PARAM_STRICT="true",
            PARAM_FORMAT="parsable",
        )
        self.assertIn("[warning]", result.stdout)
        self.assertIn("line-length", result.stdout)

    def test_real_settings_do_not_execute_shell_text(self):
        value = CONFIG + '# $(touch injected-dollar) `touch injected-backtick`\n'
        self.compare(["--config-data", value], expected_status=0, PARAM_CONFIG_DATA=value)
        self.assertEqual(list(self.cwd.glob("injected-*")), [])


if __name__ == "__main__":
    unittest.main()
