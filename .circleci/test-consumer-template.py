#!/usr/bin/env python3
"""#5512 consumer template and D08 judgment checks: python3 .circleci/test-consumer-template.py -v.

Fault controls for what #5514 will run against the published Orb:

* the consumer configuration is the template with only the release commit
  replaced, and its static structure check rejects every forbidden change;
* both observers accept only the v2.2.0 consumer branch, and an observer that
  still names the old branch or Orb is rejected;
* the consumer checkout check accepts only "release commit + generated config";
* the D08 in-job file check and the outside judgment pass only the expected
  outcome. The D08 Orb step is emulated with the checked-out script and real
  yamllint; that is a control of the judgment, not D08 evidence.

Expansion by the official compiler is checked in the setup contract job
(test-ci-contract.py). Local runs are supplementary.
"""
import copy
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
RELEASE = 'a1' * 20


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_').removesuffix('.py'), ROOT / '.circleci' / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


consumer = load('prepare-consumer.py')
d08 = load('verify-consumer-d08.py')
SOURCE = yaml.safe_load((ROOT / '.circleci/test-deploy.yml').read_text(encoding='utf-8'))


def git(repo, *arguments):
    return subprocess.check_output(
        ['git', '-c', 'user.name=test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false',
         *arguments], cwd=repo, text=True, stderr=subprocess.STDOUT).strip()


class Template(unittest.TestCase):
    def config(self):
        return yaml.safe_load(consumer.generate(RELEASE))

    def test_generation_changes_only_the_release_commit(self):
        template = consumer.TEMPLATE.read_text(encoding='utf-8')
        generated = consumer.generate(RELEASE)
        changed = [(a, b) for a, b in zip(template.splitlines(), generated.splitlines(), strict=True) if a != b]
        self.assertEqual(len(changed), consumer.PLACEHOLDERS)
        for before, after in changed:
            self.assertEqual(before.replace(consumer.PLACEHOLDER, RELEASE), after)
            self.assertEqual(before.strip(), 'RELEASE_COMMIT: ' + consumer.PLACEHOLDER)
        self.assertNotIn(consumer.PLACEHOLDER, generated)
        for bad in ('', 'main', RELEASE[:39], RELEASE.upper(), RELEASE + '0', None):
            with self.subTest(release=bad), self.assertRaisesRegex(AssertionError, 'full lowercase SHA'):
                consumer.generate(bad)
        with self.assertRaisesRegex(AssertionError, 'placeholders'):
            consumer.generate(RELEASE, template + '# ' + consumer.PLACEHOLDER + '\n')

    def test_generated_configuration_passes_the_structure_check(self):
        consumer.check_config(self.config(), SOURCE, RELEASE)

    def test_structure_check_rejects_forbidden_changes(self):
        def step(job, name):
            return next(s for s in job['steps'] if consumer.step_name(s) == name)

        def add_execute(c):
            c['jobs'][consumer.D08]['steps'].insert(5, {'yamllint/execute': {'targets': 'x.yml'}})

        def unobserved(c):
            c['jobs']['output-file-acceptance']['steps'].insert(3, 'yamllint/execute')

        def drop_case(c):
            steps = c['jobs']['boolean-acceptance']['steps']
            steps.remove(step(c['jobs']['boolean-acceptance'], 'Expect hidden-warning'))

        faults = [
            ('Unexpected top-level', lambda c: c.update(setup=True)),
            ('reference only the published', lambda c: c['orbs'].update(yamllint='orbss/yamllint@2.1.1')),
            ('reference only the published', lambda c: c['orbs'].update(yamllint='orbss/yamllint@2')),
            ('reference only the published', lambda c: c['orbs'].update(tools='circleci/orb-tools@12.5.0')),
            ('Forbidden mechanism', lambda c: c['workflows']['consumer-acceptance']['jobs'].append(
                {'minimal': {'name': 'again', 'context': 'CIRCLECI_ORBS'}})),
            ('Forbidden mechanism', lambda c: step(c['jobs']['minimal'], 'Record minimal workflow result')['run'].update(
                command='python .circleci/x.py && bash src/scripts/execute.sh')),
            ('Consumer job set changed', lambda c: c['jobs'].pop('boolean-acceptance')),
            ('verification identity changed', lambda c: c['jobs']['minimal']['environment'].update(
                VERIFICATION_SCOPE='source')),
            ('verification identity changed', lambda c: c['jobs'][consumer.D08]['environment'].update(
                RELEASE_COMMIT='b2' * 20)),
            ('executor changed', lambda c: c['jobs']['output-file-acceptance']['executor'].update(
                image='cimg/python:3.13')),
            ('Fixed yamllint versions changed', lambda c: c['jobs']['boolean-acceptance']['parameters'][
                'yamllint-version'].update(enum=['1.38.0'])),
            ('checkout or its verification is missing', lambda c: c['jobs']['minimal']['steps'].remove(
                consumer.CHECKOUT_STEP)),
            ('must not set parameters', lambda c: step(c['jobs']['output-file-acceptance'], 'Observe saving-empty')[
                'run'].update(environment={'PARAM_OUTPUT_FILE': 'x'})),
            ('unexpected command', lambda c: step(c['jobs'][consumer.D08], d08.CHECK_STEP)['run'].update(
                command='true')),
            ('step condition changed', lambda c: step(c['jobs'][consumer.D08], d08.CHECK_STEP)['run'].pop('when')),
            ('step condition changed', lambda c: step(c['jobs']['boolean-acceptance'], 'Expect config-file')[
                'run'].update(when='always')),
            ('observed cases differ', drop_case),
            ('observed cases differ', lambda c: step(c['jobs']['output-file-acceptance'], 'yamllint/execute')[
                'yamllint/execute'].update(format='standard')),
            ('unobserved Orb call', unobserved),
            ('D08 step sequence changed', add_execute),
            ('D08 step sequence changed', lambda c: c['jobs'][consumer.D08]['steps'].insert(
                4, {'run': {'name': 'Wrap yamllint', 'command': 'python .circleci/wrap.py'}})),
            ('exactly once with its fixed parameters', lambda c: step(c['jobs'][consumer.D08], 'yamllint/execute')[
                'yamllint/execute'].pop('format')),
            ('exactly once with its fixed parameters', lambda c: step(c['jobs'][consumer.D08], 'yamllint/execute')[
                'yamllint/execute'].update(strict=True)),
            ('D08 yamllint version changed', lambda c: c['jobs'][consumer.D08]['steps'].__setitem__(
                1, {'yamllint/install': {'version': '1.37.1'}})),
            ('D08 result artifact changed', lambda c: c['jobs'][consumer.D08]['steps'][6]['store_artifacts'].update(
                path='/tmp/other')),
            ('Consumer workflows changed', lambda c: c['workflows']['consumer-acceptance']['jobs'].append(
                consumer.D08)),
            ('Consumer workflows changed', lambda c: c['workflows']['consumer-acceptance']['jobs'].pop()),
            ('Consumer workflows changed', lambda c: c['workflows'].pop('d08-failed-step-artifact')),
        ]
        for message, change in faults:
            config = self.config()
            change(config)
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                consumer.check_config(config, SOURCE, RELEASE)
        with self.assertRaisesRegex(AssertionError, 'verification identity changed'):
            consumer.check_config(self.config(), SOURCE, 'b2' * 20)

    def test_inline_replaces_only_the_orb_reference(self):
        packed = 'version: 2.1\ncommands:\n  execute:\n    steps:\n      - run: |\n          line one\n\n          line two\n'
        text = consumer.generate(RELEASE)
        inlined = yaml.safe_load(consumer.inline(text, packed))
        expected = yaml.safe_load(text)
        expected['orbs']['yamllint'] = yaml.safe_load(packed)
        self.assertEqual(inlined, expected)
        self.assertTrue(consumer.inline(text, packed).startswith('# PRE-PUBLICATION STRUCTURE CHECK ONLY'))
        with self.assertRaisesRegex(AssertionError, 'one registry Orb reference'):
            consumer.inline(text.replace(consumer.ORB, 'orbss/yamllint@2.1.1'), packed)


class ObserverTargets(unittest.TestCase):
    """AC1: observers name the v2.2.0 branch and Orb; old references are rejected."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-consumer-')
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        git(self.repo, 'init', '-q')
        (self.repo / 'file').write_text('x\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-q', '-m', 'release')
        self.head = git(self.repo, 'rev-parse', 'HEAD')
        minor = '.'.join(map(str, sys.version_info[:2]))
        self.env = dict(VERIFICATION_SCOPE='consumer', RELEASE_COMMIT=self.head, CIRCLECI='true',
                        CIRCLE_SHA1=self.head, VERIFICATION_IMAGE='cimg/python:' + minor)

    def identities(self, branch):
        boolean, output = load('verify-boolean-parameters.py'), load('verify-output-file.py')
        environment = {**self.env, 'CIRCLE_BRANCH': branch}
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            with patch.dict(os.environ, environment), \
                    patch.multiple(output, REPO=self.repo, ROOT=self.repo):
                return boolean.identity(False), output.identity(False)
        finally:
            os.chdir(cwd)

    def test_observers_accept_only_the_v2_2_0_consumer_branch(self):
        if sys.version_info[:2] not in ((3, 13), (3, 14)):
            self.skipTest('observer identities are defined for the matrix Python versions')
        for record in self.identities('verify/yamllint-v2.2.0'):
            self.assertEqual(record['configured_orb'], 'orbss/yamllint@2.2.0')
            self.assertEqual((record['scope'], record['release_commit']), ('consumer', self.head))
        for branch in ('verify/yamllint-v2.1.1', 'main', ''):
            for index in (0, 1):
                with self.subTest(branch=branch, observer=index), \
                        self.assertRaisesRegex(RuntimeError, 'dedicated consumer branch'):
                    boolean, output = load('verify-boolean-parameters.py'), load('verify-output-file.py')
                    cwd = os.getcwd()
                    os.chdir(self.repo)
                    try:
                        with patch.dict(os.environ, {**self.env, 'CIRCLE_BRANCH': branch}), \
                                patch.multiple(output, REPO=self.repo, ROOT=self.repo):
                            (boolean, output)[index].identity(False)
                    finally:
                        os.chdir(cwd)

    def test_observer_with_an_old_reference_is_rejected(self):
        real = consumer.load_module
        for name in ('verify-boolean-parameters.py', 'verify-output-file.py'):
            for field, old in (('CONSUMER_BRANCH', 'verify/yamllint-v2.1.1'), ('CONSUMER_ORB', 'orbss/yamllint@2.1.1')):
                def stale(requested, name=name, field=field, old=old):
                    module = real(requested)
                    if requested == name:
                        setattr(module, field, old)
                    return module
                with self.subTest(observer=name, field=field), patch.object(consumer, 'load_module', stale), \
                        self.assertRaisesRegex(AssertionError, 'still targets another consumer branch or Orb'):
                    consumer.check_config(yaml.safe_load(consumer.generate(RELEASE)), SOURCE, RELEASE)
        for name in ('verify-boolean-parameters.py', 'verify-output-file.py'):
            self.assertNotIn('2.1.1', (ROOT / '.circleci' / name).read_text(encoding='utf-8'))

    def test_output_observer_reads_the_consumer_job(self):
        output = load('verify-output-file.py')
        config = self.repo / '.circleci/config.yml'
        config.parent.mkdir()
        config.write_text(consumer.generate(RELEASE), encoding='utf-8')
        with patch.object(output, 'REPO', self.repo):
            cases = output.configured_cases('consumer')
        self.assertEqual(list(cases), list(output.CASES))
        for case, values in cases.items():
            self.assertEqual(values, output.typed(case, output.CONFIG_ABSOLUTE))


class ConsumerCheckout(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-consumer-')
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        git(self.repo, 'init', '-q')
        template = self.repo / '.circleci/consumer/config.template.yml'
        template.parent.mkdir(parents=True)
        template.write_text(consumer.TEMPLATE.read_text(encoding='utf-8'), encoding='utf-8')
        (self.repo / '.circleci/config.yml').write_text('version: 2.1\nsetup: true\n')
        (self.repo / 'README.md').write_text('release\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-q', '-m', 'release')
        self.release = git(self.repo, 'rev-parse', 'HEAD')

    def commit_config(self, text=None, extra=None):
        (self.repo / '.circleci/config.yml').write_text(
            consumer.generate(self.release) if text is None else text, encoding='utf-8')
        if extra:
            (self.repo / extra).write_text('changed\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-q', '-m', 'consumer')

    def verify(self, **changes):
        environment = dict(VERIFICATION_SCOPE='consumer', CIRCLECI='true', CIRCLE_BRANCH=consumer.BRANCH,
                           RELEASE_COMMIT=self.release, CIRCLE_SHA1=git(self.repo, 'rev-parse', 'HEAD'))
        environment.update(changes)
        with patch.object(consumer, 'REPO', self.repo):
            return consumer.verify_checkout(environment)

    def test_release_commit_plus_generated_configuration_is_accepted(self):
        self.commit_config()
        record = self.verify()
        self.assertEqual(record['release_commit'], self.release)
        self.assertEqual(record['configured_orb'], 'orbss/yamllint@2.2.0')

    def test_other_checkouts_are_rejected(self):
        self.commit_config()
        for message, changes in (('dedicated consumer branch', dict(CIRCLE_BRANCH='verify/yamllint-v2.1.1')),
                                 ('dedicated consumer branch', dict(CIRCLE_BRANCH='main')),
                                 ('VERIFICATION_SCOPE=consumer', dict(VERIFICATION_SCOPE='source')),
                                 ('requires CircleCI', dict(CIRCLECI='')),
                                 ('does not match the CI revision', dict(CIRCLE_SHA1=self.release)),
                                 ('exactly one commit after', dict(RELEASE_COMMIT='c3' * 20))):
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                self.verify(**changes)
        (self.repo / 'README.md').write_text('dirty\n')
        with self.assertRaisesRegex(AssertionError, 'dirty'):
            self.verify()
        git(self.repo, 'checkout', '-q', '--', 'README.md')
        self.commit_config(extra='second-commit.txt')
        with self.assertRaisesRegex(AssertionError, 'exactly one commit after'):
            self.verify()

    def test_changed_files_or_edited_configuration_are_rejected(self):
        self.commit_config(extra='README.md')
        with self.assertRaisesRegex(AssertionError, r'Only \.circleci/config\.yml may differ'):
            self.verify()
        git(self.repo, 'reset', '-q', '--hard', self.release)
        edited = consumer.generate(self.release).replace('format: parsable', 'format: standard', 1)
        self.commit_config(text=edited)
        with self.assertRaisesRegex(AssertionError, 'only the release commit replaced'):
            self.verify()


class D08(unittest.TestCase):
    """The in-job file check and the outside judgment; the Orb step is emulated."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-d08-')
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.work, self.results, self.evidence = base / 'work', base / 'results', base / 'evidence'
        self.work.mkdir()
        self.bin = base / 'bin'
        self.bin.mkdir()
        real = self.bin / 'yamllint'
        real.write_text(f'#!{sys.executable}\nfrom yamllint.cli import run\nrun()\n')
        real.chmod(0o755)
        (self.bin / 'python3').symlink_to(sys.executable)
        patcher = patch.multiple(d08, ROOT=self.work, RESULT_DIR=self.results, EVIDENCE_DIR=self.evidence,
                                 YAMLLINT=importlib.metadata.version('yamllint'))
        patcher.start()
        self.addCleanup(patcher.stop)
        with patch.dict(os.environ, {'EXPECTED_YAMLLINT': d08.YAMLLINT}):
            d08.prepare()

    def execute(self, **changes):
        """Emulated Orb step: the checked-out script with the template's typed parameters."""
        values = {**d08.EXECUTE, 'output_file': str(d08.result_path()), **changes}
        environment = {k: v for k, v in os.environ.items() if not k.startswith('PARAM_') and k not in (
            'BASH_ENV', 'ENV', 'CDPATH', 'YAMLLINT_CONFIG_FILE', 'GITHUB_ACTIONS', 'GITHUB_WORKFLOW')}
        environment.update(
            PATH=f'{self.bin}{os.pathsep}{environment.get("PATH", "")}', PARAM_TARGETS=values['targets'],
            PARAM_CONFIG_FILE='', PARAM_CONFIG_DATA=values['config_data'], PARAM_STRICT='false',
            PARAM_NO_WARNINGS='false', PARAM_LIST_FILES='false', PARAM_FORMAT=values['format'],
            PARAM_OUTPUT_FILE=values['output_file'])
        return subprocess.run([BASH, str(ROOT / 'src/scripts/execute.sh')], cwd=self.work, env=environment,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=60, check=False)

    def check(self):
        with patch('builtins.print'), patch.dict(os.environ, {
                'CIRCLE_JOB': d08.JOB, 'CIRCLE_SHA1': 'c3' * 20, 'RELEASE_COMMIT': RELEASE,
                'CIRCLE_BUILD_URL': 'https://circleci.example/job/1'}):
            d08.check()
        return json.loads((self.evidence / d08.CHECK_EVIDENCE).read_text())

    def test_real_lint_error_exits_1_and_the_file_check_passes(self):
        result = self.execute()
        self.assertEqual(result.returncode, d08.EXPECTED_EXIT, result.stderr)
        self.assertEqual(result.stdout, d08.EXPECTED)
        self.assertEqual(result.stderr, b'')
        evidence = self.check()
        self.assertEqual((evidence['result'], evidence['problems']), ('PASS', []))
        self.assertEqual(evidence['saved_sha256'], d08.digest(d08.EXPECTED))

    def rejected(self, message):
        with self.assertRaisesRegex(RuntimeError, message):
            self.check()
        self.assertEqual(json.loads((self.evidence / d08.CHECK_EVIDENCE).read_text())['result'], 'FAIL')

    def test_file_check_rejects_a_missing_file(self):
        self.rejected('the result file does not exist')  # the Orb step did not run
        self.assertEqual(self.execute(output_file=str(self.results / 'missing-parent' / 'lint.txt')).returncode, 2)
        self.rejected('the result file does not exist')  # the Orb refused the destination

    def test_file_check_rejects_a_successful_execute(self):
        (self.work / d08.FIXTURE).write_bytes(b'---\nmessage: clean\n')
        self.assertEqual(self.execute().returncode, 0)
        self.rejected('the fixture is missing or was changed; the result file content differs')

    def test_file_check_rejects_different_content_and_other_entries(self):
        self.assertEqual(self.execute(format='standard').returncode, 1)
        self.rejected('content differs')
        d08.result_path().write_bytes(d08.EXPECTED + b'\n')
        self.rejected('content differs')
        d08.result_path().write_bytes(d08.EXPECTED)
        self.check()
        (self.results / '.yamllint-orb-output-0123456789abcdef.tmp').write_bytes(d08.EXPECTED)
        self.rejected('unexpected entries next to the result file')
        (self.results / '.yamllint-orb-output-0123456789abcdef.tmp').unlink()
        d08.result_path().unlink()
        d08.result_path().symlink_to(self.work / d08.FIXTURE)
        self.rejected('not a regular file')

    # --- outside judgment ---------------------------------------------------

    @staticmethod
    def shown(*names):
        """Step entries as the UI shows them for the expected outcome."""
        return [{'name': name, 'status': 'failed' if name == d08.BODY_STEP else 'success'} for name in names]

    def complete(self):
        body = self.execute()
        self.assertEqual(body.returncode, 1)
        # What the UI shows as the output of the failed body step.
        self.body_output = (body.stdout + body.stderr).decode('utf-8').removesuffix('\n')
        evidence = self.check()
        # The judgment is defined for the D08 runtime; this emulation may use another one.
        evidence['python'] = '3.14.0'
        record = json.loads((ROOT / '.circleci/consumer/d08-record.template.json').read_text(encoding='utf-8'))
        record.update(job_url='https://circleci.example/job/1', consumer_commit='c3' * 20, release_commit=RELEASE,
                      confirmed_by='reviewer', confirmed_at='2026-11-20T10:00:00+09:00', job_status='failed')
        record['execute_step'].update(identified_by='unique step name', status='failed', exit_code=1,
                                      failure_reason=self.body_output)
        self.assertEqual([step['name'] for step in record['steps']], d08.UI_STEPS)
        record['steps'] = self.shown(*d08.UI_STEPS)
        record['in_job_check']['status'] = 'success'
        record['artifact']['retrieved_how'] = 'downloaded from the Artifacts tab'
        return record, d08.result_path().read_bytes(), evidence

    def test_judgment_passes_only_the_complete_expected_outcome(self):
        record, artifact, evidence = self.complete()
        self.assertEqual(d08.judge(record, artifact, evidence), ('PASS', []))
        template = json.loads((ROOT / '.circleci/consumer/d08-record.template.json').read_text(encoding='utf-8'))
        self.assertEqual(d08.judge(template, None, None)[0], 'UNCONFIRMED')

        def step(r, name):
            return next(s for s in r['steps'] if s['name'] == name)

        faults = [
            ('FAIL', 'body step did not fail', lambda r, e: (r['execute_step'].update(status='success', exit_code=0),
                                                             step(r, d08.BODY_STEP).update(status='success'))),
            ('FAIL', 'exit status is not 1', lambda r, e: r['execute_step'].update(exit_code=2)),
            ('FAIL', 'exit status is not 1', lambda r, e: r['execute_step'].update(exit_code='1')),
            ('FAIL', 'exit status is not 1', lambda r, e: r['execute_step'].update(exit_code=True)),
            ('FAIL', 'exit status is not 1', lambda r, e: r['execute_step'].update(exit_code=1.0)),
            ('FAIL', 'another step did not succeed', lambda r, e: step(r, 'Install yamllint').update(status='failed')),
            ('FAIL', 'another step did not succeed', lambda r, e: step(r, d08.VERSION_STEP).update(status='failed')),
            ('FAIL', 'another step did not succeed', lambda r, e: r['steps'][-1].update(status='failed')),
            ('FAIL', '"Execute yamllint" must be recorded 1 time',
             lambda r, e: r['steps'].append({'name': d08.BODY_STEP, 'status': 'failed'})),
            ('FAIL', '"Check D08 result file" must be recorded 1 time',
             lambda r, e: r['steps'].remove(step(r, d08.CHECK_STEP))),
            ('FAIL', 'out of order', lambda r, e: r['steps'].insert(0, r['steps'].pop(6))),
            ('FAIL', 'not identified as', lambda r, e: r['execute_step'].update(name='Show yamllint version')),
            ('FAIL', 'directly follow', lambda r, e: r['execute_step'].update(preceded_by='Install yamllint')),
            ('FAIL', 'identification method', lambda r, e: r['execute_step'].update(identified_by='the job is red')),
            ('FAIL', 'in-job result file check did not succeed', lambda r, e: r['in_job_check'].update(status='failed')),
            ('FAIL', 'must be failed in CircleCI', lambda r, e: r.update(job_status='success')),
            ('FAIL', 'not for the D08 job', lambda r, e: r.update(job_name='minimal')),
            ('FAIL', 'CircleCI UI', lambda r, e: r.update(method='API')),
            ('FAIL', 'full commit SHA', lambda r, e: r.update(release_commit='v2.2.0')),
            ('FAIL', 'credentials', lambda r, e: r.update(notes='Authorization: Bearer abc')),
            ('FAIL', 'credentials', lambda r, e: r['execute_step'].update(output_url='https://x')),
            ('FAIL', 'artifact path', lambda r, e: r['artifact'].update(path='yamllint-d08-evidence/d08-check.json')),
            ('FAIL', 'evidence is not PASS', lambda r, e: e.update(result='FAIL', problems=['x'])),
            ('FAIL', 'executed fixture differs', lambda r, e: e.update(fixture_sha256='0' * 64)),
            ('FAIL', 'typed parameters differ', lambda r, e: e.update(typed_parameters={})),
            ('FAIL', 'saved file hash', lambda r, e: e.update(saved_sha256='0' * 64)),
            ('FAIL', 'not from yamllint', lambda r, e: e.update(yamllint='0.0.0')),
            ('FAIL', 'not from Python 3.14', lambda r, e: e.update(python='3.13.9')),
            ('FAIL', 'not from the D08 job', lambda r, e: e['ci'].update(CIRCLE_JOB='minimal')),
            ('FAIL', 'different commits', lambda r, e: r.update(consumer_commit='d4' * 20)),
            ('FAIL', 'different release commits', lambda r, e: r.update(release_commit='d4' * 20)),
            ('FAIL', 'another job URL', lambda r, e: r.update(job_url='https://circleci.example/job/2')),
            ('UNCONFIRMED', 'exit_code is not confirmed', lambda r, e: r['execute_step'].update(exit_code='unconfirmed')),
            ('UNCONFIRMED', 'status of step', lambda r, e: step(r, 'Install yamllint').update(status='unconfirmed')),
            ('UNCONFIRMED', 'confirmed_by', lambda r, e: r.update(confirmed_by='')),
            ('UNCONFIRMED', 'confirmed_by', lambda r, e: r.update(confirmed_by='   ')),
            ('UNCONFIRMED', 'confirmed_at', lambda r, e: r.update(confirmed_at='\t')),
            ('UNCONFIRMED', 'artifact.retrieved_how', lambda r, e: r['artifact'].update(retrieved_how=' ')),
            ('UNCONFIRMED', 'failure_reason', lambda r, e: r['execute_step'].update(failure_reason=None)),
            ('FAIL', 'steps are not recorded', lambda r, e: r.update(steps=[])),
        ]
        for verdict, message, change in faults:
            changed_record, changed_evidence = copy.deepcopy(record), copy.deepcopy(evidence)
            changed_evidence['yamllint'] = d08.YAMLLINT
            change(changed_record, changed_evidence)
            actual, reasons = d08.judge(changed_record, artifact, changed_evidence)
            with self.subTest(message=message):
                self.assertEqual(actual, verdict, reasons)
                self.assertTrue(any(message in reason for reason in reasons), reasons)
        for changed, verdict, message in ((b'', 'FAIL', 'artifact differs'), (artifact + b'x', 'FAIL', 'artifact differs'),
                                          (None, 'UNCONFIRMED', 'artifact was not retrieved')):
            actual, reasons = d08.judge(record, changed, evidence)
            self.assertEqual(actual, verdict)
            self.assertTrue(any(message in reason for reason in reasons), reasons)
        actual, reasons = d08.judge(record, artifact, None)
        self.assertEqual((actual, reasons), ('UNCONFIRMED', ['the in-job check evidence was not retrieved']))

    def test_judgment_requires_the_expected_failure_reason(self):
        record, artifact, evidence = self.complete()
        # The emulated Orb step shows exactly the expected lint error: the reason to confirm.
        self.assertEqual(self.body_output, d08.EXPECTED_REASON)
        self.assertEqual(d08.EXPECTED_REASON + '\n', d08.EXPECTED.decode('utf-8'))
        orb_error = "yamllint Orb: output_file: the result file '/tmp/yamllint-d08-results/lint.txt' was not created"
        cases = [
            ('FAIL', 'the output_file save failed'),  # another reason
            ('FAIL', 'lint error'),  # a summary, not the output shown
            ('FAIL', 'Exited with code exit status 1'),  # only the exit status
            ('FAIL', d08.EXPECTED_REASON + '\n' + orb_error),  # additional output
            ('FAIL', orb_error),
            ('FAIL', d08.EXPECTED_REASON.replace('2:20', '2:21')),  # another position
            ('FAIL', d08.EXPECTED_REASON.replace('[error]', '[warning]')),  # another level
            ('FAIL', d08.EXPECTED_REASON.replace('(trailing-spaces)', '(line-length)')),  # another rule
            ('FAIL', d08.EXPECTED_REASON + ' '),  # not exactly the output
            ('FAIL', 1), ('FAIL', [d08.EXPECTED_REASON]), ('FAIL', {'output': d08.EXPECTED_REASON}),
            ('UNCONFIRMED', ''), ('UNCONFIRMED', '   '), ('UNCONFIRMED', '\n\t'), ('UNCONFIRMED', 'unconfirmed'),
            ('UNCONFIRMED', None),
        ]
        for verdict, reason in cases:
            changed = copy.deepcopy(record)
            changed['execute_step']['failure_reason'] = reason
            actual, reasons = d08.judge(changed, artifact, evidence)
            with self.subTest(reason=reason):
                self.assertEqual(actual, verdict, reasons)
                self.assertTrue(any('failure' in message for message in reasons), reasons)
        del record['execute_step']['failure_reason']
        self.assertEqual(d08.judge(record, artifact, evidence)[0], 'UNCONFIRMED')

    def test_judgment_requires_every_step_the_ui_shows(self):
        record, artifact, evidence = self.complete()
        self.assertEqual([name for name in d08.UI_STEPS if name in d08.JOB_STEPS], d08.JOB_STEPS)
        ui, upload = d08.UI_STEPS, d08.SPECIAL_STEPS['store_artifacts']
        cases = [
            ('only the six named run steps', 'FAIL', '"Spin up environment" must be recorded 1', self.shown(*d08.JOB_STEPS)),
            ('both uploads left out', 'FAIL', f'"{upload}" must be recorded 2', self.shown(*ui[:-2])),
            ('one upload left out', 'FAIL', f'"{upload}" must be recorded 2', self.shown(*ui[:-1])),
            ('an extra upload', 'FAIL', f'"{upload}" must be recorded 2', self.shown(*ui, upload)),
            ('a step the job does not have', 'FAIL', 'unexpected step "Restoring cache"',
             self.shown(*ui[:3], 'Restoring cache', *ui[3:])),
            ('environment steps swapped', 'FAIL', 'out of order', self.shown(ui[1], ui[0], *ui[2:])),
            ('upload before the check', 'FAIL', 'out of order', self.shown(*ui[:8], ui[9], ui[8], ui[10])),
            ('an entry without a name', 'FAIL', 'unexpected step "None"',
             self.shown(*ui) + [{'status': 'success'}]),
            ('an entry that is not an object', 'FAIL', 'unexpected step "None"', self.shown(*ui) + [upload]),
            ('a name that is not text', 'FAIL', "unexpected step \"['x']\"",
             self.shown(*ui) + [{'name': ['x'], 'status': 'success'}]),
        ]
        for index, name in enumerate(ui):
            if name not in ui[:index]:
                cases.append((f'"{name}" left out', 'FAIL', f'"{name}" must be recorded',
                              self.shown(*ui[:index], *ui[index + 1:])))
            if name != d08.BODY_STEP:
                failed = self.shown(*ui)
                failed[index]['status'] = 'failed'
                cases.append((f'step {index} "{name}" failed', 'FAIL', 'another step did not succeed', failed))
                blank = self.shown(*ui)
                blank[index]['status'] = ' '
                cases.append((f'step {index} "{name}" not confirmed', 'UNCONFIRMED', 'status of step', blank))
        for label, verdict, message, steps in cases:
            changed = copy.deepcopy(record)
            changed['steps'] = steps
            actual, reasons = d08.judge(changed, artifact, evidence)
            with self.subTest(label):
                self.assertEqual(actual, verdict, reasons)
                self.assertTrue(any(message in reason for reason in reasons), reasons)
        self.assertEqual(d08.judge(record, artifact, evidence), ('PASS', []))

    def test_judge_command_exits_0_only_for_pass(self):
        record, artifact, evidence = self.complete()
        evidence['yamllint'] = '1.38.0'
        files = {name: self.work / name for name in ('record.json', 'lint.txt', 'check.json')}
        files['lint.txt'].write_bytes(artifact)
        files['check.json'].write_text(json.dumps(evidence))

        def run(changed):
            files['record.json'].write_text(json.dumps(changed))
            return subprocess.run([sys.executable, str(ROOT / '.circleci/verify-consumer-d08.py'), 'judge',
                                   '--record', str(files['record.json']), '--artifact', str(files['lint.txt']),
                                   '--check-evidence', str(files['check.json'])],
                                  capture_output=True, text=True, timeout=60, check=False)
        passed = run(record)
        self.assertEqual((passed.returncode, json.loads(passed.stdout)['d08']), (0, 'PASS'), passed.stdout)
        failed = run({**record, 'job_status': 'success'})
        self.assertEqual((failed.returncode, json.loads(failed.stdout)['d08']), (1, 'FAIL'))
        unknown = run({**record, 'confirmed_by': 'unconfirmed'})
        self.assertEqual((unknown.returncode, json.loads(unknown.stdout)['d08']), (1, 'UNCONFIRMED'))


if __name__ == '__main__':
    unittest.main()
