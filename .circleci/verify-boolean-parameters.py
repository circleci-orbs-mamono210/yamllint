#!/usr/bin/env python3
"""Observe actual Orb calls and raw parameter values without rewriting them."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys

ROOT = Path.cwd()
EVIDENCE = ROOT / '.boolean-evidence'
STATE = EVIDENCE / 'state.json'
DATA = 'extends: default\nrules:\n  line-length: disable\n'
WARN_DATA = 'extends: default\nrules:\n  line-length:\n    max: 30\n    level: warning\n'
LIST_DATA = 'extends: relaxed\nyaml-files: ["*.yml"]\nignore: ["consumer-fixtures/listing/skip.yml"]\n'
CASES = {
    'config-file': (['--config-file', 'consumer-fixtures/config.yml', '--', 'consumer-fixtures/long.yml'], 0, 'empty'),
    'config-data': (['--config-data', DATA, '--', 'consumer-fixtures/long.yml'], 0, 'empty'),
    'visible-strict-warning': (['--config-data', WARN_DATA, '--strict', '--format', 'parsable', '--', 'consumer-fixtures/warning.yml'], 2, 'warning'),
    'hidden-warning': (['--config-data', WARN_DATA, '--no-warnings', '--format', 'parsable', '--', 'consumer-fixtures/warning.yml'], 0, 'empty'),
    'hidden-strict-warning': (['--config-data', WARN_DATA, '--strict', '--no-warnings', '--format', 'parsable', '--', 'consumer-fixtures/warning.yml'], 2, 'empty'),
    'visible-error': (['--config-data', 'extends: default', '--strict', '--no-warnings', '--format', 'parsable', '--', 'consumer-fixtures/error.yml'], 1, 'error'),
    'list-files': (['--config-data', LIST_DATA, '--list-files', '--', 'consumer-fixtures/listing'], 0, 'listing'),
    'default-booleans': (['--config-data', WARN_DATA, '--format', 'parsable', '--', 'consumer-fixtures/warning.yml'], 0, 'warning'),
    'false-booleans': (['--config-data', WARN_DATA, '--format', 'parsable', '--', 'consumer-fixtures/warning.yml'], 0, 'warning'),
    'literal-targets': (['--', '-consumer.yml', './-', 'consumer-fixtures/valid.yml'], 0, 'empty'),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def identity(local=False):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    scope = os.environ.get('VERIFICATION_SCOPE')
    require(scope in ('source', 'consumer'), 'Set VERIFICATION_SCOPE to source or consumer')
    release = os.environ.get('RELEASE_COMMIT', '') if scope == 'consumer' else commit
    require(re.fullmatch(r'[0-9a-f]{40}', release), 'Set RELEASE_COMMIT to the verified release/tag commit')
    subprocess.run(['git', 'merge-base', '--is-ancestor', release, 'HEAD'], check=True)
    dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD'], check=False).returncode != 0
    image = os.environ.get('VERIFICATION_IMAGE', '')
    require(image in ('cimg/python:3.13', 'cimg/python:3.14'), 'Expected a matrix image')
    if not local:
        require(os.environ.get('CIRCLECI') == 'true', 'CI evidence requires CircleCI')
        require(os.environ.get('CIRCLE_SHA1') == commit, 'Checkout does not match CI revision')
        require(not dirty, 'Tracked checkout is dirty')
        require(platform.python_version().startswith(image.split(':')[1] + '.'), 'Wrong actual Python')
        if scope == 'consumer':
            require(os.environ.get('CIRCLE_BRANCH') == 'verify/yamllint-v2.1.1', 'Use the dedicated consumer branch')
    packages = {}
    for name in ('yamllint', 'pathspec', 'PyYAML'):
        packages[name] = importlib.metadata.version(name)
    return dict(kind='local-supplementary' if local else 'CircleCI', release_commit=release,
                checkout_commit=commit, tracked_dirty=dirty, scope=scope,
                configured_orb='orbss/yamllint@2.1.1' if scope == 'consumer' else 'packed source inline',
                configured_image=image, configured_image_executed=not local,
                python=platform.python_version(), packages=packages,
                ci={k: os.environ.get(k, '') for k in ('CIRCLE_SHA1', 'CIRCLE_BUILD_URL', 'CIRCLE_BUILD_NUM', 'CIRCLE_WORKFLOW_ID',
                         'CIRCLE_PIPELINE_ID', 'CIRCLE_JOB', 'CIRCLE_BRANCH', 'CIRCLE_TAG')})


def validate(case, argv, status, stdout, stderr):
    expected, code, output = CASES[case]
    require(argv == expected, f'{case}: argument mismatch: {argv!r}')
    require(status == code, f'{case}: expected {code}, got {status}')
    require(stderr == '', f'{case}: unexpected stderr: {stderr!r}')
    if output == 'empty':
        require(stdout == '', f'{case}: unexpected stdout: {stdout!r}')
    elif output in ('warning', 'error'):
        file, severity, rule = (('warning.yml', 'warning', 'line-length') if output == 'warning'
                                else ('error.yml', 'error', 'trailing-spaces'))
        lines = stdout.splitlines()
        pattern = r'consumer-fixtures/' + re.escape(file) + r':\d+:\d+: \[' + severity + r'\] .+ \(' + rule + r'\)'
        require(len(lines) == 1 and re.fullmatch(pattern, lines[0]), f'{case}: wrong diagnostic meaning or extra output')
    else:
        wanted = {'consumer-fixtures/listing/keep.yml', 'consumer-fixtures/listing/broken.yml'}
        require(len(stdout.splitlines()) == 2 and set(stdout.splitlines()) == wanted,
                'list-files: selection mismatch')


PARAMETERS = ('PARAM_CONFIG_FILE', 'PARAM_CONFIG_DATA', 'PARAM_TARGETS',
              'PARAM_STRICT', 'PARAM_NO_WARNINGS', 'PARAM_LIST_FILES', 'PARAM_FORMAT')


def validate_raw(case, raw):
    # These are observed strings, never replacements for the Orb's environment.
    flags = {'PARAM_STRICT': '--strict', 'PARAM_NO_WARNINGS': '--no-warnings',
             'PARAM_LIST_FILES': '--list-files'}
    for name, flag in flags.items():
        allowed = ('true', '1') if flag in CASES[case][0] else ('false', '0', '', None)
        require(raw.get(name) in allowed, f'{case}: unexpected raw {name}: {raw.get(name)!r}')


def prepare(local):
    metadata = identity(local)
    expected = os.environ.get('EXPECTED_YAMLLINT', '')
    require(metadata['packages']['yamllint'] == expected, 'Installed yamllint differs from requested fixed version')
    require(not EVIDENCE.exists(), 'Evidence directory exists; use a fresh checkout/job')
    for path in ('consumer-fixtures', '-consumer.yml', '-'):
        require(not (ROOT / path).exists(), f'Fixture already exists: {path}')
    EVIDENCE.mkdir()
    real = shutil.which('yamllint')
    require(bool(real), 'Real yamllint executable missing')
    fixture = ROOT / 'consumer-fixtures'
    (fixture / 'listing').mkdir(parents=True)
    long = '---\nmessage: ' + 'word ' * 40 + 'end\n'
    for name, value in {'long.yml': long, 'warning.yml': long,
                        'error.yml': '---\nmessage: ok  \n', 'valid.yml': '---\nmessage: valid\n',
                        'config.yml': DATA, 'listing/keep.yml': '---\nmessage: valid\n',
                        'listing/broken.yml': '---\nmessage: [broken\n',
                        'listing/skip.yml': '---\nmessage: excluded\n'}.items():
        (fixture / name).write_text(value)
    for path in ('-consumer.yml', '-'):
        (ROOT / path).write_text('---\nmessage: valid\n')
    # An upstream control establishes that the supplied setting changes behavior.
    control = subprocess.run([real, '--config-data', 'extends: default', '--format', 'parsable', '--', 'consumer-fixtures/long.yml'],
                             text=True, capture_output=True)
    require(control.returncode == 1 and control.stderr == '' and '[error]' in control.stdout
            and '(line-length)' in control.stdout, 'Default/configuration control did not fail as expected')
    state = dict(identity=metadata, real=real, pending=None, results=[],
                 configuration_control=dict(status=control.returncode, stdout=control.stdout, stderr=control.stderr))
    save(STATE, state)
    save(EVIDENCE / 'runtime.json', metadata)
    bindir = EVIDENCE / 'bin'
    bindir.mkdir()
    wrapper = bindir / 'yamllint'
    wrapper.write_text('#!/bin/bash\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(Path(__file__).resolve())) + ' invoke "$@"\n')
    wrapper.chmod(0o755)
    if not local:
        bash_env = os.environ.get('BASH_ENV')
        require(bool(bash_env), 'CircleCI BASH_ENV missing')
        with open(bash_env, 'a') as handle:
            handle.write('export PATH=' + shlex.quote(str(bindir)) + ':"$PATH"\n')


def expect(case):
    state = json.loads(STATE.read_text())
    require(state['pending'] is None, 'Previous Orb body was not invoked')
    require(case not in [r['case'] for r in state['results']], 'Case already executed')
    require(len(state['results']) < len(CASES) and list(CASES)[len(state['results'])] == case,
            'Missing or reordered expectation')
    state['pending'] = case
    save(STATE, state)


def invoke(argv):
    state = json.loads(STATE.read_text())
    if argv == ['--version']:
        return subprocess.run([state['real'], *argv]).returncode
    case = state['pending']
    require(case in CASES, 'Unexpected or duplicate body invocation')
    # Real executable; no checked-out src/ import or shell success conversion.
    result = subprocess.run([state['real'], *argv], text=True, capture_output=True)
    raw = {name: os.environ.get(name) for name in PARAMETERS}
    observation = dict(case=case, raw_parameters=raw, argv=argv, status=result.returncode,
                       stdout=result.stdout, stderr=result.stderr)
    save(EVIDENCE / 'last-observation.json', observation)
    validate_raw(case, raw)
    validate(case, argv, result.returncode, result.stdout, result.stderr)
    state['results'].append(observation)
    state['pending'] = None
    save(STATE, state)
    sys.stdout.write(result.stdout)
    return 0  # Only after all argument/status/output conditions pass.


def finish():
    state = json.loads(STATE.read_text())
    require(state['pending'] is None, 'Final Orb body was not invoked')
    require([r['case'] for r in state['results']] == list(CASES), 'Missing, reordered or duplicated cases')
    save(EVIDENCE / 'results.json', dict(identity=state['identity'],
         configuration_control=state['configuration_control'], results=state['results'], result='PASS'))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'invoke':
        return invoke(sys.argv[2:])
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'expect', 'finish', 'minimal-record'])
    parser.add_argument('case', nargs='?', choices=list(CASES))
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.local)
    elif args.action == 'expect':
        require(args.case is not None, 'Expected case required')
        expect(args.case)
    elif args.action == 'finish':
        finish()
    else:
        metadata = identity(args.local)
        EVIDENCE.mkdir(exist_ok=False)
        save(EVIDENCE / 'minimal.json', dict(identity=metadata, result='PASS',
             scope='Preceding checkout/install/execute with omitted parameters succeeded'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
