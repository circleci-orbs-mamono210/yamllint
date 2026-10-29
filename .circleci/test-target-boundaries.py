#!/usr/bin/env python3
"""Local Phase 1 regression tests; these do not establish a CircleCI run.

Run from any directory with Python 3, PyYAML and Bash 4+ available:
    python3 .circleci/test-target-boundaries.py

The recorder replaces yamllint to check argv and pre-execution rejection.
Existing CI shims are extracted from test-deploy.yml, not reimplemented here.
Actual yamllint lint results and the release matrix need separate verification.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

try:
    import yaml
except ImportError as error:
    raise SystemExit("PyYAML is required (also a dependency of yamllint).") from error


ROOT = Path(__file__).resolve().parents[1]
EXECUTE = ROOT / "src/scripts/execute.sh"
CONFIG = yaml.safe_load((ROOT / ".circleci/test-deploy.yml").read_text())
DIAGNOSTIC = (
    "yamllint Orb: standalone '-' is not supported in targets; "
    "use './-' for a file named '-'."
)
RECORDER = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ['ARGV_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:] == ['--version']:
    print('yamllint test-recorder')
    sys.exit(0)
sys.stdout.write(os.environ.get('RECORDER_STDOUT', ''))
sys.stderr.write(os.environ.get('RECORDER_STDERR', ''))
sys.exit(int(os.environ.get('RECORDER_STATUS', '0')))
"""


def run_step(job, name):
    """Read the actual CI shell, reversing CircleCI's literal << escape."""
    matches = [
        step["run"]["command"]
        for step in CONFIG["jobs"][job]["steps"]
        if isinstance(step, dict)
        and isinstance(step.get("run"), dict)
        and step["run"].get("name") == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"Expected one CI step: {job} / {name}")
    return matches[0].replace("\\<<", "<<")


def require_refusal(result, calls):
    """All three contract conditions are mandatory; status alone is insufficient."""
    if result.returncode != 2:
        raise AssertionError(f"Expected exit 2, got {result.returncode}")
    if DIAGNOSTIC not in result.stderr:
        raise AssertionError("Missing Orb refusal diagnostic on stderr")
    if calls:
        raise AssertionError(f"yamllint body was called: {calls!r}")


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="yamllint-targets-")
        self.addCleanup(self.temporary.cleanup)
        self.cwd = Path(self.temporary.name)
        self.bin = self.cwd / "recorder-bin"
        self.bin.mkdir()
        self.recorder = self.bin / "yamllint"
        self.recorder.write_text(RECORDER)
        self.recorder.chmod(0o755)
        self.log = self.cwd / "argv.jsonl"
        self.bash_env = self.cwd / "bash-env"
        self.bash_env.write_text("")
        self.env = os.environ.copy()
        for name in ("BASH_ENV", "ENV", "CDPATH"):
            self.env.pop(name, None)
        self.env.update(
            PATH=f"{self.bin}{os.pathsep}{self.env['PATH']}",
            BASH_ENV=str(self.bash_env),
            ARGV_LOG=str(self.log),
            REAL_YAMLLINT=str(self.recorder),
            RECORDER_STATUS="0",
            RECORDER_STDOUT="",
            RECORDER_STDERR="",
            PARAM_TARGETS=".",
            PARAM_CONFIG_FILE="",
            PARAM_STRICT="false",
            PARAM_FORMAT="",
        )

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] \
            if self.log.exists() else []

    def reset_calls(self):
        self.log.unlink(missing_ok=True)

    def run_process(self, args, **environment):
        return subprocess.run(
            args, cwd=self.cwd, env={**self.env, **environment},
            input="", text=True, capture_output=True, timeout=10, check=False,
        )

    def shell(self, command, **environment):
        return self.run_process(["bash", "-euo", "pipefail", "-c", command],
                                **environment)

    def execute(self, targets, **environment):
        return self.run_process(["bash", str(EXECUTE)], PARAM_TARGETS=targets,
                                **environment)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class TargetArguments(Sandbox):
    def test_normal_multiple_and_empty_targets(self):
        cases = [
            ("file.yml", ["file.yml"]),
            ("directory/", ["directory/"]),
            ("first.yml\nsecond.yml", ["first.yml", "second.yml"]),
            ("\nfirst.yml\n\nsecond.yml\n", ["first.yml", "second.yml"]),
            ("", ["."]),
            ("\n\n", ["."]),
            ("  ", ["  "]),
        ]
        for value, expected in cases:
            with self.subTest(targets=value):
                self.reset_calls()
                self.assert_success(self.execute(value))
                self.assertEqual(self.calls(), [["--", *expected]])

    def test_special_characters_remain_literal_single_arguments(self):
        (self.cwd / "match.yml").write_text("---\nvalue: 1\n")
        targets = [
            "-file.yml", "--help", "--config-file", "--", "./-",
            "a b.yml", '"quoted".yml', "'single'.yml", "*.yml", "[ab]?.yml",
            r"back\slash.yml", "$HOME.yml", "$(touch injected)",
            "`touch injected-backtick`", "first;touch injected-semicolon", " leading ",
        ]
        self.assert_success(self.execute("\n".join(targets)))
        self.assertEqual(self.calls(), [["--", *targets]])
        for name in ("injected", "injected-backtick", "injected-semicolon"):
            self.assertFalse((self.cwd / name).exists(), name)

    def test_options_precede_boundary_and_preserve_values(self):
        result = self.execute("first.yml\n--help", PARAM_CONFIG_FILE="config file.yml",
                              PARAM_STRICT="true", PARAM_FORMAT="parsable")
        self.assert_success(result)
        self.assertEqual(self.calls(), [[
            "--config-file", "config file.yml", "--strict", "--format", "parsable",
            "--", "first.yml", "--help",
        ]])

    def test_standalone_dash_rejected_before_any_body_call(self):
        for value in ("-", "-\nvalid.yml", "valid.yml\n-", "\nvalid.yml\n-\n"):
            with self.subTest(targets=value):
                self.reset_calls()
                require_refusal(self.execute(value), self.calls())

    def test_similar_paths_are_not_normalized_to_dash(self):
        for value in ("./-", "directory/-", " -", "- ", "--"):
            with self.subTest(targets=value):
                self.reset_calls()
                self.assert_success(self.execute(value))
                self.assertEqual(self.calls(), [["--", value]])

    def test_yamllint_exit_status_and_output_are_preserved(self):
        for status in (0, 1, 2, 17):
            with self.subTest(status=status):
                self.reset_calls()
                result = self.execute("file.yml", RECORDER_STATUS=str(status),
                                      RECORDER_STDOUT="lint output\n",
                                      RECORDER_STDERR="lint diagnostic\n")
                self.assertEqual(result.returncode, status)
                self.assertEqual(result.stdout, "lint output\n")
                self.assertEqual(result.stderr, "lint diagnostic\n")
                self.assertEqual(self.calls(), [["--", "file.yml"]])

    def test_existing_invalid_strict_rejection_is_preserved(self):
        result = self.execute("file.yml", PARAM_STRICT="invalid")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid strict value: invalid", result.stderr)
        self.assertEqual(self.calls(), [])


class RefusalVerifier(Sandbox):
    def test_correct_refusal_control(self):
        require_refusal(self.execute("-"), self.calls())

    def test_verifier_detects_each_broken_refusal_condition(self):
        source = EXECUTE.read_text()
        diagnostic_lines = [line for line in source.splitlines(keepends=True)
                            if DIAGNOSTIC in line]
        self.assertEqual(len(diagnostic_lines), 1, "Locate the actual rejection to mutate")
        diagnostic = diagnostic_lines[0]
        indentation = diagnostic[:len(diagnostic) - len(diagnostic.lstrip())]
        refusal = diagnostic + indentation + "exit 2\n"
        self.assertEqual(source.count(refusal), 1, "Expected one rejection fixture")
        mutants = {
            "unexpected success": refusal.replace("exit 2", "exit 0"),
            "wrong failure status": refusal.replace("exit 2", "exit 1"),
            "missing diagnostic": indentation + "exit 2\n",
            "diagnostic only on stdout": refusal.replace(" >&2", ""),
            "body called": indentation + "yamllint -- file.yml\n" + refusal,
        }
        mutant_script = self.cwd / "mutated-execute.sh"
        for name, replacement in mutants.items():
            with self.subTest(mutant=name):
                self.reset_calls()
                mutant_script.write_text(source.replace(refusal, replacement, 1))
                result = self.run_process(["bash", str(mutant_script)], PARAM_TARGETS="-")
                with self.assertRaises(AssertionError):
                    require_refusal(result, self.calls())


class ExistingShims(Sandbox):
    TARGET = "targets-test/valid/"
    OPTIONS = ["--config-file", "combined-test/yamllint.yml", "--strict",
               "--format", "parsable"]
    TARGETS = ["combined-test/selected/first.yml", "combined-test/selected/second.yml"]
    WARNINGS = "".join(
        f"combined-test/selected/{name}.yml:2:21: [warning] line too long (line-length)\n"
        for name in ("first", "second")
    )

    def prepare(self, job):
        is_targets = job == "targets-test"
        step = "Prepare target selection verifier" if is_targets else "Prepare combined parameter verifier"
        self.assert_success(self.shell(run_step(job, step)))
        directory = "targets-test" if is_targets else "combined-test"
        return self.cwd / directory / "bin/yamllint"

    def invoke(self, wrapper, args, combined=False):
        return self.run_process(
            ["bash", str(wrapper), *args],
            RECORDER_STATUS="2" if combined else "0",
            RECORDER_STDOUT=self.WARNINGS if combined else "",
        )

    def test_targets_shim_accepts_exact_arguments_and_retains_call_guard(self):
        wrapper = self.prepare("targets-test")
        guard = run_step("targets-test", "Verify all target selection cases ran")
        self.assertNotEqual(self.shell(guard).returncode, 0)
        for count, targets in enumerate(([self.TARGET], [self.TARGET + "first.yml"],
                                         [self.TARGET + "first.yml", self.TARGET + "second.yml"]), 1):
            (self.cwd / "targets-test/expected-targets.txt").write_text("\n".join(targets) + "\n")
            self.assert_success(self.invoke(wrapper, ["--", *targets]))
            self.assertEqual(self.calls()[-1], ["--", *targets])
            self.assertEqual(self.shell(guard).returncode == 0, count == 3)
        self.assert_success(self.invoke(wrapper, ["--", *targets]))
        self.assertNotEqual(self.shell(guard).returncode, 0)

    def test_targets_shim_rejects_malformed_boundary_and_targets(self):
        wrapper = self.prepare("targets-test")
        cases = {
            "missing boundary": [self.TARGET],
            "misplaced boundary": [self.TARGET, "--"],
            "duplicate boundary": ["--", "--", self.TARGET],
            "missing target": ["--"],
            "extra target": ["--", self.TARGET, "extra.yml"],
            "wrong target": ["--", "wrong.yml"],
            "unexpected option": ["--strict", "--", self.TARGET],
        }
        for name, args in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(self.invoke(wrapper, args).returncode, 0)
                self.assertEqual(self.calls(), [])
                self.assertEqual((self.cwd / "targets-test/verified-calls.txt").read_text(), "")

    def test_combined_shim_accepts_exact_arguments_and_retains_call_guard(self):
        wrapper = self.prepare("combined-parameters-test")
        guard = run_step("combined-parameters-test", "Verify combined command actually ran")
        self.assertNotEqual(self.shell(guard).returncode, 0)
        args = [*self.OPTIONS, "--", *self.TARGETS]
        self.assert_success(self.invoke(wrapper, args, combined=True))
        self.assertEqual(self.calls(), [args])
        self.assert_success(self.shell(guard))

    def test_combined_shim_rejects_malformed_boundary_and_targets(self):
        wrapper = self.prepare("combined-parameters-test")
        cases = {
            "missing boundary": [*self.OPTIONS, *self.TARGETS],
            "boundary before options": ["--", *self.OPTIONS, *self.TARGETS],
            "target before boundary": [*self.OPTIONS, self.TARGETS[0], "--", self.TARGETS[1]],
            "duplicate boundary": [*self.OPTIONS, "--", "--", *self.TARGETS],
            "missing target": [*self.OPTIONS, "--", self.TARGETS[0]],
            "extra target": [*self.OPTIONS, "--", *self.TARGETS, "extra.yml"],
            "wrong target": [*self.OPTIONS, "--", "wrong.yml", self.TARGETS[1]],
            "option after boundary": [*self.OPTIONS, "--", *self.TARGETS, "--strict"],
        }
        for name, args in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(self.invoke(wrapper, args, combined=True).returncode, 0)
                self.assertEqual(self.calls(), [])
                self.assertFalse((self.cwd / "combined-test/verified").exists())

    def test_version_bypass_does_not_count_as_body_verification(self):
        for job, guard_name in (
            ("targets-test", "Verify all target selection cases ran"),
            ("combined-parameters-test", "Verify combined command actually ran"),
        ):
            with self.subTest(job=job):
                self.bash_env.write_text("")
                self.reset_calls()
                wrapper = self.prepare(job)
                self.assert_success(self.invoke(wrapper, ["--version"]))
                self.assertEqual(self.calls(), [["--version"]])
                self.assertNotEqual(self.shell(run_step(job, guard_name)).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
