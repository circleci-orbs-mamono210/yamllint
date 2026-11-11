#!/usr/bin/env python3
"""#5508 output_file checks: python3 .circleci/test-output-file.py -v.

Every case runs the real src/scripts/execute.sh as a child process from a
temporary working directory outside this repository. The parent checks the
Orb's exit status, stdout, stderr, created entries and body calls. Real
yamllint 1.37.1 or 1.38.0 must be importable by this Python; otherwise the
suite fails. A stand-in replaces the body only where a case needs fixed bytes
or statuses, streaming control or a race. It never turns a non-zero status
into success, and its cases are named separately from real-yamllint cases.

Faults are real OS failures: RLIMIT_FSIZE for result writes, /dev/full and a
closed pipe for the step log. Run as a non-root user, because one check needs
directory permission bits, which root ignores. Local runs are supplementary
and never CircleCI evidence; #5510 adds these checks to the fixed matrix.
"""

import errno
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import pty
import resource
import select
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXECUTE = ROOT / "src/scripts/execute.sh"
BASH = shutil.which("bash")
PREFIX = b"yamllint Orb: output_file: "
TEMPORARY_PREFIX = ".yamllint-orb-output-"
SAVE_LIMIT = 4096  # RLIMIT_FSIZE in bytes; every saving payload is larger.
WARNING_CONFIG = "extends: default\nrules:\n  line-length:\n    max: 20\n    level: warning\n"
LIST_CONFIG = 'extends: relaxed\nyaml-files: ["*.yml", "*.yaml"]\n'
CONFLICT = b"yamllint Orb: config_file and config_data cannot both be non-empty."
DASH = b"yamllint Orb: standalone '-' is not supported in targets; use './-' for a file named '-'."
STRICT = b"Invalid strict value: invalid"
# Bytes a body may legitimately print: CR, NUL, invalid UTF-8, ANSI colors
# and no final newline. Larger than SAVE_LIMIT and the 64 KiB relay chunk.
PAYLOAD = (b"first line\r\n\x00 nul\xff\xfe invalid utf-8\n\x1b[31mred\x1b[0m\rcarriage\n"
           + b"".join(b"line %05d of a long body output\n" % i for i in range(2600))
           + b"no final newline")
BODY_STDERR = b"body diagnostic on stderr\n"

# Body stand-in, installed as "yamllint" on PATH. It first records argv and
# its own stdout connection (without writing to stdout), then either execs
# real yamllint unchanged or runs one controlled behavior.
BODY = r'''import json, os, stat, sys, time
info = os.fstat(1)
record = {"argv": sys.argv[1:], "isatty": os.isatty(1), "type": stat.S_IFMT(info.st_mode),
          "id": [info.st_dev, info.st_ino, info.st_rdev]}
if os.environ.get("BODY_SCAN"):
    record["scan"] = {d: sorted(os.listdir(d)) for d in os.environ["BODY_SCAN"].split(os.pathsep)}
with open(os.environ["BODY_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(record) + "\n")
mode = os.environ.get("BODY_MODE", "real")
if mode == "real":
    os.execv(sys.executable, [sys.executable, "-m", "yamllint", *sys.argv[1:]])
compete = os.environ.get("BODY_COMPETE")
if compete:
    kind = os.environ["BODY_COMPETE_KIND"]
    if kind == "file":
        with open(compete, "x") as handle:
            handle.write("competitor\n")
    elif kind == "directory":
        os.mkdir(compete)
    else:
        os.symlink(os.environ["BODY_COMPETE_TARGET"], compete)
if os.environ.get("BODY_LOCK"):
    os.chmod(os.environ["BODY_LOCK"], 0o555)
if os.environ.get("BODY_REMOVE_TEMPORARY"):
    directory = os.environ["BODY_REMOVE_TEMPORARY"]
    for name in os.listdir(directory):
        if name.startswith(".yamllint-orb-output-"):
            os.unlink(os.path.join(directory, name))
def emit(variable, stream):
    if os.environ.get(variable):
        with open(os.environ[variable], "rb") as handle:
            data = handle.read()
        for start in range(0, len(data), 4096):
            stream.write(data[start:start + 4096])
            stream.flush()
emit("BODY_STDOUT", sys.stdout.buffer)
emit("BODY_STDERR", sys.stderr.buffer)
if mode == "stream":
    sys.stdout.buffer.write(b"first chunk\n")
    sys.stdout.buffer.flush()
    deadline = time.monotonic() + 30
    while not os.path.exists(os.environ["BODY_RELEASE"]):
        if time.monotonic() > deadline:
            sys.exit(99)
        time.sleep(0.02)
    sys.stdout.buffer.write(b"second chunk\n")
    sys.stdout.buffer.flush()
sys.exit(int(os.environ.get("BODY_STATUS", "0")))
'''


class OutputSandbox(unittest.TestCase):
    """Shared child-process sandbox; it defines no test methods itself."""

    announced = False

    @classmethod
    def setUpClass(cls):
        cls.version = importlib.metadata.version("yamllint")
        if cls.version not in ("1.37.1", "1.38.0"):
            raise RuntimeError("Run this suite with yamllint 1.37.1 or 1.38.0")
        if not BASH:
            raise RuntimeError("bash is required")
        if not OutputSandbox.announced:
            OutputSandbox.announced = True
            print(f"Real upstream: yamllint {cls.version}; Python {sys.version.split()[0]}; "
                  f"euid {os.geteuid()}", flush=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="yamllint-output-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.work = self.base / "work"        # the Orb's working directory
        self.results = self.base / "results"  # destinations outside the work tree
        self.home = self.base / "home"
        self.bin = self.base / "bin"
        for directory in (self.work, self.results, self.home, self.bin):
            directory.mkdir()
        body = self.bin / "yamllint"
        body.write_text(f"#!{sys.executable}\n" + BODY, encoding="utf-8")
        body.chmod(0o755)
        (self.bin / "python3").symlink_to(sys.executable)
        self.log = self.base / "calls.jsonl"
        self.payload_file = self.base / "payload.bin"
        self.payload_file.write_bytes(PAYLOAD)
        self.stderr_file = self.base / "stderr.bin"
        self.stderr_file.write_bytes(BODY_STDERR)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("PARAM_", "BODY_")) and key not in (
                        "BASH_ENV", "ENV", "CDPATH", "YAMLLINT_CONFIG_FILE",
                        "GITHUB_ACTIONS", "GITHUB_WORKFLOW")}
        self.env.update(
            PATH=f"{self.bin}{os.pathsep}{self.env.get('PATH', '')}", HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.base / "xdg"), BODY_LOG=str(self.log), BODY_MODE="real",
            PARAM_TARGETS="", PARAM_CONFIG_FILE="", PARAM_CONFIG_DATA="", PARAM_STRICT="false",
            PARAM_NO_WARNINGS="false", PARAM_LIST_FILES="false", PARAM_FORMAT="",
            PARAM_OUTPUT_FILE="",
        )
        long_line = 'message: "' + "word " * 10 + '"'
        fixtures = {
            "clean.yml": "---\nmessage: clean\n",
            "warning.yml": "---\n" + long_line + "\n",
            "error.yml": "---\nmessage: error  \n",
            "-leading.yml": "---\n" + long_line + "\n",
            "日本語 ファイル.yml": "---\nメッセージ: " + "とても長い日本語の値です" * 3 + "\n",
            "long-error.yml": "---\n" + "".join(f"key{i:04d}: value  \n" for i in range(3000)),
            "long-warning.yml": "---\n" + "".join(f"key{i:04d}: {'word ' * 6}end\n" for i in range(3000)),
            "settings file.yml": WARNING_CONFIG,
            "listing/keep.yml": "---\nvalue: 1\n",
            "listing/sub/also.yaml": "---\nvalue: 2\n",
            "listing/note.txt": "not yaml\n",
        }
        for name, content in fixtures.items():
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    # --- running -----------------------------------------------------------

    def environment(self, parameters):
        merged = {**self.env, **parameters}
        return {key: value for key, value in merged.items() if value is not None}

    def run_orb(self, script=EXECUTE, stdout=subprocess.PIPE, limit=None, timeout=60, **parameters):
        """Run the script once; a None parameter value removes that variable."""
        self.log.unlink(missing_ok=True)

        def limit_file_size():
            resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))

        return subprocess.run(
            [BASH, str(script)], cwd=self.work, env=self.environment(parameters),
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.PIPE,
            preexec_fn=limit_file_size if limit is not None else None,
            timeout=timeout, check=False)

    def run_on_terminal(self, script=EXECUTE, **parameters):
        """Run with stdout on a pseudo-terminal; return status, terminal bytes, stderr."""
        self.log.unlink(missing_ok=True)
        master, slave = pty.openpty()
        try:
            process = subprocess.Popen(
                [BASH, str(script)], cwd=self.work, env=self.environment(parameters),
                stdin=subprocess.DEVNULL, stdout=slave, stderr=subprocess.PIPE)
        finally:
            os.close(slave)
        output = bytearray()
        deadline = time.monotonic() + 60
        try:
            while True:
                if time.monotonic() > deadline:
                    process.kill()
                    raise AssertionError("terminal run did not finish")
                ready, _, _ = select.select([master], [], [], 0.2)
                if not ready:
                    continue
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:  # EIO: every slave side is closed
                        raise
                    data = b""
                if not data:
                    break
                output += data
            stderr = process.stderr.read()
            process.wait(timeout=20)
        finally:
            os.close(master)
            process.stderr.close()
        return process.returncode, bytes(output), stderr

    def direct(self, argv):
        """The upstream CLI with a non-terminal stdout, as a comparison."""
        return subprocess.run([sys.executable, "-m", "yamllint", *argv], cwd=self.work,
                              env=self.environment({}), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=60, check=False)

    # --- observations ------------------------------------------------------

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def entries(self):
        """Every entry (lstat, including symlinks) below work, results and home."""
        found = set()
        for top in (self.work, self.results, self.home):
            for directory, names, files in os.walk(top):
                for name in names + files:
                    found.add(os.path.relpath(os.path.join(directory, name), self.base))
        return found

    def temporaries(self):
        return sorted(entry for entry in self.entries()
                      if os.path.basename(entry).startswith(TEMPORARY_PREFIX))

    @staticmethod
    def diagnostics(result_stderr):
        return [line for line in result_stderr.splitlines() if line.startswith(PREFIX)]

    def require_saved(self, destination, expected):
        self.assertTrue(destination.is_file() and not destination.is_symlink(),
                        f"result file missing: {destination}")
        self.assertEqual(destination.read_bytes(), expected, "saved bytes differ from stdout")

    def require_unsaved(self, destination):
        self.assertFalse(os.path.lexists(destination), f"unexpected result entry: {destination}")

    def require_no_temporaries(self):
        self.assertEqual(self.temporaries(), [], "temporary data was left behind")

    def require_not_started(self, result, before, diagnostic):
        """Refusal before the body: status 2, stderr diagnostic only, nothing created."""
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn(diagnostic, result.stderr)
        self.assertEqual(result.stdout, b"", "refusal wrote to stdout")
        self.assertEqual(self.calls(), [], "yamllint body was started")
        self.assertEqual(self.entries(), before, "entries changed although nothing was run")


class SaveChecks(OutputSandbox):
    """Reusable checks; each raises AssertionError when the script is wrong."""

    REAL_CASES = (
        ("success without output", [], ["clean.yml"], {}, 0),
        ("non-strict warning", ["--config-file", "settings file.yml"], ["warning.yml"],
         dict(PARAM_CONFIG_FILE="settings file.yml"), 0),
        ("strict warning", ["--config-file", "settings file.yml", "--strict", "--format", "parsable"],
         ["warning.yml"], dict(PARAM_CONFIG_FILE="settings file.yml", PARAM_STRICT="true",
                               PARAM_FORMAT="parsable"), 2),
        ("error", ["--format", "parsable"], ["error.yml"], dict(PARAM_FORMAT="parsable"), 1),
        ("hidden strict warning, empty", ["--config-data", WARNING_CONFIG, "--strict", "--no-warnings",
                                          "--format", "parsable"], ["warning.yml"],
         dict(PARAM_CONFIG_DATA=WARNING_CONFIG, PARAM_STRICT="1", PARAM_NO_WARNINGS="1",
              PARAM_FORMAT="parsable"), 2),
        ("list_files", ["--config-data", LIST_CONFIG, "--list-files"], ["listing"],
         dict(PARAM_CONFIG_DATA=LIST_CONFIG, PARAM_LIST_FILES="true"), 0),
        ("multiple, hyphen and non-ASCII targets", ["--config-file", "settings file.yml", "--format", "standard"],
         ["-leading.yml", "warning.yml", "日本語 ファイル.yml"],
         dict(PARAM_CONFIG_FILE="settings file.yml", PARAM_FORMAT="standard"), 0),
        ("long output", ["--format", "parsable"], ["long-error.yml"], dict(PARAM_FORMAT="parsable"), 1),
        ("explicit colored", ["--format", "colored"], ["error.yml"], dict(PARAM_FORMAT="colored"), 1),
        ("explicit github", ["--format", "github"], ["error.yml"], dict(PARAM_FORMAT="github"), 1),
        ("explicit auto", ["--format", "auto"], ["error.yml"], dict(PARAM_FORMAT="auto"), 1),
        ("default format", [], ["error.yml"], {}, 1),
        ("stderr only, missing target", [], ["missing.yml"], {}, 255),
    )

    def check_real_case(self, case, script=EXECUTE):
        name, options, targets, parameters, status = case
        argv = [*options, "--", *targets]
        direct = self.direct(argv)
        self.assertEqual(direct.returncode, status, f"{name}: fixture control {direct!r}")
        destination = self.results / ("real " + name + ".txt")
        result = self.run_orb(script, PARAM_TARGETS="\n".join(targets),
                              PARAM_OUTPUT_FILE=str(destination), **parameters)
        self.assertEqual(self.calls()[0]["argv"] if self.calls() else None, argv, f"{name}: body argv")
        self.assertEqual(len(self.calls()), 1, f"{name}: expected one body call")
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (direct.returncode, direct.stdout, direct.stderr), name)
        self.require_saved(destination, result.stdout)
        if direct.stderr:
            self.assertNotIn(direct.stderr.strip(), destination.read_bytes())
        self.assertNotIn(b"yamllint " + self.version.encode(), destination.read_bytes())
        self.require_no_temporaries()
        return result

    def check_bytes_case(self, status, script=EXECUTE):
        destination = self.results / f"bytes-{status}.txt"
        result = self.run_orb(script, BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                              BODY_STDERR=str(self.stderr_file), BODY_STATUS=str(status),
                              PARAM_TARGETS="clean.yml", PARAM_OUTPUT_FILE=str(destination))
        self.assertEqual(result.returncode, status, result.stderr)
        self.assertEqual(result.stdout, PAYLOAD)
        self.assertEqual(result.stderr, BODY_STDERR, "stderr changed or Orb diagnostics added")
        self.require_saved(destination, PAYLOAD)
        self.assertNotIn(BODY_STDERR.strip(), destination.read_bytes())
        self.assertEqual(len(self.calls()), 1)
        self.require_no_temporaries()

    def run_fault(self, body_status, fault, script=EXECUTE, destination=None):
        destination = destination or self.results / f"fault-{body_status}-{fault}.txt"
        parameters = dict(BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                          BODY_STATUS=str(body_status), PARAM_TARGETS="clean.yml",
                          PARAM_OUTPUT_FILE=str(destination))
        limit = SAVE_LIMIT if fault in ("save", "both") else None
        if fault in ("log", "both"):
            with open("/dev/full", "wb") as full:
                return destination, self.run_orb(script, stdout=full, limit=limit, **parameters)
        if fault == "closed log":
            reader, writer = os.pipe()
            os.close(reader)
            try:
                return destination, self.run_orb(script, stdout=writer, **parameters)
            finally:
                os.close(writer)
        return destination, self.run_orb(script, limit=limit, **parameters)

    def check_fault(self, body_status, fault, script=EXECUTE):
        destination, result = self.run_fault(body_status, fault, script)
        failed = fault != "none"
        expected = body_status if body_status else (2 if failed else 0)
        label = f"body {body_status}, fault {fault}"
        self.assertEqual(result.returncode, expected, f"{label}: {result.stderr!r}")
        self.assertEqual(len(self.calls()), 1, label)
        diagnostics = self.diagnostics(result.stderr)
        if fault == "none":
            self.assertEqual((result.stdout, result.stderr), (PAYLOAD, b""), label)
        if fault in ("save", "both"):
            self.require_unsaved(destination)
            self.assertTrue(any(b"could not write" in line for line in diagnostics), label)
            self.assertTrue(any(b"was not created" in line for line in diagnostics), label)
        else:
            self.require_saved(destination, PAYLOAD)
        if fault == "save":
            self.assertEqual(result.stdout, PAYLOAD, f"{label}: log incomplete after save failure")
        if fault in ("log", "both", "closed log"):
            self.assertTrue(any(b"step log" in line for line in diagnostics), label)
        self.require_no_temporaries()

    def check_conflict(self, kind, body_status=0, script=EXECUTE):
        destination = self.results / f"conflict-{kind}-{body_status}"
        link_target = self.results / f"link-target-{kind}-{body_status}.txt"
        if kind == "symlink":
            link_target.write_text("link target\n")
        result = self.run_orb(script, BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                              BODY_STATUS=str(body_status), BODY_COMPETE=str(destination),
                              BODY_COMPETE_KIND=kind, BODY_COMPETE_TARGET=str(link_target),
                              PARAM_TARGETS="clean.yml", PARAM_OUTPUT_FILE=str(destination))
        self.assertEqual(result.returncode, body_status or 2, result.stderr)
        self.assertEqual(result.stdout, PAYLOAD, "log forwarding must not depend on finalization")
        self.assertTrue(any(b"appeared while yamllint was running" in line
                            for line in self.diagnostics(result.stderr)), result.stderr)
        if kind == "file":
            self.assertEqual(destination.read_text(), "competitor\n")
        elif kind == "directory":
            self.assertTrue(destination.is_dir() and not destination.is_symlink())
            self.assertEqual(list(destination.iterdir()), [])
        else:
            self.assertEqual(os.readlink(destination), str(link_target))
            if kind == "symlink":
                self.assertEqual(link_target.read_text(), "link target\n")
            else:
                self.assertFalse(os.path.lexists(link_target), "broken link target was created")
        self.require_no_temporaries()

    def check_streaming(self, script=EXECUTE, wait=5.0):
        release = self.base / "release"
        destination = self.results / "streamed.txt"
        self.log.unlink(missing_ok=True)
        process = subprocess.Popen(
            [BASH, str(script)], cwd=self.work,
            env=self.environment(dict(BODY_MODE="stream", BODY_RELEASE=str(release),
                                      PARAM_TARGETS="clean.yml",
                                      PARAM_OUTPUT_FILE=str(destination))),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        early = b""
        try:
            deadline = time.monotonic() + wait
            while b"first chunk\n" not in early and time.monotonic() < deadline:
                ready, _, _ = select.select([process.stdout], [], [], 0.05)
                if ready:
                    data = os.read(process.stdout.fileno(), 65536)
                    if not data:
                        break
                    early += data
            running = process.poll() is None
        finally:
            # Always release the controlled body, then bound the wait.
            release.write_text("release\n")
            try:
                rest, stderr = process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise AssertionError("controlled body did not finish after release")
        self.assertTrue(running, "the Orb finished while the body was still held")
        self.assertEqual(early, b"first chunk\n",
                         "flushed body output was not forwarded before the body finished")
        self.assertEqual((process.returncode, stderr), (0, b""))
        self.assertEqual(early + rest, b"first chunk\nsecond chunk\n")
        self.require_saved(destination, b"first chunk\nsecond chunk\n")

    def check_non_blocking_log(self, script=EXECUTE):
        """A full non-blocking step stdout (EAGAIN) is waited for, not a log failure."""
        reader, writer = os.pipe()
        fcntl.fcntl(writer, getattr(fcntl, "F_SETPIPE_SZ", 1031), 4096)
        os.set_blocking(writer, False)
        destination = self.results / "non-blocking.txt"
        self.log.unlink(missing_ok=True)
        try:
            process = subprocess.Popen(
                [BASH, str(script)], cwd=self.work,
                env=self.environment(dict(BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                                          PARAM_TARGETS="clean.yml",
                                          PARAM_OUTPUT_FILE=str(destination))),
                stdin=subprocess.DEVNULL, stdout=writer, stderr=subprocess.PIPE)
        finally:
            os.close(writer)
        received = bytearray()
        with os.fdopen(reader, "rb") as stream:
            time.sleep(1.0)  # the relay fills the small pipe and meets EAGAIN
            for chunk in iter(lambda: stream.read(65536), b""):
                received += chunk
        stderr = process.stderr.read()
        process.stderr.close()
        process.wait(timeout=60)
        self.assertEqual((process.returncode, stderr), (0, b""))
        self.assertEqual(bytes(received), PAYLOAD)
        self.require_saved(destination, PAYLOAD)

    def check_terminal(self, script=EXECUTE):
        lines = b"one\ntwo\n"
        lines_file = self.base / "lines.bin"
        lines_file.write_bytes(lines)
        common = dict(BODY_MODE="emit", BODY_STDOUT=str(lines_file), PARAM_TARGETS="clean.yml")
        status, shown, stderr = self.run_on_terminal(script, **common)
        self.assertEqual((status, stderr), (0, b""))
        disabled = self.calls()[0]
        self.assertTrue(disabled["isatty"], "disabled saving must keep the terminal")
        self.assertEqual(stat.S_IFMT(disabled["type"]), stat.S_IFCHR)
        self.assertEqual(shown, b"one\r\ntwo\r\n")
        destination = self.results / "terminal.txt"
        status, shown, stderr = self.run_on_terminal(script, PARAM_OUTPUT_FILE=str(destination), **common)
        self.assertEqual((status, stderr), (0, b""))
        enabled = self.calls()[0]
        self.assertFalse(enabled["isatty"], "body stdout must not be a terminal when saving")
        self.assertEqual(stat.S_IFMT(enabled["type"]), stat.S_IFIFO, "body stdout must be a pipe")
        self.assertEqual(shown, b"one\r\ntwo\r\n", "the step log shows the forwarded bytes")
        self.require_saved(destination, lines)  # no terminal newline conversion in the file

    INTERPRETED = ("with space.txt", "quote \" and ' marks.txt", "日本語の結果.txt",
                   "-leading-hyphen.txt", "  padded both  .txt", " leading.txt", "trailing.txt ",
                   "$HOME.txt", "${HOME}.txt", "$(touch injected).txt", "`touch injected`.txt",
                   "*.txt", "[ab]?.txt", "~")

    def check_interpretation(self, script=EXECUTE):
        for directory in ("~", "$HOME", "sub dir"):
            (self.work / directory).mkdir()
        (self.results / "a.txt").write_text("existing\n")
        cases = [(str(self.results / name), self.results / name) for name in self.INTERPRETED]
        cases += [("~/home-like.txt", self.work / "~" / "home-like.txt"),
                  ("$HOME/variable-like.txt", self.work / "$HOME" / "variable-like.txt"),
                  ("sub dir/relative.txt", self.work / "sub dir" / "relative.txt"),
                  ("relative.txt", self.work / "relative.txt"),
                  ("../results/parent-relative.txt", self.results / "parent-relative.txt")]
        for value, expected in cases:
            before = self.entries()
            result = self.run_orb(script, PARAM_TARGETS="warning.yml",
                                  PARAM_CONFIG_FILE="settings file.yml", PARAM_OUTPUT_FILE=value)
            self.assertEqual(result.returncode, 0, f"{value!r}: {result.stderr!r}")
            self.assertTrue(result.stdout, "fixture must produce output")
            self.assertEqual(self.entries() - before, {os.path.relpath(expected, self.base)},
                             f"{value!r} created other entries")
            self.assertEqual(before - self.entries(), set())
            self.require_saved(expected, result.stdout)
        self.assertEqual((self.results / "a.txt").read_text(), "existing\n")
        self.assertEqual(list(self.home.iterdir()), [], "a path was expanded into HOME")
        self.assertFalse(list(self.base.rglob("injected")), "shell text was executed")


class PublicParameter(SaveChecks):
    def test_public_parameter_and_source_wiring(self):
        command = yaml.safe_load((ROOT / "src/commands/execute.yml").read_text())
        parameter = command["parameters"]["output_file"]
        self.assertEqual((parameter["type"], parameter["default"]), ("string", ""))
        steps = [step["run"] for step in command["steps"] if "run" in step]
        execution = [step for step in steps if step["command"] == "<<include(scripts/execute.sh)>>"]
        self.assertEqual(len(execution), 1)
        self.assertEqual(execution[0]["environment"]["PARAM_OUTPUT_FILE"],
                         "<< parameters.output_file >>")


class SavingDisabled(SaveChecks):
    """AC1: unset or empty output_file keeps the existing behavior."""

    def test_stdout_connection_status_and_files_are_unchanged(self):
        argv = ["--config-file", "settings file.yml", "--format", "parsable", "--", "warning.yml"]
        direct = self.direct(argv)
        for value in (None, ""):
            with self.subTest(output_file=value), tempfile.TemporaryFile() as stdout:
                before = self.entries()
                result = self.run_orb(stdout=stdout, PARAM_TARGETS="warning.yml", PARAM_FORMAT="parsable",
                                      PARAM_CONFIG_FILE="settings file.yml", PARAM_OUTPUT_FILE=value)
                stdout.seek(0)
                self.assertEqual((result.returncode, stdout.read(), result.stderr),
                                 (direct.returncode, direct.stdout, direct.stderr))
                record = self.calls()
                self.assertEqual(len(record), 1)
                self.assertEqual(record[0]["argv"], argv)
                info = os.fstat(stdout.fileno())
                # The body writes to the very file the Orb received: no relay.
                self.assertEqual(record[0]["id"][:2], [info.st_dev, info.st_ino])
                self.assertEqual(self.entries(), before)

    def test_statuses_and_stderr_pass_through_without_python3(self):
        only_body = self.base / "only-body"
        only_body.mkdir()
        shutil.copy2(self.bin / "yamllint", only_body / "yamllint")
        for status in (0, 1, 2, 17):
            with self.subTest(status=status):
                before = self.entries()
                result = self.run_orb(PATH=str(only_body), BODY_MODE="emit", BODY_STATUS=str(status),
                                      BODY_STDOUT=str(self.payload_file), BODY_STDERR=str(self.stderr_file),
                                      PARAM_TARGETS="clean.yml")
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (status, PAYLOAD, BODY_STDERR))
                self.assertEqual(self.entries(), before)

    def test_disabled_real_cases_match_upstream(self):
        for case in self.REAL_CASES:
            name, options, targets, parameters, status = case
            with self.subTest(case=name):
                direct = self.direct([*options, "--", *targets])
                result = self.run_orb(PARAM_TARGETS="\n".join(targets), **parameters)
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (direct.returncode, direct.stdout, direct.stderr))
                self.require_no_temporaries()


class SavingEnabled(SaveChecks):
    """AC2: the saved file and the Orb stdout are byte-identical."""

    def test_real_yamllint_cases(self):
        for case in self.REAL_CASES:
            with self.subTest(case=case[0]):
                result = self.check_real_case(case)
                if case[0] == "explicit colored":
                    self.assertIn(b"\x1b[", result.stdout)
                if case[0] in ("explicit auto", "default format"):
                    self.assertNotIn(b"\x1b[", result.stdout, "auto must see a non-terminal")
                if case[0] == "long output":
                    self.assertGreater(len(result.stdout), 3 * 65536)

    def test_stand_in_bytes_and_statuses(self):
        for status in (0, 1, 2, 17):
            with self.subTest(status=status):
                self.check_bytes_case(status)

    def test_output_file_is_a_literal_path(self):
        self.check_interpretation()


class StreamingAndConnection(SaveChecks):
    """AC3: a pipe (not a terminal) and forwarding before the body ends."""

    def test_body_stdout_is_a_pipe_only_when_saving(self):
        self.check_terminal()

    def test_auto_format_follows_the_connection(self):
        status, shown, _ = self.run_on_terminal(PARAM_TARGETS="error.yml")
        self.assertEqual(status, 1)
        self.assertIn(b"\x1b[", shown, "disabled saving keeps upstream terminal detection")
        destination = self.results / "auto.txt"
        status, shown, _ = self.run_on_terminal(PARAM_TARGETS="error.yml",
                                                PARAM_OUTPUT_FILE=str(destination))
        self.assertEqual(status, 1)
        self.assertEqual(destination.read_bytes(), self.direct(["--", "error.yml"]).stdout)
        self.assertNotIn(b"\x1b[", destination.read_bytes())
        colored = self.results / "colored.txt"
        status, _, _ = self.run_on_terminal(PARAM_TARGETS="error.yml", PARAM_FORMAT="colored",
                                            PARAM_OUTPUT_FILE=str(colored))
        self.assertEqual(status, 1)
        self.assertIn(b"\x1b[", colored.read_bytes(), "explicit colors are kept")

    def test_output_is_forwarded_before_the_body_exits(self):
        self.check_streaming()

    def test_non_blocking_step_stdout_is_waited_for(self):
        self.check_non_blocking_log()


class ExitStatus(SaveChecks):
    """AC4: the roadmap table except output refusals (#5509)."""

    def test_body_status_with_save_and_log_outcomes(self):
        for body_status in (0, 1, 2):
            for fault in ("none", "save", "log", "both"):
                with self.subTest(body=body_status, fault=fault):
                    self.check_fault(body_status, fault)
        with self.subTest(body=0, fault="closed log"):
            self.check_fault(0, "closed log")

    def test_preparation_failures_do_not_start_yamllint(self):
        only_body = self.base / "only-body"
        only_body.mkdir()
        shutil.copy2(self.bin / "yamllint", only_body / "yamllint")
        destination = self.results / "missing-python.txt"
        before = self.entries()
        result = self.run_orb(PATH=str(only_body), PARAM_TARGETS="clean.yml",
                              PARAM_OUTPUT_FILE=str(destination))
        self.require_not_started(result, before, PREFIX + b"could not prepare the output: python3")
        # A directory where no file can be created, for root and non-root alike.
        before = self.entries()
        result = self.run_orb(PARAM_TARGETS="clean.yml",
                              PARAM_OUTPUT_FILE="/proc/yamllint-orb-unwritable.txt")
        self.require_not_started(result, before,
                                 PREFIX + b"could not prepare the output: cannot create a temporary file")
        self.assertFalse(os.path.lexists("/proc/yamllint-orb-unwritable.txt"))

    def test_body_start_failure_is_not_a_result(self):
        no_body = self.base / "no-body"
        no_body.mkdir()
        (no_body / "python3").symlink_to(sys.executable)
        not_executable = self.base / "not-executable"
        not_executable.mkdir()
        (not_executable / "python3").symlink_to(sys.executable)
        (not_executable / "yamllint").write_text("#!/bin/sh\necho unreachable\n")
        for path, status in ((no_body, 127), (not_executable, 126)):
            with self.subTest(status=status):
                destination = self.results / f"start-{status}.txt"
                result = self.run_orb(PATH=str(path), PARAM_TARGETS="clean.yml",
                                      PARAM_OUTPUT_FILE=str(destination))
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, b"")
                self.assertIn(PREFIX + b"yamllint could not be started", result.stderr)
                self.require_unsaved(destination)
                self.require_no_temporaries()

    def test_existing_refusals_are_unchanged_when_saving(self):
        cases = ((CONFLICT, dict(PARAM_CONFIG_FILE="settings file.yml", PARAM_CONFIG_DATA="relaxed")),
                 (DASH, dict(PARAM_TARGETS="clean.yml\n-")),
                 (STRICT, dict(PARAM_STRICT="invalid")))
        for diagnostic, parameters in cases:
            with self.subTest(diagnostic=diagnostic):
                disabled = self.run_orb(**parameters)
                destination = self.results / "refused.txt"
                before = self.entries()
                enabled = self.run_orb(PARAM_OUTPUT_FILE=str(destination), **parameters)
                self.require_not_started(enabled, before, diagnostic)
                self.assertEqual((enabled.returncode, enabled.stdout, enabled.stderr),
                                 (disabled.returncode, disabled.stdout, disabled.stderr))
                self.assertEqual(self.diagnostics(enabled.stderr), [])


class Finalization(SaveChecks):
    """AC5: never replace an entry; never leave a partial result."""

    def test_entries_created_during_the_run_are_kept(self):
        for kind in ("file", "directory", "symlink", "broken-symlink"):
            for body_status in (0, 1):
                with self.subTest(kind=kind, body=body_status):
                    self.check_conflict(kind, body_status)

    def test_write_failure_leaves_no_partial_result(self):
        for body_status in (0, 1):
            with self.subTest(body=body_status):
                destination, result = self.run_fault(body_status, "save")
                self.assertEqual(result.returncode, body_status or 2)
                self.require_unsaved(destination)
                self.require_no_temporaries()

    def test_vanished_temporary_file_is_not_finalized(self):
        destination = self.results / "vanished.txt"
        result = self.run_orb(BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                              BODY_REMOVE_TEMPORARY=str(self.results), PARAM_TARGETS="clean.yml",
                              PARAM_OUTPUT_FILE=str(destination))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, PAYLOAD)
        self.assertIn(PREFIX + b"the result file", result.stderr)
        self.require_unsaved(destination)
        self.require_no_temporaries()

    def test_directory_permissions_before_and_during_the_run(self):
        if os.geteuid() == 0:
            self.fail("Run as a non-root user: root ignores directory permission bits")
        locked = self.results / "locked"
        locked.mkdir()
        locked.chmod(0o555)
        self.addCleanup(locked.chmod, 0o755)
        before = self.entries()
        result = self.run_orb(PARAM_TARGETS="clean.yml", PARAM_OUTPUT_FILE=str(locked / "out.txt"))
        self.require_not_started(result, before, PREFIX + b"could not prepare the output: "
                                                          b"cannot create a temporary file")
        later = self.results / "later"
        later.mkdir()
        self.addCleanup(later.chmod, 0o755)
        result = self.run_orb(BODY_MODE="emit", BODY_STDOUT=str(self.payload_file),
                              BODY_LOCK=str(later), PARAM_TARGETS="clean.yml",
                              PARAM_OUTPUT_FILE=str(later / "out.txt"))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, PAYLOAD)
        self.assertIn(PREFIX + b"could not create", result.stderr)
        self.assertIn(PREFIX + b"could not remove the temporary file", result.stderr)
        self.require_unsaved(later / "out.txt")
        leftovers = [name for name in os.listdir(later) if name.startswith(TEMPORARY_PREFIX)]
        self.assertEqual(len(leftovers), 1, "the reported temporary file must be the only one")
        self.assertIn(leftovers[0].encode(), result.stderr)


class FaultDetection(SaveChecks):
    """AC6: the checks above reject broken implementations of the save path."""

    MUTANTS = {
        "result file not created": ("            os.link(path, destination)\n",
                                    "            pass\n", "check_bytes_case", (0,)),
        "bytes dropped": ("                write_all(saved, chunk)\n",
                          "                write_all(saved, chunk[1:])\n", "check_bytes_case", (0,)),
        "stderr saved": ("run_yamllint | python3", "run_yamllint 2>&1 | python3",
                         "check_bytes_case", (1,)),
        "wrong exit status": ('    exit "${RELAY_STATUS[0]}"\n', "    exit 0\n",
                              "check_bytes_case", (1,)),
        "save failure ignored": ("    saved = relay_status in (0, LOG_FAILED)\n    problem = relay_status != 0\n",
                                 "    saved = True\n    problem = False\n", "check_fault", (0, "save")),
        "log failure ignored": ("    problem = relay_status != 0\n", "    problem = relay_status == SAVE_FAILED\n",
                                "check_fault", (0, "log")),
        "existing entry replaced": ("            os.link(path, destination)\n",
                                    "            os.replace(path, destination)\n", "check_conflict", ("file",)),
        "body not run": ("run_yamllint | python3", "true | python3", "check_real_case",
                         (SaveChecks.REAL_CASES[1],)),
        "relay waits for the end": ("            chunk = os.read(0, 65536)\n",
                                    "            chunk = sys.stdin.buffer.read()\n", "check_streaming", ()),
        "EAGAIN treated as a log failure": ("        except BlockingIOError:\n",
                                            "        except ZeroDivisionError:\n",
                                            "check_non_blocking_log", ()),
        "body writes to the step stdout": (
            'run_yamllint | python3 -I -c "${ORB_OUTPUT_HELPER}" forward',
            'run_yamllint; python3 -I -c "${ORB_OUTPUT_HELPER}" forward', "check_terminal", ()),
        "path trimmed": ("    raw = argv[2]\n", "    raw = argv[2].strip()\n", "check_interpretation", ()),
        "path expanded": ("    raw = argv[2]\n",
                          "    raw = os.path.expanduser(os.path.expandvars(argv[2]))\n",
                          "check_interpretation", ()),
        "relative to HOME": ("    raw = argv[2]\n",
                             "    raw = os.path.join(os.path.expanduser(\"~\"), argv[2])\n",
                             "check_interpretation", ()),
    }

    def test_checks_reject_broken_save_implementations(self):
        source = EXECUTE.read_text()
        mutated = self.base / "mutated-execute.sh"
        for name, (original, replacement, check, arguments) in self.MUTANTS.items():
            with self.subTest(mutant=name):
                self.assertEqual(source.count(original), 1, f"{name}: locate the code to mutate")
                mutated.write_text(source.replace(original, replacement, 1))
                with self.assertRaises(AssertionError):
                    getattr(self, check)(*arguments, script=mutated)
                self.reset_results()

    def reset_results(self):
        for entry in list(self.results.iterdir()):
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        for name in ("~", "$HOME", "sub dir"):
            path = self.work / name
            if path.is_dir():
                shutil.rmtree(path)
        for path in (self.work / "relative.txt", self.base / "release"):
            path.unlink(missing_ok=True)
        for entry in list(self.home.iterdir()):
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()


if __name__ == "__main__":
    unittest.main()
