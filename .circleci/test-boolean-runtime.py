#!/usr/bin/env python3
"""Real-upstream boolean regressions and fault controls for the runtime observer.

Local subprocesses explicitly model both encodings. They are supplemental to
actual typed Orb steps in every CircleCI matrix job, whose environment is never
rewritten. The old two-condition implementation must fail the numeric controls.
"""
import copy
from contextlib import chdir
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT / '.circleci/verify-boolean-parameters.py'
SCRIPT = ROOT / 'src/scripts/execute.sh'
spec = importlib.util.spec_from_file_location('observer', OBSERVER)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class BooleanRuntime(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-boolean-')
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.evidence = self.work / '.boolean-evidence'
        self.state = self.evidence / 'state.json'
        # Fixture setup only. The subprocess observer uses its normal real CLI
        # invocation, validation and state machine, without mocks.
        with chdir(self.work), \
                patch.multiple(observer, ROOT=self.work, EVIDENCE=self.evidence, STATE=self.state), \
                patch.object(observer, 'identity', return_value={
                    'kind': 'local-supplementary',
                    'packages': {'yamllint': importlib.metadata.version('yamllint')}}), \
                patch.dict(os.environ, {'EXPECTED_YAMLLINT': importlib.metadata.version('yamllint')}):
            observer.prepare(local=True)
        # Bind to this Python's actual upstream, independently of host PATH.
        real = self.work / 'real-yamllint'
        real.write_text(f'#!{sys.executable}\nfrom yamllint.cli import run\nrun()\n')
        real.chmod(0o755)
        state = json.loads(self.state.read_text())
        state['real'] = str(real)
        self.state.write_text(json.dumps(state))
        self.initial = copy.deepcopy(state)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('PARAM_')
                    and k not in ('BASH_ENV', 'ENV', 'CDPATH', 'YAMLLINT_CONFIG_FILE')}
        self.env.update(PATH=str(self.evidence / 'bin') + os.pathsep + self.env['PATH'],
                        HOME=str(self.work), XDG_CONFIG_HOME=str(self.work / 'xdg'))
        self.calls = {}
        pending = None
        config = yaml.safe_load((ROOT / '.circleci/test-deploy.yml').read_text())
        for step in config['jobs']['compatibility-tests']['steps']:
            if isinstance(step, dict) and step.get('run', {}).get('name', '').startswith('Expect '):
                pending = step['run']['name'].removeprefix('Expect ')
            elif pending and isinstance(step, dict) and 'yamllint/execute' in step:
                self.calls[pending] = step['yamllint/execute']
                pending = None
        self.assertEqual(list(self.calls), list(observer.CASES))

    def run_observer(self, *args, environment=None):
        return subprocess.run([sys.executable, str(OBSERVER), *args], cwd=self.work,
                              env=environment or self.env, text=True, capture_output=True, timeout=20)

    def parameters(self, case, numeric):
        defaults = yaml.safe_load((ROOT / 'src/commands/execute.yml').read_text())['parameters']
        values = {k: v['default'] for k, v in defaults.items()}
        values.update(self.calls[case])
        return {'PARAM_' + key.upper(): (str(int(value)) if numeric else str(value).lower())
                if isinstance(value, bool) else value for key, value in values.items()}

    def execute(self, case, numeric, script=SCRIPT):
        return subprocess.run(['bash', str(script)], cwd=self.work,
                              env={**self.env, **self.parameters(case, numeric)},
                              text=True, capture_output=True, timeout=20)

    def test_actual_script_all_cases_text_and_numeric(self):
        for numeric in (False, True):
            self.state.write_text(json.dumps(self.initial))
            for case in observer.CASES:
                with self.subTest(numeric=numeric, case=case):
                    self.assertEqual(self.run_observer('expect', case).returncode, 0)
                    result = self.execute(case, numeric)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.run_observer('finish').returncode, 0)
            report = json.loads((self.evidence / 'results.json').read_text())
            self.assertEqual(len(report['results']), len(observer.CASES))
            for row in report['results']:
                self.assertEqual(row['raw_parameters'], self.parameters(row['case'], numeric))

    def test_old_conditions_fail_numeric_regressions(self):
        old = SCRIPT.read_text()
        for name in ('NO_WARNINGS', 'LIST_FILES'):
            addition = ' || "${PARAM_' + name + ':-false}" == "1"'
            self.assertEqual(old.count(addition), 1)
            old = old.replace(addition, '')
        path = self.work / 'old-execute.sh'
        path.write_text(old)
        for case in ('hidden-warning', 'hidden-strict-warning', 'visible-error', 'list-files'):
            with self.subTest(case=case):
                state = copy.deepcopy(self.initial)
                state['pending'] = case
                self.state.write_text(json.dumps(state))
                result = self.execute(case, True, path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('argument mismatch', result.stderr)

    def test_validator_rejects_corrupt_observations(self):
        for case, (argv, status, output) in observer.CASES.items():
            actual = subprocess.run([self.initial['real'], *argv], cwd=self.work,
                                    env=self.env, text=True, capture_output=True, timeout=20)
            observer.validate(case, argv, actual.returncode, actual.stdout, actual.stderr)
            faults = [(argv, 99, actual.stdout, actual.stderr),
                      (argv, status, actual.stdout + 'unexpected\n', ''),
                      (argv, status, actual.stdout, 'unexpected\n'),
                      (argv[:-1], status, actual.stdout, '')]
            if status:
                faults.append((argv, 0, actual.stdout, ''))
            if actual.stdout:
                faults.append((argv, status, '', ''))
            for flag in ('--no-warnings', '--list-files'):
                if flag in argv:
                    faults.append(([v for v in argv if v != flag], status, actual.stdout, ''))
            for fault in faults:
                with self.subTest(case=case, fault=fault):
                    with self.assertRaises(RuntimeError):
                        observer.validate(case, *fault)
            raw = self.parameters(case, True)
            observer.validate_raw(case, raw)
            for name in ('PARAM_STRICT', 'PARAM_NO_WARNINGS', 'PARAM_LIST_FILES'):
                with self.assertRaises(RuntimeError):
                    observer.validate_raw(case, {**raw, name: 'invalid'})

    def test_state_rejects_missing_duplicate_and_reordered_bodies(self):
        self.assertNotEqual(self.run_observer('finish').returncode, 0)
        self.assertNotEqual(self.run_observer('expect', 'list-files').returncode, 0)
        self.assertEqual(self.run_observer('expect', 'config-file').returncode, 0)
        self.assertNotEqual(self.run_observer('expect', 'config-data').returncode, 0)
        self.assertNotEqual(self.run_observer('finish').returncode, 0)
        self.assertEqual(self.execute('config-file', True).returncode, 0)
        self.assertNotEqual(self.execute('config-file', True).returncode, 0)
        self.assertNotEqual(self.run_observer('expect', 'config-file').returncode, 0)
        state = copy.deepcopy(self.initial)
        state['results'] = [{'case': c} for c in observer.CASES]
        state['results'][-1] = state['results'][0]
        self.state.write_text(json.dumps(state))
        self.assertNotEqual(self.run_observer('finish').returncode, 0)

    def test_invocation_rejects_bad_upstream_status_and_output(self):
        case = 'visible-strict-warning'
        argv = observer.CASES[case][0]
        actual = subprocess.run([self.initial['real'], *argv], cwd=self.work,
                                env=self.env, text=True, capture_output=True, check=False, timeout=20)
        fake = self.work / 'faulty-upstream'
        for status, stdout, stderr in ((0, actual.stdout, ''), (1, actual.stdout, ''),
                                        (2, '', ''), (2, actual.stdout, 'unexpected\n')):
            fake.write_text(f'#!{sys.executable}\nimport sys\nsys.stdout.write({stdout!r})\n'
                            f'sys.stderr.write({stderr!r})\nsys.exit({status})\n')
            fake.chmod(0o755)
            state = dict(self.initial, pending=case, real=str(fake))
            self.state.write_text(json.dumps(state))
            result = self.execute(case, True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(self.state.read_text())['results'], [])


if __name__ == '__main__':
    unittest.main()
