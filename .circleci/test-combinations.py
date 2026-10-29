#!/usr/bin/env python3
"""Phase 5 combinations using the unchanged Phase 4 real-upstream recorder."""
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("phase4", Path(__file__).with_name("test-list-files.py"))
phase4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase4)
WARNING_CONFIG = "extends: default\nrules:\n  line-length:\n    max: 20\n    level: warning\n"


class Combinations(phase4.ListFiles):
    def test_listing_no_warnings_strict_format_and_settings(self):
        expected = ["fixtures/keep.yml", "fixtures/drop.yml", "fixtures/sub/keep.yml"]
        for mode in ("file", "data"):
            config = ["--config-file", "settings file.yml"] if mode == "file" else [
                "--config-data", phase4.CONFIG]
            parameters = dict(PARAM_CONFIG_FILE="settings file.yml") if mode == "file" else dict(
                PARAM_CONFIG_DATA=phase4.CONFIG)
            for strict in (False, True):
                for no_warnings in (False, True):
                    for fmt in ("standard", "parsable"):
                        with self.subTest(mode=mode, strict=strict, no_warnings=no_warnings, format=fmt):
                            options = config + (["--strict"] if strict else [])
                            options += ["--no-warnings"] if no_warnings else []
                            options += ["--format", fmt, "--list-files"]
                            result = self.compare(options, PARAM_STRICT=str(strict).lower(),
                                                  PARAM_NO_WARNINGS=str(no_warnings).lower(),
                                                  PARAM_FORMAT=fmt, **parameters)
                            self.require_listing(result, expected)

    def test_warning_display_with_strict_format_data_and_literal_targets(self):
        targets = ("--warning.yml", "space warning.yml")
        for target in targets:
            (self.cwd / target).write_text('---\nmessage: "' + 'word ' * 10 + '"\n')
        (self.cwd / "settings file.yml").write_text(WARNING_CONFIG)
        for mode in ("file", "data"):
            self.check_warning_combination(mode, targets)

    def check_warning_combination(self, mode, targets):
        for strict in (False, True):
            for no_warnings in (False, True):
                for fmt in ("standard", "parsable"):
                    with self.subTest(mode=mode, strict=strict, no_warnings=no_warnings, format=fmt):
                        options = ["--config-file", "settings file.yml"] if mode == "file" else [
                            "--config-data", WARNING_CONFIG]
                        parameters = dict(PARAM_CONFIG_FILE="settings file.yml") if mode == "file" else dict(
                            PARAM_CONFIG_DATA=WARNING_CONFIG)
                        options += ["--strict"] if strict else []
                        options += ["--no-warnings"] if no_warnings else []
                        options += ["--format", fmt]
                        result = self.compare(options, targets, **parameters,
                                              PARAM_STRICT=str(strict).lower(), PARAM_FORMAT=fmt,
                                              PARAM_NO_WARNINGS=str(no_warnings).lower(), PARAM_LIST_FILES="false")
                        self.assertEqual(result.returncode, 2 if strict else 0)
                        self.assertEqual(result.stderr, "")
                        if no_warnings:
                            self.assertEqual(result.stdout, "")
                        else:
                            for target in targets:
                                self.assertIn(target, result.stdout)
                            self.assertEqual(result.stdout.count("line-length"), 2)
                            if fmt == "parsable":
                                self.assertEqual(result.stdout.count("[warning]"), 2)

    def test_all_new_parameters_unset_keep_existing_configuration(self):
        for name in ("PARAM_CONFIG_DATA", "PARAM_NO_WARNINGS", "PARAM_LIST_FILES"):
            self.env.pop(name, None)
        (self.cwd / "settings file.yml").write_text(WARNING_CONFIG)
        (self.cwd / "warning.yml").write_text('---\nmessage: "' + 'word ' * 10 + '"\n')
        for strict in (False, True):
            for fmt in ("standard", "parsable"):
                with self.subTest(strict=strict, format=fmt):
                    options = ["--config-file", "settings file.yml"]
                    options += ["--strict"] if strict else []
                    options += ["--format", fmt]
                    result = self.compare(options, ("warning.yml",), PARAM_CONFIG_FILE="settings file.yml",
                                          PARAM_STRICT=str(strict).lower(), PARAM_FORMAT=fmt)
                    self.assertEqual(result.returncode, 2 if strict else 0)
                    self.assertIn("line-length", result.stdout)


if __name__ == "__main__":
    # Run only Phase 5 additions; the inherited Phase 4 suite is run separately.
    unittest.main(defaultTest=[
        "Combinations.test_listing_no_warnings_strict_format_and_settings",
        "Combinations.test_warning_display_with_strict_format_data_and_literal_targets",
        "Combinations.test_all_new_parameters_unset_keep_existing_configuration",
    ])
