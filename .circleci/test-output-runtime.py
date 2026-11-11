#!/usr/bin/env python3
"""#5510 step-observer checks: python3 .circleci/test-output-runtime.py -v.

The real src/scripts/execute.sh runs once per case as a CircleCI-like step,
"bash -eo pipefail -c <script>", in a temporary checkout outside this
repository. This test plays CircleCI: it provides BASH_ENV and gives the step
a pipe or a pseudo-terminal as stdout. The observer's own prepare, BASH_ENV
hook, body recorder and finish run unchanged, with the real yamllint 1.37.1
or 1.38.0 of this Python. Fault controls:

* broken Orb scripts that the real-step observation must reject;
* corrupted observations that each observer check must reject;
* the recorder must keep the body's bytes, connection, end of output and
  exit status, and must refuse before running an unexpected body.

Local runs are supplementary. CircleCI runs this suite in every fixed-matrix
compatibility job; the observed real steps run in the output-file jobs.
"""
import copy
import errno
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT / '.circleci/verify-output-file.py'
EXECUTE = (ROOT / 'src/scripts/execute.sh').read_text(encoding='utf-8')
VERSION = (ROOT / 'src/scripts/show-version.sh').read_text(encoding='utf-8')
BASH = shutil.which('bash')
spec = importlib.util.spec_from_file_location('observer', OBSERVER)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
RELAY = 'run_yamllint | python3 -I -c "${ORB_OUTPUT_HELPER}" forward'


class Job:
    """One emulated output-file job in a temporary checkout."""

    def __init__(self, selection=None, numeric=False, terminal=False, shim=False):
        self.version = importlib.metadata.version('yamllint')
        if self.version not in ('1.37.1', '1.38.0'):
            raise RuntimeError('Run this suite with yamllint 1.37.1 or 1.38.0')
        self.temporary = tempfile.TemporaryDirectory(prefix='yamllint-output-runtime-')
        base = Path(self.temporary.name)
        self.work, self.absolute = base / 'work', base / 'results'
        self.bin, home, self.bash_env = base / 'bin', base / 'home', base / 'bash_env'
        for directory in (self.work, self.bin, home):
            directory.mkdir()
        self.bash_env.write_text('')
        if shim:
            # Like a pyenv shim on cimg/python: python3 for the Orb's helper is a
            # bash script, which reads BASH_ENV again inside the step.
            (self.bin / 'python3').write_text(f'#!{BASH}\nexec {shlex.quote(sys.executable)} "$@"\n')
            (self.bin / 'python3').chmod(0o755)
        else:
            (self.bin / 'python3').symlink_to(sys.executable)
        # Bind the body to this Python's real upstream, independently of PATH.
        self.real = base / 'real-yamllint'
        self.real.write_text(f'#!{sys.executable}\nfrom yamllint.cli import run\nrun()\n')
        self.real.chmod(0o755)
        resolved = self.real
        if shim:
            # Like a pyenv shim on cimg/python: a bash script, which reads BASH_ENV
            # again inside the step, that execs the real program.
            resolved = base / 'shims' / 'yamllint'
            resolved.parent.mkdir()
            resolved.write_text(f'#!{BASH}\nexec {shlex.quote(str(self.real))} "$@"\n')
            resolved.chmod(0o755)
        self.numeric, self.terminal = numeric, terminal
        self.evidence = self.work / '.output-evidence'
        with patch.multiple(observer, ROOT=self.work, EVIDENCE=self.evidence,
                            STATE=self.evidence / 'state.json', ABSOLUTE=self.absolute), \
                patch.object(observer, 'identity', return_value={
                    'kind': 'local-supplementary', 'packages': {'yamllint': self.version}}), \
                patch.object(observer.shutil, 'which', return_value=str(resolved)), \
                patch.dict(os.environ, {'EXPECTED_YAMLLINT': self.version, 'BASH_ENV': str(self.bash_env)}):
            observer.prepare(local=True, selection=selection)
        self.selected = list(observer.CASES) if selection is None else list(selection)
        self.calls = observer.configured_cases()
        self.defaults = observer.defaults()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('PARAM_') and k not in (
            'BASH_ENV', 'ENV', 'CDPATH', 'YAMLLINT_CONFIG_FILE', 'GITHUB_ACTIONS', 'GITHUB_WORKFLOW')}
        self.env.update(PATH=f'{self.bin}{os.pathsep}{self.env.get("PATH", "")}', HOME=str(home),
                        XDG_CONFIG_HOME=str(base / 'xdg'), BASH_ENV=str(self.bash_env))

    def close(self):
        self.temporary.cleanup()

    def parameters(self, case):
        values = dict(self.defaults)
        for name, value in self.calls[case].items():
            values[name] = (value.replace(observer.CONFIG_ABSOLUTE, str(self.absolute))
                            if isinstance(value, str) else value)
        result = {}
        for name, env in observer.PARAMETERS.items():
            value = values[name]
            if isinstance(value, bool):
                value = ('1' if value else '0') if self.numeric else ('true' if value else 'false')
            result[env] = value
        return result

    def step(self, command, parameters=None):
        """One step shell; returns (status, stdout+stderr as seen by CircleCI)."""
        env = {**self.env, **(parameters or {})}
        argv = [BASH, '-eo', 'pipefail', '-c', command]
        if not self.terminal:
            result = subprocess.run(argv, cwd=self.work, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
            return result.returncode, result.stdout + result.stderr
        master, slave = pty.openpty()
        try:
            process = subprocess.Popen(argv, cwd=self.work, env=env, stdin=subprocess.DEVNULL,
                                       stdout=slave, stderr=slave)
        finally:
            os.close(slave)
        output, deadline = bytearray(), time.monotonic() + 120
        try:
            while True:
                if time.monotonic() > deadline:
                    process.kill()
                    raise AssertionError('terminal step did not finish')
                ready, _, _ = select.select([master], [], [], 0.2)
                if not ready:
                    continue
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    data = b''
                if not data:
                    break
                output += data
            process.wait(timeout=30)
        finally:
            os.close(master)
        return process.returncode, bytes(output)

    def observer_step(self, *args):
        return self.step(' '.join(shlex.quote(str(a)) for a in (sys.executable, OBSERVER, *args)))

    def run(self, script=EXECUTE):
        """Run every selected case like the CircleCI job; stop at the first failing step."""
        for case in self.selected:
            for name, (status, output) in ((f'Observe {case}', self.observer_step('expect', case)),
                                           ('Show yamllint version', self.step(VERSION))):
                if status:
                    return name, output
            status, output = self.step(script, self.parameters(case))
            if status:
                return f'Execute yamllint ({case})', output
        status, output = self.observer_step('finish')
        return (None, output) if status == 0 else ('Verify output_file observations', output)

    def state(self):
        return json.loads((self.evidence / 'state.json').read_text(encoding='utf-8'))

    def results(self):
        return json.loads((self.evidence / 'results.json').read_text(encoding='utf-8'))


def mutate(old, new, text=EXECUTE):
    if text.count(old) != 1:
        raise AssertionError(f'mutation anchor not unique: {old!r}')
    return text.replace(old, new)


class RealStepObservation(unittest.TestCase):
    """The unchanged script passes every configured case on both kinds of step stdout."""

    def check_job(self, numeric, terminal, shim):
        job = Job(numeric=numeric, terminal=terminal, shim=shim)
        self.addCleanup(job.close)
        failed, output = job.run()
        self.assertIsNone(failed, output.decode(errors='replace'))
        report = job.results()
        self.assertEqual([row['case'] for row in report['cases']], list(observer.CASES))
        step_type = 'character device' if terminal else 'pipe'
        for row in report['cases']:
            with self.subTest(case=row['case']):
                self.assertEqual(row['body_status'], 0)
                self.assertEqual(row['step_stdout']['type'], step_type)
                self.assertEqual(row['step_stdout']['isatty'], terminal)
                self.assertEqual(row['raw_parameters'], job.parameters(row['case']))
                if row['saving']:
                    self.assertEqual(row['body_stdout']['type'], 'pipe')
                    self.assertFalse(row['body_stdout']['isatty'])
                    self.assertTrue(row['saved']['equals_reference_stdout'])
                else:
                    self.assertEqual(row['body_stdout']['identity'], row['step_stdout']['identity'])
                self.assertEqual(row['body_stderr']['identity'], row['step_stderr']['identity'])
        saved = {row['case']: row['saved']['bytes'] for row in report['cases'] if row['saving']}
        self.assertEqual(saved['relative-strict-clean'], 0)
        self.assertGreater(saved['long-literal-path'], 65536)
        self.assertTrue((job.work / observer.LITERAL).is_file())
        # The hook is inactive after finish: the recorder is no longer put on PATH.
        status, output = job.step('printf "%s" "$PATH"')
        self.assertEqual(status, 0)
        self.assertNotIn(str(job.evidence), output.decode())

    def test_all_cases_with_pipe_step_stdout_and_textual_booleans(self):
        self.check_job(numeric=False, terminal=False, shim=False)

    def test_all_cases_with_terminal_step_stdout_numeric_booleans_and_bash_shim(self):
        self.check_job(numeric=True, terminal=True, shim=True)


class BrokenOrbScripts(unittest.TestCase):
    """Each broken script must stop the job: a failing step or a rejected finish."""

    def rejected(self, script, selection, reason, failed_step='Verify output_file observations'):
        job = Job(selection=selection)
        self.addCleanup(job.close)
        failed, output = job.run(script)
        self.assertEqual(failed, failed_step, output.decode(errors='replace'))
        self.assertIn(reason, output.decode(errors='replace'))

    def test_relay_while_saving_is_disabled(self):
        script = mutate('    run_yamllint\n    exit 0\nfi', '    run_yamllint | cat\n    exit 0\nfi')
        self.rejected(script, ['saving-omitted'], 'saving is disabled but yamllint stdout is not the step stdout')

    def test_stderr_sent_into_the_saved_output(self):
        script = mutate(RELAY, RELAY.replace('run_yamllint |', 'run_yamllint 2>&1 |'))
        self.rejected(script, ['absolute-parsable'], 'yamllint stderr is not the step stderr')

    def test_extra_bytes_in_the_result_file(self):
        script = mutate('        saved = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)\n',
                        '        saved = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)\n'
                        '        os.write(saved, b"yamllint result\\n")\n')
        self.rejected(script, ['absolute-parsable'], 'saved bytes differ from the reference stdout')

    def test_no_file_for_empty_output(self):
        script = mutate('    elif saved:\n', '    elif saved and os.path.getsize(path):\n')
        self.rejected(script, ['relative-strict-clean'], "expected only 'root:output-results/strict-clean.txt'")

    def test_terminal_given_to_yamllint(self):
        spawn = ('python3 -c "import pty, sys; sys.exit(pty.spawn(sys.argv[1:]) >> 8)" '
                 'yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[@]}" |')
        script = mutate(RELAY, RELAY.replace('run_yamllint |', spawn))
        self.rejected(script, ['absolute-parsable'], 'yamllint stdout is a terminal while saving')

    def test_output_file_reinterpreted(self):
        script = mutate('OUTPUT_FILE="${PARAM_OUTPUT_FILE:-}"\n',
                        'OUTPUT_FILE="${PARAM_OUTPUT_FILE:-}"\nOUTPUT_FILE="${OUTPUT_FILE//\\$HOME/home}"\n')
        self.rejected(script, ['long-literal-path'], 'long-literal-path: expected only')

    def test_temporary_file_left_behind(self):
        script = mutate('        os.unlink(path)\n    except FileNotFoundError:',
                        '        os.stat(path)\n    except FileNotFoundError:')
        self.rejected(script, ['absolute-parsable'], 'Temporary output data was left behind')

    def test_strict_not_passed(self):
        script = mutate('    true | 1)\n        YAMLLINT_ARGS+=("--strict")', '    true | 1)\n        :')
        self.rejected(script, ['relative-strict-clean'], 'relative-strict-clean: argument mismatch')

    def test_body_run_twice(self):
        script = mutate('set +e\nrun_yamllint |', 'run_yamllint > /dev/null\nset +e\nrun_yamllint |')
        self.rejected(script, ['absolute-parsable'], 'Unexpected or duplicate body invocation',
                      failed_step='Execute yamllint (absolute-parsable)')

    def test_color_codes_removed(self):
        script = mutate('        if not chunk:\n            break\n',
                        '        if not chunk:\n            break\n'
                        '        chunk = chunk.replace(b"\\x1b", b"")\n')
        self.rejected(script, ['colored-format'], 'saved bytes differ from the reference stdout')

    def test_body_not_run(self):
        script = mutate(RELAY, RELAY.replace('run_yamllint |', 'true |'))
        self.rejected(script, ['absolute-parsable'], 'Final Orb body was not invoked')


class CorruptObservations(unittest.TestCase):
    """Every observer check rejects its own fault, identified by its message."""

    @classmethod
    def setUpClass(cls):
        cls.job = Job()
        failed, output = cls.job.run()
        if failed:
            cls.job.close()
            raise AssertionError(output.decode(errors='replace'))
        cls.state = cls.job.state()
        cls.final = observer.snapshot(cls.state)

    @classmethod
    def tearDownClass(cls):
        cls.job.close()

    def bounds(self, state, case):
        cases = state['selected']
        index = cases.index(case)
        after = state['cases'][cases[index + 1]]['before'] if index + 1 < len(cases) else self.final
        return state['cases'][case]['before'], after

    def check(self, case, state=None, before=None, after=None, environment=None):
        state = state or self.state
        default_before, default_after = self.bounds(state, case)
        environment = environment or observer.reference_environment()
        return observer.check_case(state, case, before or default_before, after or default_after, environment)

    def assert_rejected(self, message, case, change=None, **arguments):
        state = copy.deepcopy(self.state)
        if change:
            change(state['cases'][case])
        with self.assertRaisesRegex(RuntimeError, message):
            self.check(case, state=state, **arguments)

    def test_case_checks_reject_corruption(self):
        for case in observer.CASES:
            self.check(case)  # the unchanged observation passes
        body = lambda change: lambda entry: change(entry['body'])  # noqa: E731
        faults = [
            ('absolute-parsable', 'did not exit 0', body(lambda b: b.update(status=1))),
            ('absolute-parsable', 'was not invoked', lambda e: e.update(body=None)),
            ('absolute-parsable', 'argument mismatch', body(lambda b: b['argv'].remove('parsable'))),
            ('absolute-parsable', 'PARAM_OUTPUT_FILE was not passed unchanged',
             body(lambda b: b['raw_parameters'].update(PARAM_OUTPUT_FILE='lint.txt'))),
            ('relative-strict-clean', 'unexpected raw PARAM_STRICT',
             body(lambda b: b['raw_parameters'].update(PARAM_STRICT='false'))),
            ('hidden-warning', 'unexpected raw PARAM_NO_WARNINGS',
             body(lambda b: b['raw_parameters'].update(PARAM_NO_WARNINGS='invalid'))),
            ('config-file', 'PARAM_CONFIG_FILE was not passed unchanged',
             body(lambda b: b['raw_parameters'].update(PARAM_CONFIG_FILE=''))),
            ('absolute-parsable', 'ran in another directory', body(lambda b: b.update(cwd='/'))),
            ('absolute-parsable', 'no recorded step owns the body', body(lambda b: b.update(step=9))),
            ('absolute-parsable', 'terminal while saving',
             body(lambda b: b['stdout'].update(isatty=True))),
            ('absolute-parsable', 'is the step stdout although saving is enabled',
             lambda e: e['body'].update(stdout=e['steps'][e['body']['step']]['stdout'])),
            ('absolute-parsable', 'stderr is not the step stderr',
             body(lambda b: b['stderr'].update(identity=[0, 0, 0, 0]))),
            ('saving-omitted', 'saving is disabled but yamllint stdout is not the step stdout',
             body(lambda b: b['stdout'].update(identity=[0, 0, 0, 0]))),
            ('saving-empty', 'saving is disabled but yamllint stdout is not the step stdout',
             body(lambda b: b['stdout'].update(isatty=not b['stdout']['isatty']))),
        ]
        for case, message, change in faults:
            with self.subTest(case=case, message=message):
                self.assert_rejected(message, case, change)
        before, after = self.bounds(self.state, 'absolute-parsable')
        with self.assertRaisesRegex(RuntimeError, 'expected only'):
            self.check('absolute-parsable', after=after + ['absolute:extra.txt'])
        before, after = self.bounds(self.state, 'saving-empty')
        with self.assertRaisesRegex(RuntimeError, 'saving is disabled but entries were created'):
            self.check('saving-empty', after=after + ['root:output-results/extra.txt'])
        with self.assertRaisesRegex(RuntimeError, 'entries disappeared'):
            self.check('saving-empty', before=before + ['root:gone.yml'])
        with self.assertRaisesRegex(RuntimeError, 'reference environment differs'):
            self.check('auto-format', environment={**observer.reference_environment(),
                                                   'GITHUB_ACTIONS': 'true', 'GITHUB_WORKFLOW': 'ci'})

    def test_saved_file_faults(self):
        path = self.job.absolute / 'absolute-parsable.txt'
        original = path.read_bytes()
        try:
            for changed in (original + b'\n', original[:-1], original.replace(b'\n', b'\r\n'), b''):
                path.write_bytes(changed)
                with self.subTest(changed=changed[-12:]):
                    with self.assertRaisesRegex(RuntimeError, 'saved bytes differ from the reference stdout'):
                        self.check('absolute-parsable')
            path.unlink()
            path.symlink_to(self.job.work / 'output-fixtures/warning.yml')
            with self.assertRaisesRegex(RuntimeError, 'not a regular file'):
                self.check('absolute-parsable')
        finally:
            path.unlink()
            path.write_bytes(original)
        self.check('absolute-parsable')

    def test_meaning_checks_reject_wrong_reference_output(self):
        warning = b'output-fixtures/warning.yml:2:31: [warning] line too long (61 > 30 characters) (line-length)\n'
        for kind, data in (('empty', b'\n'), ('warning', b''), ('warning', warning * 2),
                           ('warning', warning.replace(b'warning]', b'error]')),
                           ('listing', b'output-fixtures/listing/keep.yml\n'),
                           ('standard', b'\x1b[4moutput-fixtures/warning.yml\x1b[0m\n'),
                           ('colored', b'output-fixtures/warning.yml\n'), ('long', warning * 2000)):
            with self.subTest(kind=kind, data=data[:30]):
                with self.assertRaisesRegex(RuntimeError, 'expected meaning'):
                    observer.check_meaning('case', kind, data)

    def test_sequence_checks_reject_missing_reordered_and_leftovers(self):
        def finish_with(change):
            state = copy.deepcopy(self.state)
            change(state)
            path = self.job.evidence / 'state.json'
            original = path.read_text(encoding='utf-8')
            path.write_text(json.dumps(state), encoding='utf-8')
            try:
                with patch.multiple(observer, ROOT=self.job.work, EVIDENCE=self.job.evidence, STATE=path):
                    observer.finish()
            finally:
                path.write_text(original, encoding='utf-8')
        cases = list(observer.CASES)
        for message, change in (
                ('Final Orb body was not invoked', lambda s: s.update(pending=cases[-1])),
                ('Missing, reordered or duplicated cases',
                 lambda s: s.update(cases={c: s['cases'][c] for c in reversed(cases)})),
                ('Missing, reordered or duplicated cases', lambda s: s['cases'].pop(cases[3]))):
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message):
                    finish_with(change)
        leftover = self.job.absolute / '.yamllint-orb-output-0123456789abcdef.tmp'
        leftover.write_text('')
        try:
            with self.assertRaisesRegex(RuntimeError, 'Temporary output data was left behind'):
                finish_with(lambda s: None)
        finally:
            leftover.unlink()


class Recorder(unittest.TestCase):
    """The body-position recorder and the BASH_ENV hook, in isolation."""

    def setUp(self):
        self.job = Job(selection=['absolute-parsable'])
        self.addCleanup(self.job.close)
        self.wrapper = self.job.evidence / 'bin' / 'yamllint'
        self.marker = self.job.work / 'fake-ran'

    def arm(self, step_pid=None):
        """Arm the case with a recorded step owned by this test process (or another PID)."""
        state = self.job.state()
        pid = step_pid or os.getpid()
        state['pending'] = 'absolute-parsable'
        state['cases'] = {'absolute-parsable': dict(before=[], body=None, steps=[dict(
            pid=pid, start=observer.process(pid)[1], stdout={}, stderr={})])}
        (self.job.evidence / 'state.json').write_text(json.dumps(state), encoding='utf-8')

    def fake(self, body):
        """Replace the real upstream with a controlled body; it records its own stdout."""
        self.job.real.write_text(f'#!{sys.executable}\nimport os, sys, time, json\n'
                                 f'open({str(self.marker)!r}, "w").write(json.dumps(list(os.fstat(1)[1:3])))\n'
                                 + body)

    def invoke(self, *argv):
        process = subprocess.Popen([str(self.wrapper), *argv], cwd=self.job.work, env=self.job.env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(process.stderr.close)
        self.addCleanup(process.stdout.close)
        return process

    def test_bytes_connection_and_status_are_unchanged(self):
        payload = b'first\r\nsecond\x00 \xff\xfe \x1b[31mred\x1b[0m no final newline'
        self.fake(f'os.write(1, {payload!r})\nsys.exit(3)\n')
        self.arm()
        process = self.invoke('--format', 'parsable', '--', 'x.yml')
        pipe = os.fstat(process.stdout.fileno())
        stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 3, stderr)
        self.assertEqual(stdout, payload)
        state = self.job.state()
        body = state['cases']['absolute-parsable']['body']
        self.assertEqual(body['status'], 3)
        self.assertEqual(body['argv'], ['--format', 'parsable', '--', 'x.yml'])
        self.assertEqual(body['stdout']['type'], 'pipe')
        # The recorder, the body and this test's pipe are one and the same connection.
        fake_ino, fake_dev = json.loads(self.marker.read_text())
        self.assertEqual(body['stdout']['identity'][1:3], [pipe.st_dev, pipe.st_ino])
        self.assertEqual([fake_dev, fake_ino], [pipe.st_dev, pipe.st_ino])
        self.assertIsNone(state['pending'])

    def test_end_of_output_is_the_body_own(self):
        # The body releases its stdout, then keeps running.
        self.fake('os.write(1, b"x")\nos.dup2(os.open(os.devnull, os.O_WRONLY), 1)\ntime.sleep(6)\n')
        self.arm()
        process = self.invoke('--', 'x.yml')
        start = time.monotonic()
        data = process.stdout.read()  # returns at end of output
        elapsed = time.monotonic() - start
        process.wait(timeout=30)
        self.assertEqual(data, b'x')
        self.assertLess(elapsed, 4, 'the recorder kept the body stdout open')
        self.assertEqual(process.returncode, 0)

    def test_refuses_before_running_an_unexpected_body(self):
        self.fake('sys.exit(0)\n')
        for message, prepare in (('Unexpected or duplicate body invocation', lambda: None),
                                 ('did not run in the latest observed step', lambda: self.arm(step_pid=1)),
                                 ('Unexpected or duplicate body invocation', self.arm_recorded)):
            with self.subTest(message=message):
                prepare()
                process = self.invoke('--', 'x.yml')
                stdout, stderr = process.communicate(timeout=30)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn(message, stderr.decode())
                self.assertEqual(stdout, b'')
                self.assertFalse(self.marker.exists(), 'the body ran although it was refused')

    def arm_recorded(self):
        self.arm()
        state = self.job.state()
        state['cases']['absolute-parsable']['body'] = {'status': 0}
        (self.job.evidence / 'state.json').write_text(json.dumps(state), encoding='utf-8')

    def test_version_call_passes_through_without_a_record(self):
        self.fake('print("fake 9.9.9")\n')
        self.arm()
        before = self.job.state()
        process = self.invoke('--version')
        stdout, stderr = process.communicate(timeout=30)
        self.assertEqual((process.returncode, stdout), (0, b'fake 9.9.9\n'), stderr)
        self.assertEqual(self.job.state(), before)

    def test_hook_records_the_step_shell_and_writes_nothing(self):
        self.arm()
        state = self.job.state()
        state['cases']['absolute-parsable']['steps'] = []
        (self.job.evidence / 'state.json').write_text(json.dumps(state), encoding='utf-8')
        with subprocess.Popen([BASH, '-eo', 'pipefail', '-c', 'true'], cwd=self.job.work, env=self.job.env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            pipe = os.fstat(process.stdout.fileno())
            stdout, stderr = process.communicate(timeout=30)
        self.assertEqual((process.returncode, stdout, stderr), (0, b'', b''))
        steps = self.job.state()['cases']['absolute-parsable']['steps']
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]['pid'], process.pid)
        self.assertEqual(steps[0]['stdout']['type'], 'pipe')
        self.assertEqual(steps[0]['stdout']['identity'][1:3], [pipe.st_dev, pipe.st_ino])
        self.assertFalse(steps[0]['stdout']['isatty'])
        self.assertEqual(stat.S_IFMT(pipe.st_mode), steps[0]['stdout']['identity'][0])

    def test_shell_nested_in_an_observed_step_is_not_a_step(self):
        self.arm()
        state = self.job.state()
        state['cases']['absolute-parsable']['steps'] = []
        (self.job.evidence / 'state.json').write_text(json.dumps(state), encoding='utf-8')
        nested = f'{shlex.quote(BASH)} -c true'
        with subprocess.Popen([BASH, '-eo', 'pipefail', '-c', f'{nested}; {nested}'], cwd=self.job.work,
                              env=self.job.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            stdout, stderr = process.communicate(timeout=30)
        self.assertEqual((process.returncode, stdout, stderr), (0, b'', b''))
        steps = self.job.state()['cases']['absolute-parsable']['steps']
        self.assertEqual([step['pid'] for step in steps], [process.pid])


if __name__ == '__main__':
    unittest.main()
