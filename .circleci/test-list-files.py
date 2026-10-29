#!/usr/bin/env python3
"""Phase 4 checks: python3 .circleci/test-list-files.py -v.

Requires Python 3.8+, Bash, PyYAML and real yamllint 1.37.1 or 1.38.0 in
this Python environment. Run once per version. No dependencies are installed
and unsupported versions fail rather than skip version-specific assertions.
These local tests do not establish a CircleCI run or the Phase 5 matrix.
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
    'extends: "default"\nyaml-files: ["*.yml"]\n'
    'ignore: ["fixtures/skip.yml"]\n'
)
CONFLICT = "yamllint Orb: config_file and config_data cannot both be non-empty."
DASH = ("yamllint Orb: standalone '-' is not supported in targets; "
        "use './-' for a file named '-'.")
# The recorder preserves the real CLI's stdout, stderr and exit status. It does
# not turn expected failures into success. The optional guard proves that file
# listing bypasses linter.run; a normal lint control proves the guard is active.
RECORDER = r'''import json, os, subprocess, sys
from pathlib import Path
with open(os.environ['ARGV_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps(sys.argv[1:]) + '\n')
if os.environ.get('GUARD_LINT') == '1':
    from yamllint import cli, linter
    def forbidden_lint(*args, **kwargs):
        Path(os.environ['LINT_MARKER']).write_text('lint called\n')
        sys.exit(91)
    linter.run = forbidden_lint
    cli.run()
# Use the same entry point as the direct control, including traceback paths.
sys.exit(subprocess.run([sys.executable, '-m', 'yamllint', *sys.argv[1:]],
                       check=False).returncode)
'''


def require_refusal(result, calls, diagnostic):
    """Assert in the parent, never in the shell that is expected to exit."""
    if result.returncode != 2:
        raise AssertionError(f"Expected exit 2, got {result.returncode}")
    if diagnostic not in result.stderr:
        raise AssertionError("Missing Orb diagnostic on stderr")
    if result.stdout:
        raise AssertionError("Unexpected stdout during Orb refusal")
    if calls:
        raise AssertionError(f"yamllint body was called: {calls!r}")


class ListFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = importlib.metadata.version("yamllint")
        if cls.version not in ("1.37.1", "1.38.0"):
            raise RuntimeError("Run this suite with yamllint 1.37.1 and 1.38.0")
        print(f"Real upstream: yamllint {cls.version}; "
              f"pathspec {importlib.metadata.version('pathspec')}; "
              f"PyYAML {importlib.metadata.version('PyYAML')}; "
              f"Python {sys.version.split()[0]}", flush=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="yamllint-list-files-")
        self.addCleanup(temporary.cleanup)
        self.cwd = Path(temporary.name)
        binary = self.cwd / "bin"
        binary.mkdir()
        recorder = binary / "yamllint"
        recorder.write_text(f"#!{sys.executable}\n" + RECORDER, encoding="utf-8")
        recorder.chmod(0o755)
        self.log = self.cwd / "argv.jsonl"
        self.lint_marker = self.cwd / "lint-called"
        (self.cwd / "fixtures/sub").mkdir(parents=True)
        for name in ("keep.yml", "drop.yml", "extra.yaml", "skip.yml",
                     "note.txt", "sub/keep.yml"):
            (self.cwd / "fixtures" / name).write_text("---\nvalue: 1\n")
        (self.cwd / "invalid.yml").write_text("---\nvalue: [\n")
        (self.cwd / "settings file.yml").write_text(CONFIG)
        self.env = os.environ.copy()
        for name in list(self.env):
            if name.startswith("PARAM_") or name in (
                    "BASH_ENV", "ENV", "CDPATH", "YAMLLINT_CONFIG_FILE"):
                self.env.pop(name, None)
        self.env.update(
            PATH=f"{binary}{os.pathsep}{self.env['PATH']}",
            HOME=str(self.cwd), XDG_CONFIG_HOME=str(self.cwd / "xdg"),
            ARGV_LOG=str(self.log), LINT_MARKER=str(self.lint_marker),
            GUARD_LINT="0", PARAM_TARGETS="fixtures", PARAM_CONFIG_FILE="",
            PARAM_CONFIG_DATA="", PARAM_STRICT="false", PARAM_NO_WARNINGS="false",
            PARAM_FORMAT="", PARAM_LIST_FILES="true",
        )

    def run_process(self, argv, **environment):
        return subprocess.run(
            argv, cwd=self.cwd, env={**self.env, **environment}, input="",
            text=True, capture_output=True, timeout=20, check=False,
        )

    def execute(self, script=EXECUTE, **parameters):
        self.log.unlink(missing_ok=True)
        return self.run_process(["bash", str(script)], **parameters)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def require_observation(self, actual, expected, argv):
        self.assertEqual(self.calls(), [argv], "Expected one exact body invocation")
        self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                         (expected.returncode, expected.stdout, expected.stderr))

    def compare(self, options, targets=("fixtures",), script=EXECUTE, **parameters):
        argv = [*options, "--", *targets]
        expected = self.run_process([sys.executable, "-m", "yamllint", *argv])
        parameters.setdefault("PARAM_TARGETS", "\n".join(targets))
        actual = self.execute(script, **parameters)
        self.require_observation(actual, expected, argv)
        return actual

    def require_listing(self, result, paths):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        # Do not impose directory ordering. CountEqual still catches duplicates.
        self.assertCountEqual(result.stdout.splitlines(), paths)

    def test_public_parameter_and_source_wiring(self):
        command = yaml.safe_load((ROOT / "src/commands/execute.yml").read_text())
        parameter = command["parameters"]["list_files"]
        self.assertEqual(parameter["type"], "boolean")
        self.assertIs(parameter["default"], False)
        steps = [step["run"] for step in command["steps"] if "run" in step]
        execution = [step for step in steps
                     if step["command"] == "<<include(scripts/execute.sh)>>"]
        self.assertEqual(len(execution), 1)
        self.assertEqual(execution[0]["environment"]["PARAM_LIST_FILES"],
                         "<< parameters.list_files >>")

    def test_common_selection_and_three_config_modes(self):
        for mode in ("discovery", "file", "data"):
            with self.subTest(mode=mode):
                # Explicit settings must override a conflicting discovered config.
                (self.cwd / ".yamllint").write_text(
                    CONFIG if mode == "discovery" else "extends: default\nignore: ['*']\n")
                options, parameters = [], {}
                if mode == "file":
                    options = ["--config-file", "settings file.yml"]
                    parameters = dict(PARAM_CONFIG_FILE="settings file.yml")
                elif mode == "data":
                    options = ["--config-data", CONFIG]
                    parameters = dict(PARAM_CONFIG_DATA=CONFIG)
                result = self.compare([*options, "--list-files"], **parameters)
                self.require_listing(result, ["fixtures/keep.yml", "fixtures/drop.yml",
                                              "fixtures/sub/keep.yml"])

    def test_yaml_files_negative_patterns_by_version(self):
        config = "extends: default\nyaml-files: ['*.yml', '!drop.yml']\n"
        # Explicit per-version expectations, even where the two versions agree.
        expected = {
            "1.37.1": ["fixtures/keep.yml", "fixtures/skip.yml", "fixtures/sub/keep.yml"],
            "1.38.0": ["fixtures/keep.yml", "fixtures/skip.yml", "fixtures/sub/keep.yml"],
        }
        result = self.compare(["--config-data", config, "--list-files"],
                              PARAM_CONFIG_DATA=config)
        self.require_listing(result, expected[self.version])

    def test_ignore_negative_patterns_by_version(self):
        cases = [
            ("['!keep.yml', 'fixtures/']", {
                "1.37.1": [],
                "1.38.0": ["fixtures/keep.yml", "fixtures/sub/keep.yml"],
            }),
            ("['*.yml', '!fixtures/']", {
                "1.37.1": ["fixtures/keep.yml", "fixtures/drop.yml", "fixtures/skip.yml",
                           "fixtures/extra.yaml", "fixtures/sub/keep.yml"],
                "1.38.0": ["fixtures/extra.yaml"],
            }),
        ]
        for patterns, expected in cases:
            config = ("extends: default\nyaml-files: ['*.yml', '*.yaml']\n"
                      f"ignore: {patterns}\n")
            (self.cwd / "settings file.yml").write_text(config)
            for mode in ("file", "data"):
                with self.subTest(patterns=patterns, mode=mode):
                    options = ["--config-file", "settings file.yml"] if mode == "file" else [
                        "--config-data", config]
                    parameters = dict(PARAM_CONFIG_FILE="settings file.yml") if mode == "file" else dict(
                        PARAM_CONFIG_DATA=config)
                    result = self.compare([*options, "--list-files"], **parameters)
                    self.require_listing(result, expected[self.version])

    def test_listing_never_calls_linter_and_guard_detects_lint(self):
        result = self.compare(["--list-files"], ("invalid.yml",), GUARD_LINT="1")
        self.require_listing(result, ["invalid.yml"])
        self.assertFalse(self.lint_marker.exists())
        control = self.execute(PARAM_TARGETS="invalid.yml", PARAM_LIST_FILES="false",
                               GUARD_LINT="1")
        self.assertEqual(control.returncode, 91)
        self.assertEqual(self.lint_marker.read_text(), "lint called\n")
        self.assertEqual(self.calls(), [["--", "invalid.yml"]])

    def test_unset_and_false_keep_normal_lint(self):
        for value in (None, "false"):
            if value is None:
                self.env.pop("PARAM_LIST_FILES", None)
            else:
                self.env["PARAM_LIST_FILES"] = value
            for target, status in (("fixtures/keep.yml", 0), ("invalid.yml", 1)):
                with self.subTest(value=value, target=target):
                    result = self.compare([], (target,))
                    self.assertEqual(result.returncode, status)
                    if status:
                        self.assertIn("syntax", result.stdout)
                    else:
                        self.assertEqual(result.stdout, "")

    def test_literal_targets_are_not_options_or_shell(self):
        targets = ("--version", "space name.yml", '$(touch injected).yml',
                   "./-", "fixtures/note.txt", "space name.yml")
        for target in targets[:4]:
            (self.cwd / target).write_text("---\nvalue: 1\n")
        result = self.compare(["--list-files"], targets,
                              PARAM_TARGETS="\n" + "\n\n".join(targets) + "\n")
        self.require_listing(result, targets)
        self.assertFalse((self.cwd / "injected").exists())

    def test_empty_targets_use_current_directory(self):
        (self.cwd / ".yamllint").write_text(CONFIG)
        for value in ("", "\n\n"):
            with self.subTest(targets=value):
                result = self.compare(["--list-files"], (".",), PARAM_TARGETS=value)
                self.assertEqual(result.returncode, 0)
                self.assertIn("./fixtures/keep.yml", result.stdout.splitlines())
                self.assertNotIn("./fixtures/skip.yml", result.stdout.splitlines())

    def test_valid_strict_and_formats_do_not_change_listing(self):
        baseline = self.compare(["--list-files"], ("invalid.yml",))
        self.require_listing(baseline, ["invalid.yml"])
        for strict in (False, True):
            for format_name in ("", "auto", "standard", "parsable", "colored", "github"):
                with self.subTest(strict=strict, format=format_name):
                    options = ["--strict"] if strict else []
                    if format_name:
                        options += ["--format", format_name]
                    result = self.compare([*options, "--list-files"], ("invalid.yml",),
                                          PARAM_STRICT=str(strict).lower(), PARAM_FORMAT=format_name)
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (baseline.returncode, baseline.stdout, baseline.stderr))

    def test_invalid_format_is_rejected_by_upstream(self):
        result = self.compare(["--format", "invalid-orb-format", "--list-files"],
                              PARAM_FORMAT="invalid-orb-format")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr)

    def test_invalid_config_is_rejected_by_upstream(self):
        for value in ("[", "rules:\n  nonexistent-orb-rule: enable\n"):
            with self.subTest(config_data=value):
                result = self.compare(["--config-data", value, "--list-files"],
                                      PARAM_CONFIG_DATA=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr)
        result = self.compare(["--config-file", "missing-settings.yml", "--list-files"],
                              PARAM_CONFIG_FILE="missing-settings.yml")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr)

    def test_nonexistent_and_invalid_yaml_list_but_fail_lint(self):
        for target in ("nonexistent.yml", "invalid.yml"):
            with self.subTest(target=target):
                listing = self.compare(["--list-files"], (target,))
                self.require_listing(listing, [target])
                lint = self.compare([], (target,), PARAM_LIST_FILES="false")
                self.assertNotEqual(lint.returncode, 0)
                if target == "invalid.yml":
                    self.assertEqual(lint.returncode, 1)
                    self.assertIn("syntax", lint.stdout)
                else:
                    self.assertTrue(lint.stderr)

    def test_standalone_dash_refusal(self):
        for target in ("-", "fixtures/keep.yml\n-", "-\nfixtures/keep.yml"):
            with self.subTest(targets=target):
                result = self.execute(PARAM_TARGETS=target)
                require_refusal(result, self.calls(), DASH)

    def test_configuration_conflict_refusal(self):
        for filename, data in (("settings file.yml", CONFIG), ("missing.yml", "relaxed"),
                               (" ", "\n")):
            with self.subTest(config_file=filename, config_data=data):
                result = self.execute(PARAM_CONFIG_FILE=filename, PARAM_CONFIG_DATA=data)
                require_refusal(result, self.calls(), CONFLICT)

    def test_refusal_guards_detect_executed_mutants(self):
        source = EXECUTE.read_text()
        cases = [(DASH, dict(PARAM_TARGETS="-")),
                 (CONFLICT, dict(PARAM_CONFIG_FILE="settings file.yml", PARAM_CONFIG_DATA=CONFIG))]
        for diagnostic, parameters in cases:
            lines = [line for line in source.splitlines(keepends=True) if diagnostic in line]
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
                "body invoked": indent + "yamllint --list-files -- fixtures/keep.yml\n" + refusal,
            }
            for name, replacement in mutants.items():
                with self.subTest(diagnostic=diagnostic, mutant=name):
                    mutated = self.cwd / "mutated-refusal.sh"
                    mutated.write_text(source.replace(refusal, replacement, 1))
                    result = self.execute(mutated, **parameters)
                    with self.assertRaises(AssertionError):
                        require_refusal(result, self.calls(), diagnostic)

    def test_observation_guard_detects_body_mutants(self):
        source = EXECUTE.read_text()
        invocation = 'yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[@]}"'
        self.assertEqual(source.count(invocation), 1)
        mutants = {
            "no invocation": "true",
            "no listing option": 'yamllint -- "${TARGETS[@]}"',
            "wrong exit status": invocation + "\nexit 17",
            "extra stdout": invocation + "\nprintf 'unexpected output\\n'",
            "extra stderr": invocation + "\nprintf 'unexpected error\\n' >&2",
            "dropped target": 'yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[0]}"',
        }
        for name, replacement in mutants.items():
            with self.subTest(mutant=name):
                mutated = self.cwd / "mutated-body.sh"
                mutated.write_text(source.replace(invocation, replacement, 1))
                with self.assertRaises(AssertionError):
                    self.compare(["--list-files"], ("invalid.yml", "fixtures/keep.yml"),
                                 script=mutated)


if __name__ == "__main__":
    unittest.main()
