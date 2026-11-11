#!/usr/bin/env python3
"""#5509 output_file destination checks: python3 .circleci/test-output-destination.py -v.

Reuses the #5508 child-process sandbox from test-output-file.py. Each refused
destination must exit 2 with an Orb diagnostic on stderr, write nothing to
stdout, never start the body and leave every entry unchanged (type, bytes,
mtime and link target), with no temporary data. Accepted destinations are
checked with real yamllint: the selection and lint results equal a run
without saving. Local runs are supplementary and never CircleCI evidence.

Order of refusals (recorded for #5509): the existing input refusals run first
(config_file with config_data, a standalone "-" target, an invalid strict
value), then output_file is checked, before yamllint is started.
"""

import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import unittest


spec = importlib.util.spec_from_file_location(
    "output_file", Path(__file__).with_name("test-output-file.py"))
output_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(output_file)
EXECUTE = output_file.EXECUTE
PREFIX = output_file.PREFIX
REJECTED = PREFIX + b"rejected: "
SELECT_ALL = 'extends: relaxed\nyaml-files: ["*"]\n'


class DestinationSandbox(output_file.OutputSandbox):
    def setUp(self):
        super().setUp()
        src = self.work / "src"
        (src / "deep").mkdir(parents=True)
        (src / "a.yml").write_text("---\nvalue: a\n")
        (src / "deep" / "b.yml").write_text("---\nvalue: b\n")
        (self.work / "nested").mkdir()
        (self.work / "outside").mkdir()
        (self.work / "alias").symlink_to("src")
        (self.work / "srclink").symlink_to("src")
        (src / "escape").symlink_to("../outside")  # a symlink inside a target directory
        self.existing = self.results / "existing.txt"
        self.existing.write_text("existing result\n")
        (self.results / "existing-dir").mkdir()
        (self.results / "existing-dir" / "child.txt").write_text("child\n")
        (self.results / "link-to-file").symlink_to(self.existing)
        (self.results / "link-to-dir").symlink_to(self.results / "existing-dir")
        (self.results / "broken-link").symlink_to(self.results / "missing-target.txt")
        os.mkfifo(self.results / "fifo")
        (self.work / "existing-relative.txt").write_text("existing relative\n")

    def state(self):
        """lstat-based snapshot; reads regular files only (never opens a FIFO)."""
        snapshot = {}
        for top in (self.work, self.results, self.home):
            for directory, names, files in os.walk(top):
                for name in names + files:
                    path = os.path.join(directory, name)
                    info = os.lstat(path)
                    item = [stat.S_IFMT(info.st_mode), info.st_size, info.st_mtime_ns]
                    if stat.S_ISLNK(info.st_mode):
                        item.append(os.readlink(path))
                    elif stat.S_ISREG(info.st_mode):
                        item.append(hashlib.sha256(Path(path).read_bytes()).hexdigest())
                    snapshot[os.path.relpath(path, self.base)] = item
        return snapshot

    def check_refused(self, value, wanted, script=EXECUTE, **parameters):
        before = self.state()
        result = self.run_orb(script, PARAM_OUTPUT_FILE=value, **parameters)
        label = f"{value!r} {parameters}"
        self.assertEqual(result.returncode, 2, f"{label}: {result.stderr!r}")
        self.assertIn(REJECTED, result.stderr, label)
        self.assertIn(wanted, result.stderr, label)
        self.assertEqual(result.stdout, b"", f"{label}: diagnostic or output on stdout")
        self.assertEqual(self.calls(), [], f"{label}: yamllint body was started")
        self.assertEqual(self.state(), before, f"{label}: an entry was created or changed")
        return result

    def check_accepted(self, value, targets, options=(), **parameters):
        """Save run equals a non-saving run with real yamllint; returns the result."""
        parameters = dict(PARAM_TARGETS="\n".join(targets), **parameters)
        destination = Path(value) if os.path.isabs(value) else self.work / value
        real_parent = os.path.realpath(destination.parent)
        scanned = list(dict.fromkeys((real_parent, os.path.realpath(self.work),
                                      os.path.realpath(self.results))))
        disabled = self.run_orb(**parameters)
        result = self.run_orb(PARAM_OUTPUT_FILE=value, BODY_SCAN=os.pathsep.join(scanned), **parameters)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (disabled.returncode, disabled.stdout, disabled.stderr), value)
        self.assertEqual(self.calls()[0]["argv"], [*options, "--", *targets])
        self.require_saved(destination, result.stdout)
        self.require_no_temporaries()
        # While yamllint runs, exactly one temporary file exists, next to the
        # real destination and outside every target directory.
        scan = self.calls()[0]["scan"]
        during = [(directory, name) for directory, names in scan.items() for name in names
                  if name.startswith(output_file.TEMPORARY_PREFIX)]
        self.assertEqual(len(during), 1, f"temporary data while yamllint runs: {during}")
        self.assertEqual(during[0][0], real_parent)
        for target in targets:
            if os.path.isdir(self.work / target):
                real_target = os.path.realpath(self.work / target)
                self.assertNotEqual(os.path.commonpath([real_parent, real_target]), real_target,
                                    "temporary data inside a target directory")
        return result

    def check_refusal_suite(self, script=EXECUTE):
        """Representative refusals for the fault-detection test."""
        self.check_refused(str(self.results / "a\nb.txt"), b"newline", script)
        self.check_refused(str(self.existing), b"already exists as a regular file", script)
        self.check_refused(str(self.results / "broken-link"), b"a broken symbolic link", script)
        self.check_refused(str(self.results / "missing" / "out.txt"), b"does not exist", script)
        self.check_refused("missing.yml", b"same path as the target", script,
                           PARAM_TARGETS="missing.yml")
        self.check_refused("conf.yml", b"same path as config_file", script,
                           PARAM_TARGETS="clean.yml", PARAM_CONFIG_FILE="conf.yml")
        self.check_refused("src/out.txt", b"inside the target directory", script, PARAM_TARGETS="src")
        self.check_refused("alias/out.txt", b"inside the target directory", script, PARAM_TARGETS="src")
        self.check_refused("src/out.txt", b"inside the target directory", script,
                           PARAM_TARGETS="srclink")


class InvalidDestination(DestinationSandbox):
    """AC1: newline/CR, existing entries and missing parents are refused first."""

    def test_newline_and_carriage_return(self):
        for value in (str(self.results / "a\nb.txt"), str(self.results / "a\rb.txt"),
                      str(self.results / "trailing.txt") + "\n", "\n", "\r"):
            with self.subTest(value=value):
                self.check_refused(value, b"must not contain a newline or carriage return")

    def test_existing_entries_of_every_kind(self):
        cases = ((self.existing, b"a regular file"), (self.results / "existing-dir", b"a directory"),
                 (self.results / "link-to-file", b"a symbolic link"),
                 (self.results / "link-to-dir", b"a symbolic link"),
                 (self.results / "broken-link", b"a broken symbolic link"),
                 (self.results / "fifo", b"a special file"))
        for path, kind in cases:
            with self.subTest(entry=path.name):
                self.check_refused(str(path), b"already exists as " + kind)
        self.assertFalse(os.path.lexists(self.results / "missing-target.txt"))
        before = os.lstat("/dev/null")
        self.check_refused("/dev/null", b"already exists as a special file")
        after = os.lstat("/dev/null")
        self.assertEqual((before.st_mode, before.st_rdev), (after.st_mode, after.st_rdev))
        self.check_refused("existing-relative.txt", b"already exists as a regular file",
                           PARAM_TARGETS="clean.yml")

    def test_missing_or_invalid_parent_is_not_created(self):
        cases = (("missing-dir/out.txt", b"does not exist and is not created"),
                 (str(self.results / "missing" / "out.txt"), b"does not exist and is not created"),
                 (str(self.results / "missing" / "deep" / "out.txt"), b"does not exist and is not created"),
                 (str(self.existing / "out.txt"), b"is not a directory"),
                 (str(self.results / "fifo" / "out.txt"), b"is not a directory"),
                 (str(self.results) + "/", b"does not name a file"),
                 (str(self.results / "new-dir") + "/", b"does not name a file"),
                 (".", b"does not name a file"), ("..", b"does not name a file"),
                 (str(self.results / "missing" / ".."), b"does not name a file"))
        for value, wanted in cases:
            with self.subTest(value=value):
                self.check_refused(value, wanted, PARAM_TARGETS="clean.yml")


class ConflictingDestination(DestinationSandbox):
    """AC2: compared by real path; spelling, `..` and symlinks cannot bypass it."""

    def test_same_path_as_a_target_file(self):
        absolute = str(self.work / "missing.yml")
        for targets in ("missing.yml", "./missing.yml", absolute, "clean.yml\nmissing.yml"):
            for value in ("missing.yml", "./missing.yml", absolute, "src/../missing.yml",
                          "alias/../missing.yml", "nested/../missing.yml"):
                with self.subTest(targets=targets, value=value):
                    self.check_refused(value, b"is the same path as the target", PARAM_TARGETS=targets)

    def test_same_path_as_config_file(self):
        absolute = str(self.work / "conf.yml")
        for config in ("conf.yml", "./conf.yml", absolute):
            for value in ("conf.yml", "./conf.yml", absolute, "src/../conf.yml", "alias/../conf.yml"):
                with self.subTest(config_file=config, value=value):
                    self.check_refused(value, b"is the same path as config_file",
                                       PARAM_TARGETS="clean.yml", PARAM_CONFIG_FILE=config)

    def test_inside_a_target_directory(self):
        absolute = str(self.work / "src")
        cases = (("src", "src/out.txt"), ("src", "src/deep/out.txt"), ("src", "./src/out.txt"),
                 ("src", absolute + "/out.txt"), ("src", "src/../src/out.txt"),
                 ("src", "nested/../src/out.txt"),
                 ("src", "alias/out.txt"), ("src", "alias/deep/out.txt"),  # intermediate symlink
                 (absolute, "src/out.txt"), ("./src/", "src/out.txt"), ("src/deep/..", "src/out.txt"),
                 ("clean.yml\nsrc", "src/out.txt"),
                 ("", "out.txt"), ("", "./nested/out.txt"), (".", str(self.work / "out.txt")),
                 ("", "src/../out.txt"))
        for targets, value in cases:
            with self.subTest(targets=targets, value=value):
                self.check_refused(value, b"is inside the target directory", PARAM_TARGETS=targets)

    def test_target_directory_that_is_itself_a_symlink(self):
        for value in ("src/out.txt", "srclink/out.txt", "alias/out.txt", str(self.work / "src" / "x.txt")):
            with self.subTest(value=value):
                self.check_refused(value, b"is inside the target directory", PARAM_TARGETS="srclink")

    def test_upstream_exclusions_do_not_relax_the_rule(self):
        configs = ('extends: relaxed\nignore: ["*.txt", "out*"]\n',
                   'extends: relaxed\nyaml-files: ["*.yml"]\n')
        for config in configs:
            with self.subTest(config_data=config):
                self.check_refused("src/out.txt", b"is inside the target directory",
                                   PARAM_TARGETS="src", PARAM_CONFIG_DATA=config)


class AcceptedDestination(DestinationSandbox):
    """AC3: accepted destinations do not change selection or results."""

    def test_symlink_inside_a_target_directory_is_resolved_not_walked(self):
        # src/escape -> ../outside: the real destination is outside the target.
        options = ["--config-data", SELECT_ALL, "--list-files"]
        for value in ("outside/listing.txt", "src/escape/listing-through-link.txt"):
            with self.subTest(value=value):
                result = self.check_accepted(value, ["src"], options, PARAM_CONFIG_DATA=SELECT_ALL,
                                             PARAM_LIST_FILES="true")
                listed = result.stdout.decode().splitlines()
                self.assertCountEqual(listed, ["src/a.yml", "src/deep/b.yml"])
                self.assertFalse(any("escape" in line for line in listed),
                                 "upstream does not walk symlinked directories")
        self.assertEqual(sorted(os.listdir(self.work / "outside")),
                         ["listing-through-link.txt", "listing.txt"])

    def test_current_directory_target_with_an_outside_destination(self):
        listing = ["--config-data", SELECT_ALL, "--list-files"]
        result = self.check_accepted(str(self.results / "list.txt"), ["."], listing,
                                     PARAM_CONFIG_DATA=SELECT_ALL, PARAM_LIST_FILES="true")
        self.assertIn("./clean.yml", result.stdout.decode().splitlines())
        self.assertNotIn(b"list.txt", result.stdout)
        self.assertNotIn(output_file.TEMPORARY_PREFIX.encode(), result.stdout)
        lint = ["--config-data", SELECT_ALL, "--format", "parsable"]
        result = self.check_accepted(str(self.results / "lint.txt"), ["."], lint,
                                     PARAM_CONFIG_DATA=SELECT_ALL, PARAM_FORMAT="parsable")
        self.assertNotIn(b"lint.txt", result.stdout)
        self.assertNotIn(output_file.TEMPORARY_PREFIX.encode(), result.stdout)

    def test_file_targets_with_a_destination_in_the_working_directory(self):
        options = ["--config-file", "settings file.yml", "--format", "standard"]
        self.check_accepted("lint result.txt", ["warning.yml", "src/a.yml"], options,
                            PARAM_CONFIG_FILE="settings file.yml", PARAM_FORMAT="standard")
        self.check_accepted("nested/relative.txt", ["warning.yml"], options[:2] + ["--format", "colored"],
                            PARAM_CONFIG_FILE="settings file.yml", PARAM_FORMAT="colored")


class ExistingRefusals(DestinationSandbox):
    """AC4: existing refusals keep their status and diagnostics and win first."""

    def test_existing_refusals_precede_output_file_checks(self):
        refusals = ((output_file.CONFLICT, dict(PARAM_CONFIG_FILE="settings file.yml",
                                                PARAM_CONFIG_DATA="relaxed")),
                    (output_file.DASH, dict(PARAM_TARGETS="-")),
                    (output_file.STRICT, dict(PARAM_STRICT="invalid")))
        destinations = (str(self.results / "new.txt"), str(self.existing),
                        str(self.results / "a\nb.txt"), "src/out.txt")
        for diagnostic, parameters in refusals:
            disabled = self.run_orb(**parameters)
            self.assertEqual(disabled.returncode, 2)
            for value in destinations:
                with self.subTest(diagnostic=diagnostic, value=value):
                    before = self.state()
                    result = self.run_orb(PARAM_OUTPUT_FILE=value, **parameters)
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (disabled.returncode, disabled.stdout, disabled.stderr))
                    self.assertIn(diagnostic, result.stderr)
                    self.assertEqual(self.diagnostics(result.stderr), [])
                    self.assertEqual(self.calls(), [])
                    self.assertEqual(self.state(), before)


class RefusalFaultDetection(DestinationSandbox):
    """AC5: the refusal checks reject broken implementations."""

    MUTANTS = {
        "unexpected success": ("    fi\n    exit 2\nfi\n\n# yamllint writes to a pipe",
                               "    fi\n    exit 0\nfi\n\n# yamllint writes to a pipe"),
        "different status": ("    fi\n    exit 2\nfi\n\n# yamllint writes to a pipe",
                             "    fi\n    exit 1\nfi\n\n# yamllint writes to a pipe"),
        "body started after refusal": ("    fi\n    exit 2\nfi\n\n# yamllint writes to a pipe",
                                       "    fi\nfi\n\n# yamllint writes to a pipe"),
        "diagnostic on stdout": ("        sys.stderr.write(PREFIX + message + \"\\n\")\n"
                                 "        sys.stderr.flush()\n",
                                 "        sys.stdout.write(PREFIX + message + \"\\n\")\n"
                                 "        sys.stdout.flush()\n"),
        "newline accepted": ("    if \"\\n\" in raw or \"\\r\" in raw:\n", "    if False:\n"),
        "broken symlink missed": ("    mode = os.lstat(path).st_mode\n", "    mode = os.stat(path).st_mode\n"),
        "existing file truncated": ("        return refuse(repr(raw) + \" already exists as \" + existing\n",
                                    "        return open(raw, \"w\").close() or refuse(repr(raw)"
                                    " + \" already exists as \" + existing\n"),
        "missing parent created": ("        return refuse(\"the parent directory \" + repr(parent)\n",
                                   "        return os.makedirs(parent) or refuse(\"the parent directory \""
                                   " + repr(parent)\n"),
        "target compared without symlinks": ("        real_target = os.path.realpath(target)\n",
                                             "        real_target = os.path.abspath(target)\n"),
        "destination compared without symlinks": (
            "    return os.path.join(os.path.realpath(parent), tail)\n",
            "    return os.path.join(os.path.abspath(parent), tail)\n"),
        "target directory not checked": (
            "        if os.path.isdir(target) and inside(destination, real_target):\n", "        if False:\n"),
        "target file not checked": ("        if destination == real_target:\n", "        if False:\n"),
        "config file not checked": (
            "    if config_file and destination == os.path.realpath(config_file):\n", "    if False:\n"),
    }

    def test_checks_reject_broken_refusals(self):
        source = EXECUTE.read_text()
        mutated = self.base / "mutated-execute.sh"
        for name, (original, replacement) in self.MUTANTS.items():
            with self.subTest(mutant=name):
                self.assertEqual(source.count(original), 1, f"{name}: locate the code to mutate")
                mutated.write_text(source.replace(original, replacement, 1))
                with self.assertRaises(AssertionError):
                    self.check_refusal_suite(mutated)
                self.tearDown_mutant()

    def tearDown_mutant(self):
        """Undo what a broken implementation may have created."""
        for path in (self.results / "a\nb.txt", self.work / "missing.yml", self.work / "conf.yml",
                     self.work / "src" / "out.txt"):
            if os.path.lexists(path) and not os.path.isdir(path):
                path.unlink()
        missing = self.results / "missing"
        if missing.is_dir():
            for directory, names, files in os.walk(missing, topdown=False):
                for name in files:
                    os.unlink(os.path.join(directory, name))
                os.rmdir(directory)
        self.existing.write_text("existing result\n")
        for name in os.listdir(self.results):
            if name.startswith(output_file.TEMPORARY_PREFIX):
                os.unlink(self.results / name)


if __name__ == "__main__":
    unittest.main()
