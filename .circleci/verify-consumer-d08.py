#!/usr/bin/env python3
"""D08: result file and artifact after a failed real yamllint/execute step (#5512).

Used by the job d08-failed-lint-artifact of consumer/config.template.yml,
which references the published Orb directly. The job is EXPECTED TO FAIL:
its single yamllint/execute step lints one fixed fixture with a lint error,
saves the output with output_file and must exit 1. Nothing is placed before
the yamllint body, and nothing converts its exit status.

  prepare  before the Orb step: write the fixture, create the result directory.
  check    after it, with "when: always": judge only the result file (present,
           a regular file, exactly the expected bytes, nothing else created).
           A step cannot read the exit status of the previous step, so the
           failed step and its exit status 1 are confirmed in the CircleCI UI.
  judge    outside the job: combine the UI record (consumer/d08-record.template.json),
           the downloaded artifact and the downloaded check evidence. Prints
           PASS only when every condition holds; anything else is FAIL or
           UNCONFIRMED and exits non-zero. The record must state the failure
           reason shown in the UI, which must be the expected lint error
           output, and the result of every step the UI shows for the job.

A red job alone is never a pass, and PASS here is not a claim about any
other failure path. Local runs are supplementary.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys

ROOT = Path.cwd()
FIXTURE = 'd08-fixtures/error.yml'
FIXTURE_BYTES = b'---\nmessage: lint error  \n'
RESULT_DIR = Path('/tmp/yamllint-d08-results')
RESULT_NAME = 'lint.txt'
EVIDENCE_DIR = Path('/tmp/yamllint-d08-evidence')
YAMLLINT = '1.38.0'
IMAGE = 'cimg/python:3.14'
# The typed parameters of the single yamllint/execute call in the template.
EXECUTE = {'targets': FIXTURE, 'config_data': 'extends: default', 'format': 'parsable',
           'output_file': str(RESULT_DIR / RESULT_NAME)}
# yamllint 1.38.0, "extends: default", parsable: one trailing-spaces error.
EXPECTED = b'd08-fixtures/error.yml:2:20: [error] trailing spaces (trailing-spaces)\n'
EXPECTED_EXIT = 1
# The failure reason to confirm in the UI: the whole output shown for the
# failed body step (without CircleCI's closing exit-code line). With output_file
# the Orb forwards yamllint's stdout to the step log, so it is the lint error.
EXPECTED_REASON = EXPECTED.decode('utf-8').removesuffix('\n')
BODY_STEP = 'Execute yamllint'
VERSION_STEP = 'Show yamllint version'
CHECK_STEP = 'Check D08 result file'
# Named run steps of the job, in order (the compiled configuration is checked
# against this list before publication).
JOB_STEPS = ['Install yamllint', 'Verify consumer checkout', 'Prepare D08 fixture and result directory',
             VERSION_STEP, BODY_STEP, CHECK_STEP]
# CircleCI's own steps, named as the UI shows them in this repository's CI
# jobs (Docker executor): two before the configured steps, and one for each
# configured `checkout` and `store_artifacts` step.
ENVIRONMENT_STEPS = ['Spin up environment', 'Preparing environment variables']
SPECIAL_STEPS = {'checkout': 'Checkout code', 'store_artifacts': 'Uploading artifacts'}
# Every step the UI shows for the D08 job, in order. The record lists all of
# them; a missing, extra or reordered step is not a pass.
UI_STEPS = [*ENVIRONMENT_STEPS, SPECIAL_STEPS['checkout'], *JOB_STEPS,
            SPECIAL_STEPS['store_artifacts'], SPECIAL_STEPS['store_artifacts']]
ARTIFACT = 'yamllint-d08-results/lint.txt'
CHECK_EVIDENCE = 'd08-check.json'
JOB = 'd08-failed-lint-artifact'
SECRET = re.compile(r'token|authorization|password|secret|cookie|output_url|api[_-]?key|private[_-]?key', re.I)
UNCONFIRMED = ('', None, 'unconfirmed', 'UNCONFIRMED', 'TODO')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def result_path():
    return RESULT_DIR / RESULT_NAME


def prepare():
    version = importlib.metadata.version('yamllint')
    if version != YAMLLINT or os.environ.get('EXPECTED_YAMLLINT') != YAMLLINT:
        raise RuntimeError(f'D08 is defined for yamllint {YAMLLINT}; installed {version}')
    for path in (ROOT / 'd08-fixtures', RESULT_DIR, EVIDENCE_DIR):
        if os.path.lexists(path):
            raise RuntimeError(f'Already exists; use a fresh checkout/job: {path}')
    fixture = ROOT / FIXTURE
    fixture.parent.mkdir()
    fixture.write_bytes(FIXTURE_BYTES)
    RESULT_DIR.mkdir(parents=True)


def file_problems():
    """Why the result file is not the expected D08 output (empty when it is)."""
    problems = []
    fixture = ROOT / FIXTURE
    if not fixture.is_file() or fixture.read_bytes() != FIXTURE_BYTES:
        problems.append('the fixture is missing or was changed')
    path = result_path()
    if not os.path.lexists(path):
        problems.append('the result file does not exist')
    elif not stat.S_ISREG(os.lstat(path).st_mode):
        problems.append('the result entry is not a regular file')
    elif path.read_bytes() != EXPECTED:
        problems.append('the result file content differs from the expected lint error output')
    entries = sorted(os.listdir(RESULT_DIR)) if RESULT_DIR.is_dir() else None
    if entries is None:
        problems.append('the result directory does not exist')
    elif [name for name in entries if name != RESULT_NAME]:
        problems.append('unexpected entries next to the result file: '
                        + ', '.join(name for name in entries if name != RESULT_NAME))
    return problems


def check():
    problems = file_problems()
    path = result_path()
    fields = ('CIRCLE_SHA1', 'CIRCLE_BUILD_URL', 'CIRCLE_BUILD_NUM', 'CIRCLE_WORKFLOW_ID',
              'CIRCLE_PIPELINE_ID', 'CIRCLE_JOB', 'CIRCLE_BRANCH', 'CIRCLE_TAG')
    saved = path.read_bytes() if path.is_file() and not path.is_symlink() else None
    record = dict(
        check='D08 in-job result file check', result='FAIL' if problems else 'PASS', problems=problems,
        scope=('Result file only. The exit status of the yamllint/execute step is not visible to this '
               'step; confirm the failed "Execute yamllint" step and its exit status 1 in the CircleCI UI.'),
        release_commit=os.environ.get('RELEASE_COMMIT', ''), fixture=FIXTURE,
        fixture_sha256=digest(FIXTURE_BYTES), typed_parameters=EXECUTE,
        expected_sha256=digest(EXPECTED), expected_bytes=len(EXPECTED),
        saved_sha256=digest(saved) if saved is not None else None,
        saved_bytes=len(saved) if saved is not None else None,
        yamllint=importlib.metadata.version('yamllint'), python=platform.python_version(),
        ci={key: os.environ.get(key, '') for key in fields})
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / CHECK_EVIDENCE).write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    if problems:
        raise RuntimeError('D08 result file check failed: ' + '; '.join(problems))


def strings(value, path=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path + '.' + str(key), str(key)
            yield from strings(item, path + '.' + str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f'{path}[{index}]')
    elif isinstance(value, str):
        yield path, value


def judge(record, artifact, evidence):
    """Return (verdict, reasons). verdict is PASS, FAIL or UNCONFIRMED."""
    failed, unknown = [], []

    def need(condition, message):
        if not condition:
            failed.append(message)

    def known(value, name):
        # A blank value is an entry that was not filled in.
        if value in UNCONFIRMED or (isinstance(value, str) and not value.strip()):
            unknown.append(name + ' is not confirmed')
            return False
        return True

    for where, text in strings(record):
        need(not SECRET.search(text), f'the record must not contain credentials or output URLs ({where})')
    for name in ('job_url', 'confirmed_by', 'confirmed_at', 'method', 'consumer_commit', 'release_commit'):
        known(record.get(name), name)
    need(record.get('method') in UNCONFIRMED or record.get('method') == 'CircleCI UI',
         'the adopted confirmation method is the CircleCI UI')
    for name in ('consumer_commit', 'release_commit'):
        value = record.get(name)
        need(value in UNCONFIRMED or re.fullmatch(r'[0-9a-f]{40}', str(value)), name + ' must be a full commit SHA')
    need(record.get('job_name') == JOB, 'the record is not for the D08 job')
    if known(record.get('job_status'), 'job_status'):
        need(record['job_status'] == 'failed', 'the D08 job must be failed in CircleCI')

    body = record.get('execute_step') or {}
    if known(body.get('status'), 'execute_step.status'):
        need(body['status'] == 'failed', 'the yamllint/execute body step did not fail')
    if known(body.get('exit_code'), 'execute_step.exit_code'):
        # A number, not text or true/1.0 (which equal 1 in Python).
        need(type(body['exit_code']) is int and body['exit_code'] == EXPECTED_EXIT,
             f'the body step exit status is not {EXPECTED_EXIT}')
    need(body.get('name') == BODY_STEP, 'the failed step is not identified as "Execute yamllint"')
    need(body.get('preceded_by') == VERSION_STEP, 'the body step must directly follow "Show yamllint version"')
    if known(body.get('identified_by'), 'execute_step.identified_by'):
        need(body['identified_by'] in ('unique step name', 'step command compared with the packed Orb script'),
             'the body step identification method is not an adopted one')
    if known(body.get('failure_reason'), 'execute_step.failure_reason'):
        need(body['failure_reason'] == EXPECTED_REASON,
             'the failure reason shown in the UI is not the expected lint error output: ' + EXPECTED_REASON)

    steps = record.get('steps')
    if not isinstance(steps, list) or not steps:
        unknown.append('steps are not recorded')
        steps = []
    steps = [step if isinstance(step, dict) else {} for step in steps]
    names = [step.get('name') for step in steps]
    for name in dict.fromkeys(UI_STEPS):
        need(names.count(name) == UI_STEPS.count(name),
             f'step "{name}" must be recorded {UI_STEPS.count(name)} time(s) as the UI shows it, '
             f'not {names.count(name)}')
    for name in dict.fromkeys(map(str, names)):
        need(name in UI_STEPS, f'unexpected step "{name}": the D08 job has no such step')
    if sorted(map(str, names)) == sorted(UI_STEPS):
        need(names == UI_STEPS, 'the recorded steps are out of order')
    for step in steps:
        name, status = step.get('name'), step.get('status')
        if not known(status, f'status of step "{name}"'):
            continue
        if name == BODY_STEP:
            need(status == 'failed', 'the recorded "Execute yamllint" step did not fail')
        else:
            need(status == 'success', f'another step did not succeed: "{name}" is {status}')

    check_step = record.get('in_job_check') or {}
    need(check_step.get('step') == CHECK_STEP, 'the in-job check step is not recorded')
    if known(check_step.get('status'), 'in_job_check.status'):
        need(check_step['status'] == 'success', 'the in-job result file check did not succeed')

    retrieved = record.get('artifact') or {}
    need(retrieved.get('path') == ARTIFACT, 'the artifact path is not the D08 result file')
    known(retrieved.get('retrieved_how'), 'artifact.retrieved_how')
    if artifact is None:
        unknown.append('the artifact was not retrieved')
    else:
        need(artifact == EXPECTED, 'the retrieved artifact differs from the expected lint error output')
    if evidence is None:
        unknown.append('the in-job check evidence was not retrieved')
    else:
        need(evidence.get('result') == 'PASS' and evidence.get('problems') == [],
             'the in-job check evidence is not PASS')
        need(evidence.get('fixture_sha256') == digest(FIXTURE_BYTES) and evidence.get('fixture') == FIXTURE,
             'the executed fixture differs')
        need(evidence.get('typed_parameters') == EXECUTE, 'the typed parameters differ')
        need(evidence.get('saved_sha256') == digest(EXPECTED), 'the saved file hash in the evidence differs')
        need(evidence.get('yamllint') == YAMLLINT, 'the evidence is not from yamllint ' + YAMLLINT)
        need(str(evidence.get('python', '')).startswith('3.14.'), 'the evidence is not from Python 3.14')
        ci = evidence.get('ci') or {}
        need(ci.get('CIRCLE_JOB') == JOB, 'the evidence is not from the D08 job')
        for name, field in (('consumer_commit', 'CIRCLE_SHA1'),):
            if record.get(name) not in UNCONFIRMED:
                need(ci.get(field) == record[name], 'the evidence and the record name different commits')
        if record.get('release_commit') not in UNCONFIRMED:
            need(evidence.get('release_commit') == record['release_commit'],
                 'the evidence and the record name different release commits')
        if record.get('job_url') not in UNCONFIRMED:
            need(ci.get('CIRCLE_BUILD_URL') == record['job_url'], 'the evidence is from another job URL')
    if failed:
        return 'FAIL', failed + unknown
    if unknown:
        return 'UNCONFIRMED', unknown
    return 'PASS', []


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['prepare', 'check', 'judge'])
    parser.add_argument('--record', type=Path, help='judge: completed copy of consumer/d08-record.template.json')
    parser.add_argument('--artifact', type=Path, help='judge: downloaded ' + ARTIFACT)
    parser.add_argument('--check-evidence', type=Path, help='judge: downloaded yamllint-d08-evidence/' + CHECK_EVIDENCE)
    args = parser.parse_args(argv[1:])
    if args.action == 'prepare':
        prepare()
    elif args.action == 'check':
        check()
    else:
        if args.record is None:
            raise RuntimeError('judge needs --record')
        record = json.loads(args.record.read_text(encoding='utf-8'))
        artifact = args.artifact.read_bytes() if args.artifact and args.artifact.is_file() else None
        evidence = (json.loads(args.check_evidence.read_text(encoding='utf-8'))
                    if args.check_evidence and args.check_evidence.is_file() else None)
        verdict, reasons = judge(record, artifact, evidence)
        print(json.dumps(dict(d08=verdict, reasons=reasons,
                              note='PASS covers D08 only; the CircleCI job itself stays failed.'), indent=2))
        return 0 if verdict == 'PASS' else 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print('yamllint D08: ' + str(error), file=sys.stderr)
        sys.exit(1)
