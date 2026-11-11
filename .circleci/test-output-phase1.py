#!/usr/bin/env python3
"""#5506 Phase 1 cross-check: python3 .circleci/test-output-phase1.py -v.

Run on the one revision that contains both #5508 and #5509. Each test_row*
method is one row of the exit-status table in the roadmap
(220_ロードマップ version 2, Phase 1 「終了コードと失敗時の扱い」), exercised
through the real src/scripts/execute.sh as a child process with real yamllint.
The recorder on PATH only logs argv and its stdout connection, then execs real
yamllint with the same argv, environment and file descriptors; no case here
uses a controlled body. Write failures are real: RLIMIT_FSIZE for the result
and /dev/full for the step log. The last test checks that the result file and
temporary data do not change target selection or lint results.

Uses the sandbox from test-output-file.py. Local runs are supplementary and
never CircleCI evidence; #5510 integrates the checks into the fixed matrix.
"""

import importlib.util
import os
from pathlib import Path
import shutil
import unittest


spec = importlib.util.spec_from_file_location(
    "output_file", Path(__file__).with_name("test-output-file.py"))
output_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output_file)
PREFIX = output_file.PREFIX
SELECT_ALL = 'extends: relaxed\nyaml-files: ["*"]\n'
WARNING = dict(PARAM_CONFIG_FILE="settings file.yml")


class ExitStatusTable(output_file.OutputSandbox):
    def saved(self, name):
        return self.results / f"{name}.txt"

    def require_lint(self, result, argv, status):
        """The Orb returned the real upstream status and stdout for argv."""
        direct = self.direct(argv)
        self.assertEqual(direct.returncode, status, "fixture control")
        self.assertEqual(result.returncode, status, result.stderr)
        self.assertEqual([call["argv"] for call in self.calls()], [argv])
        return direct

    def test_row1_output_disabled_is_unchanged(self):
        cases = ((["--", "clean.yml"], {}, 0),
                 (["--config-file", "settings file.yml", "--strict", "--", "warning.yml"],
                  dict(WARNING, PARAM_STRICT="true"), 2),
                 (["--", "error.yml"], {}, 1))
        for argv, parameters, status in cases:
            for value in (None, ""):
                with self.subTest(argv=argv, output_file=value):
                    before = self.entries()
                    result = self.run_orb(PARAM_TARGETS=argv[-1], PARAM_OUTPUT_FILE=value, **parameters)
                    direct = self.require_lint(result, argv, status)
                    self.assertEqual((result.stdout, result.stderr), (direct.stdout, direct.stderr))
                    self.assertEqual(self.entries(), before)

    def test_row2_existing_input_errors_keep_status_2(self):
        cases = ((output_file.CONFLICT, dict(PARAM_CONFIG_FILE="settings file.yml",
                                             PARAM_CONFIG_DATA="relaxed")),
                 (output_file.DASH, dict(PARAM_TARGETS="-")),
                 (output_file.STRICT, dict(PARAM_STRICT="invalid")))
        for diagnostic, parameters in cases:
            with self.subTest(diagnostic=diagnostic):
                before = self.entries()
                result = self.run_orb(PARAM_OUTPUT_FILE=str(self.saved("row2")), **parameters)
                self.require_not_started(result, before, diagnostic)
                self.assertEqual(self.diagnostics(result.stderr), [])

    def test_row3_invalid_conflicting_or_unprepared_destination(self):
        (self.results / "existing.txt").write_text("keep\n")
        only_yamllint = self.base / "without-python3"
        only_yamllint.mkdir()
        shutil.copy2(self.bin / "yamllint", only_yamllint / "yamllint")
        cases = (
            ("invalid", dict(PARAM_OUTPUT_FILE=str(self.results / "a\nb.txt")), b"rejected: "),
            ("existing entry", dict(PARAM_OUTPUT_FILE=str(self.results / "existing.txt")), b"rejected: "),
            ("missing parent", dict(PARAM_OUTPUT_FILE=str(self.results / "missing" / "x.txt")), b"rejected: "),
            ("inside target", dict(PARAM_OUTPUT_FILE="lint.txt"), b"rejected: "),
            ("same as target", dict(PARAM_TARGETS="new.yml", PARAM_OUTPUT_FILE="new.yml"), b"rejected: "),
            ("unwritable directory", dict(PARAM_OUTPUT_FILE="/proc/yamllint-orb-row3.txt"),
             b"could not prepare the output: "),
            ("python3 missing", dict(PATH=str(only_yamllint), PARAM_OUTPUT_FILE=str(self.saved("row3"))),
             b"could not prepare the output: "),
        )
        for name, parameters, diagnostic in cases:
            with self.subTest(case=name):
                before = self.entries()
                result = self.run_orb(**parameters)
                self.require_not_started(result, before, PREFIX + diagnostic)
                self.assertEqual((self.results / "existing.txt").read_text(), "keep\n")

    def test_row4_lint_0_saved_and_forwarded(self):
        argv = ["--config-file", "settings file.yml", "--", "warning.yml"]
        result = self.run_orb(PARAM_TARGETS="warning.yml", PARAM_OUTPUT_FILE=str(self.saved("row4")),
                              **WARNING)
        direct = self.require_lint(result, argv, 0)
        self.assertTrue(direct.stdout)
        self.assertEqual((result.stdout, result.stderr), (direct.stdout, b""))
        self.require_saved(self.saved("row4"), direct.stdout)
        self.require_no_temporaries()

    def test_row5_lint_nonzero_saved_and_forwarded(self):
        cases = ((["--", "error.yml"], {}, 1),
                 (["--config-file", "settings file.yml", "--strict", "--", "warning.yml"],
                  dict(WARNING, PARAM_STRICT="true"), 2),
                 (["--config-data", output_file.WARNING_CONFIG, "--strict", "--no-warnings", "--",
                   "warning.yml"], dict(PARAM_CONFIG_DATA=output_file.WARNING_CONFIG,
                                        PARAM_STRICT="true", PARAM_NO_WARNINGS="true"), 2))
        for index, (argv, parameters, status) in enumerate(cases):
            with self.subTest(argv=argv):
                destination = self.saved(f"row5-{index}")
                result = self.run_orb(PARAM_TARGETS=argv[-1], PARAM_OUTPUT_FILE=str(destination),
                                      **parameters)
                direct = self.require_lint(result, argv, status)
                self.assertEqual((result.stdout, result.stderr), (direct.stdout, b""))
                self.require_saved(destination, direct.stdout)
                self.require_no_temporaries()

    def check_failure_row(self, target, argv, lint_status, fault, **parameters):
        """Real yamllint with a real write failure on the result or on the log."""
        direct = self.direct(argv)
        self.assertEqual(direct.returncode, lint_status, "fixture control")
        self.assertGreater(len(direct.stdout), output_file.SAVE_LIMIT)
        destination = self.saved(f"{target}-{fault}")
        common = dict(PARAM_TARGETS=target, PARAM_OUTPUT_FILE=str(destination), **parameters)
        if fault == "save":
            result = self.run_orb(limit=output_file.SAVE_LIMIT, **common)
        else:
            with open("/dev/full", "wb") as full:
                result = self.run_orb(stdout=full, **common)
        self.assertEqual(result.returncode, lint_status or 2, result.stderr)
        self.assertEqual([call["argv"] for call in self.calls()], [argv])
        diagnostics = self.diagnostics(result.stderr)
        self.assertEqual(result.stderr.splitlines(), diagnostics, "only Orb diagnostics on stderr")
        if fault == "save":
            self.assertEqual(result.stdout, direct.stdout, "log forwarding continued")
            self.require_unsaved(destination)
            self.assertTrue(any(b"could not write" in line for line in diagnostics))
        else:
            self.require_saved(destination, direct.stdout)
            self.assertTrue(any(b"step log" in line for line in diagnostics))
        self.require_no_temporaries()

    def test_row6_lint_0_with_save_or_log_failure_returns_2(self):
        argv = ["--config-file", "settings file.yml", "--", "long-warning.yml"]
        for fault in ("save", "log"):
            with self.subTest(fault=fault):
                self.check_failure_row("long-warning.yml", argv, 0, fault, **WARNING)

    def test_row7_lint_nonzero_with_save_or_log_failure_keeps_lint_status(self):
        argv = ["--format", "parsable", "--", "long-error.yml"]
        for fault in ("save", "log"):
            with self.subTest(fault=fault):
                self.check_failure_row("long-error.yml", argv, 1, fault, PARAM_FORMAT="parsable")


class NoInterference(output_file.OutputSandbox):
    """Result files and temporary data never change selection or lint results."""

    def test_selection_and_results_with_and_without_saving(self):
        scanned = os.pathsep.join((str(self.work), str(self.results)))
        for options, parameters in (
                (["--config-data", SELECT_ALL, "--list-files"],
                 dict(PARAM_CONFIG_DATA=SELECT_ALL, PARAM_LIST_FILES="true")),
                (["--config-data", SELECT_ALL, "--format", "parsable"],
                 dict(PARAM_CONFIG_DATA=SELECT_ALL, PARAM_FORMAT="parsable"))):
            with self.subTest(options=options):
                disabled = self.run_orb(PARAM_TARGETS=".", **parameters)
                destination = self.results / ("listing.txt" if "--list-files" in options else "lint.txt")
                enabled = self.run_orb(PARAM_TARGETS=".", PARAM_OUTPUT_FILE=str(destination),
                                       BODY_SCAN=scanned, **parameters)
                self.assertEqual((enabled.returncode, enabled.stdout, enabled.stderr),
                                 (disabled.returncode, disabled.stdout, disabled.stderr))
                self.require_saved(destination, enabled.stdout)
                scan = self.calls()[0]["scan"]
                during = [name for name in scan[str(self.results)]
                          if name.startswith(output_file.TEMPORARY_PREFIX)]
                self.assertEqual(len(during), 1, "temporary file exists while yamllint runs")
                self.assertFalse([name for name in scan[str(self.work)]
                                  if name.startswith(output_file.TEMPORARY_PREFIX)])
                self.assertNotIn(during[0].encode(), enabled.stdout)
                self.assertNotIn(destination.name.encode(), enabled.stdout)
                self.require_no_temporaries()
                # A second, different destination: the first result is not linted.
                second = self.results / ("second-" + destination.name)
                again = self.run_orb(PARAM_TARGETS=".", PARAM_OUTPUT_FILE=str(second), **parameters)
                self.assertEqual((again.returncode, again.stdout), (disabled.returncode, disabled.stdout))


if __name__ == "__main__":
    unittest.main()
