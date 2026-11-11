#!/usr/bin/env python3
"""Observe real yamllint/execute steps that save output_file (#5510).

Runs in the fixed-matrix job output-file-<version>-py<python>. Each case is
one typed yamllint/execute step, armed by the "Observe <case>" step before it.

* A BASH_ENV hook records, at the start of every following step, that step
  shell's own stdout and stderr: terminal or not, file type and identity.
* A recorder installed as "yamllint" at the body position records argv, the
  raw PARAM_* values and its own stdout/stderr, then runs the real yamllint
  as a child. The child inherits stdin, stdout and stderr unchanged, and the
  recorder exits with the child's status. No pipe or PTY is added, and the
  recorder writes nothing to stdout.
* "finish" checks each case: the body exited 0, the typed values arrived
  unchanged, saving-disabled steps kept the step's stdout, saving steps gave
  yamllint a non-terminal stdout, yamllint's stderr stayed the step's stderr,
  the saved file has exactly the bytes of a separate reference run of the
  same real yamllint (stdout on a pipe, as when saving), and no other entry
  was created or left behind.

This covers the success path only. It does not capture the bytes delivered
to the CircleCI log, streaming, or the Orb's non-zero paths; those belong to
the child-process suites and to D08. Local runs are supplementary.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
ROOT = Path.cwd()                      # the job's working directory (the checkout)
EVIDENCE = ROOT / '.output-evidence'
STATE = EVIDENCE / 'state.json'
CONFIG_ABSOLUTE = '/tmp/yamllint-output-results'  # literal parent in test-deploy.yml
ABSOLUTE = Path(CONFIG_ABSOLUTE)
JOB = 'output-file-tests'
TEMPORARY_PREFIX = '.yamllint-orb-output-'
PARAMETERS = {
    'targets': 'PARAM_TARGETS', 'config_file': 'PARAM_CONFIG_FILE',
    'config_data': 'PARAM_CONFIG_DATA', 'strict': 'PARAM_STRICT',
    'no_warnings': 'PARAM_NO_WARNINGS', 'list_files': 'PARAM_LIST_FILES',
    'format': 'PARAM_FORMAT', 'output_file': 'PARAM_OUTPUT_FILE',
}
BOOLEANS = ('strict', 'no_warnings', 'list_files')
FLAGS = ('GITHUB_ACTIONS', 'GITHUB_WORKFLOW')  # select upstream's "auto" format

WARN = 'extends: default\nrules:\n  line-length:\n    max: 30\n    level: warning\n'
LIST = 'extends: relaxed\nyaml-files: ["*.yml", "*.yaml"]\nignore: ["output-fixtures/listing/skip.yml"]\n'
WARNING = 'output-fixtures/warning.yml'
LONG_TARGETS = ['-output-leading.yml', 'output-fixtures/日本語 ファイル.yml',
                'output-fixtures/many-warnings.yml']
MANY = 1500
LITERAL = 'output-results/-result ~ $HOME *?[a] "double" \'single\' 結果.txt'

# typed parameters as written in test-deploy.yml ({absolute} = CONFIG_ABSOLUTE),
# the argv the Orb must build from them, and the meaning of upstream's stdout.
CASES = {
    'saving-omitted': (
        dict(targets=WARNING, config_data=WARN, format='parsable'),
        ['--config-data', WARN, '--format', 'parsable', '--', WARNING], 'warning'),
    'saving-empty': (
        dict(targets=WARNING, config_data=WARN, format='parsable', output_file=''),
        ['--config-data', WARN, '--format', 'parsable', '--', WARNING], 'warning'),
    'absolute-parsable': (
        dict(targets=WARNING, config_data=WARN, format='parsable',
             output_file='{absolute}/absolute-parsable.txt'),
        ['--config-data', WARN, '--format', 'parsable', '--', WARNING], 'warning'),
    'relative-strict-clean': (
        dict(targets='output-fixtures/clean.yml', config_data=WARN, strict=True, format='parsable',
             output_file='output-results/strict-clean.txt'),
        ['--config-data', WARN, '--strict', '--format', 'parsable', '--', 'output-fixtures/clean.yml'],
        'empty'),
    'hidden-warning': (
        dict(targets=WARNING, config_data=WARN, no_warnings=True, format='parsable',
             output_file='{absolute}/hidden-warning.txt'),
        ['--config-data', WARN, '--no-warnings', '--format', 'parsable', '--', WARNING], 'empty'),
    'config-file': (
        dict(targets='output-fixtures/long.yml', config_file='output-fixtures/config.yml',
             output_file='output-results/config-file.txt'),
        ['--config-file', 'output-fixtures/config.yml', '--', 'output-fixtures/long.yml'], 'empty'),
    'list-files': (
        dict(targets='output-fixtures/listing', config_data=LIST, list_files=True,
             output_file='{absolute}/list-files.txt'),
        ['--config-data', LIST, '--list-files', '--', 'output-fixtures/listing'], 'listing'),
    'auto-format': (
        dict(targets=WARNING, config_data=WARN, output_file='output-results/auto-format.txt'),
        ['--config-data', WARN, '--', WARNING], 'standard'),
    'colored-format': (
        dict(targets=WARNING, config_data=WARN, format='colored',
             output_file='{absolute}/colored-format.txt'),
        ['--config-data', WARN, '--format', 'colored', '--', WARNING], 'colored'),
    'long-literal-path': (
        dict(targets='\n'.join(LONG_TARGETS), config_data=WARN, format='parsable', output_file=LITERAL),
        ['--config-data', WARN, '--format', 'parsable', '--', *LONG_TARGETS], 'long'),
}
SCOPE = ('Success path of real yamllint/execute steps with typed output_file in this job. '
         'Saved bytes are compared with a separate reference run of the same yamllint whose '
         'stdout is a pipe. The bytes delivered to the CircleCI log, streaming and the '
         "Orb's non-zero paths are not observed here.")
FILE_TYPES = {stat.S_IFIFO: 'pipe', stat.S_IFCHR: 'character device', stat.S_IFREG: 'regular file',
              stat.S_IFSOCK: 'socket', stat.S_IFDIR: 'directory'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(partial, path)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def resolve(value, absolute):
    return value.replace('{absolute}', str(absolute)) if isinstance(value, str) else value


def typed(case, absolute):
    return {name: resolve(value, absolute) for name, value in CASES[case][0].items()}


# --- process and connection observations ----------------------------------

def describe(fd):
    """The open file behind fd, without reading or writing it."""
    info = os.fstat(fd)
    try:
        link = os.readlink(f'/proc/self/fd/{fd}')
    except OSError:
        link = None
    kind = stat.S_IFMT(info.st_mode)
    return dict(isatty=os.isatty(fd), type=FILE_TYPES.get(kind, 'other'),
                identity=[kind, info.st_dev, info.st_ino, info.st_rdev], link=link)


def process(pid):
    data = Path(f'/proc/{pid}/stat').read_text()
    fields = data[data.rindex(')') + 2:].split()
    return int(fields[1]), fields[19]  # parent PID, start time


def ancestors():
    chain, pid = [], os.getppid()
    while pid > 1:
        parent, start = process(pid)
        chain.append([pid, start])
        pid = parent
    return chain


def flags(environment):
    return {name: name in environment for name in FLAGS}


def hook(evidence):
    """BASH_ENV: record this step shell's stdout/stderr while a case is armed.

    Every bash reads BASH_ENV, including bash started inside a step (for
    example a pyenv shim that resolves "yamllint"). Such nested shells have
    an observed step shell among their ancestors, or are that shell after an
    exec, and are not recorded.
    """
    path = evidence / 'state.json'
    state = load(path)
    case = state['pending']
    if case is None:
        return 0
    entry = state['cases'][case]
    chain = ancestors()  # starts with this shell
    if any([step['pid'], step['start']] in chain for step in entry['steps']):
        return 0
    require(entry['body'] is None, 'A step started after the body was recorded')
    shell, start = chain[0]
    entry['steps'].append(dict(pid=shell, start=start, stdout=describe(1), stderr=describe(2)))
    save(path, state)
    return 0


def invoke(evidence, argv):
    """Body position: record, run the real yamllint unchanged, keep its status."""
    path = evidence / 'state.json'
    state = load(path)
    if argv == ['--version']:
        # The Orb's separate "Show yamllint version" step, not the body.
        os.execv(state['real'], [state['real'], *argv])
    case = state['pending']
    require(case in CASES, 'Unexpected or duplicate body invocation')
    entry = state['cases'][case]
    require(entry['body'] is None, 'Unexpected or duplicate body invocation')
    chain = ancestors()
    owners = [index for index, step in enumerate(entry['steps']) if [step['pid'], step['start']] in chain]
    require(owners == [len(entry['steps']) - 1], 'The body did not run in the latest observed step')
    body = dict(argv=argv, raw_parameters={env: os.environ.get(env) for env in PARAMETERS.values()},
                cwd=os.getcwd(), stdout=describe(1), stderr=describe(2), step=owners[0],
                environment_flags=flags(os.environ), status=None)
    entry['body'] = body
    save(path, state)
    child = subprocess.Popen([state['real'], *argv])  # inherits stdin/stdout/stderr
    # Keep no copy of the body's stdout, so its end of output stays the body's own.
    null = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 1)
    os.close(null)
    status = child.wait()
    body['status'] = status
    state['pending'] = None
    save(path, state)
    return status if status >= 0 else 128 - status


# --- preparation and case sequence ----------------------------------------

def identity(local):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD'], cwd=REPO, check=False).returncode != 0
    image = os.environ.get('VERIFICATION_IMAGE', '')
    require(image in ('cimg/python:3.13', 'cimg/python:3.14'), 'Expected a matrix image')
    if not local:
        require(os.environ.get('VERIFICATION_SCOPE') == 'source', 'Expected VERIFICATION_SCOPE=source')
        require(os.environ.get('CIRCLECI') == 'true', 'CI evidence requires CircleCI')
        require(os.environ.get('CIRCLE_SHA1') == commit, 'Checkout does not match CI revision')
        require(not dirty, 'Tracked checkout is dirty')
        require(platform.python_version().startswith(image.split(':')[1] + '.'), 'Wrong actual Python')
        require(ROOT.resolve() == REPO, 'Run from the checkout')
    packages = {name: importlib.metadata.version(name) for name in ('yamllint', 'pathspec', 'PyYAML')}
    return dict(kind='local-supplementary' if local else 'CircleCI', checkout_commit=commit,
                tracked_dirty=dirty, scope='source', configured_orb='packed source inline',
                configured_image=image, configured_image_executed=not local,
                python=platform.python_version(), packages=packages,
                ci={k: os.environ.get(k, '') for k in ('CIRCLE_SHA1', 'CIRCLE_BUILD_URL', 'CIRCLE_BUILD_NUM',
                                                       'CIRCLE_WORKFLOW_ID', 'CIRCLE_PIPELINE_ID', 'CIRCLE_JOB',
                                                       'CIRCLE_BRANCH', 'CIRCLE_TAG')})


def configured_cases():
    """The typed yamllint/execute calls of the source job, keyed by their Observe step."""
    import yaml
    steps = yaml.safe_load((REPO / '.circleci/test-deploy.yml').read_text(encoding='utf-8'))['jobs'][JOB]['steps']
    calls, pending = {}, None
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get('run'), dict):
            name = step['run'].get('name', '')
            if name.startswith('Observe '):
                require(pending is None, 'Observe step without its yamllint/execute call')
                pending = name.removeprefix('Observe ')
        elif step == 'yamllint/execute' or (isinstance(step, dict) and 'yamllint/execute' in step):
            require(pending is not None and pending not in calls, 'yamllint/execute without one Observe step')
            calls[pending] = {} if isinstance(step, str) else (step['yamllint/execute'] or {})
            pending = None
    require(pending is None, 'Observe step without its yamllint/execute call')
    return calls


def defaults():
    import yaml
    command = yaml.safe_load((REPO / 'src/commands/execute.yml').read_text(encoding='utf-8'))
    require(set(command['parameters']) == set(PARAMETERS), 'execute parameters differ from the observer')
    return {name: value['default'] for name, value in command['parameters'].items()}


FIXTURES = {
    'output-fixtures/clean.yml': '---\nmessage: clean\n',
    'output-fixtures/warning.yml': '---\nmessage: "word word word word word word word word word word "\n',
    'output-fixtures/long.yml': '---\nmessage: ' + 'word ' * 40 + 'end\n',
    'output-fixtures/config.yml': 'extends: default\nrules:\n  line-length: disable\n',
    'output-fixtures/listing/keep.yml': '---\nvalue: 1\n',
    'output-fixtures/listing/sub/also.yaml': '---\nvalue: 2\n',
    'output-fixtures/listing/note.txt': 'not yaml\n',
    'output-fixtures/listing/skip.yml': '---\nvalue: 3\n',
    'output-fixtures/日本語 ファイル.yml': '---\nメッセージ: "' + 'とても長い日本語の値です' * 3 + '"\n',
    'output-fixtures/many-warnings.yml': '---\n' + ''.join(
        f'key{i:04d}: "word word word word word word"\n' for i in range(MANY)),
    '-output-leading.yml': '---\nmessage: "word word word word word word word word word word "\n',
}


def prepare(local, selection=None):
    metadata = identity(local)
    expected = os.environ.get('EXPECTED_YAMLLINT', '')
    require(metadata['packages']['yamllint'] == expected, 'Installed yamllint differs from requested fixed version')
    if not local:
        require(selection is None and str(ABSOLUTE) == CONFIG_ABSOLUTE, 'CI runs every configured case')
    selected = list(CASES) if selection is None else list(selection)
    require(selected and all(case in CASES for case in selected)
            and selected == [case for case in CASES if case in selected], 'Unknown or reordered case selection')
    configured = configured_cases()
    require(list(configured) == list(CASES), 'Configured cases differ from the observer')
    for case, values in configured.items():
        require(values == typed(case, CONFIG_ABSOLUTE), f'{case}: configured typed parameters differ')
    for path in (EVIDENCE, ABSOLUTE, ROOT / 'output-results', ROOT / 'output-fixtures', ROOT / '-output-leading.yml'):
        require(not os.path.lexists(path), f'Already exists; use a fresh checkout/job: {path}')
    real = shutil.which('yamllint')
    require(bool(real), 'Real yamllint executable missing')
    bash_env = os.environ.get('BASH_ENV')
    require(bool(bash_env), 'BASH_ENV missing')
    for name, content in FIXTURES.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    (ROOT / 'output-results').mkdir()
    ABSOLUTE.mkdir(parents=True)
    (EVIDENCE / 'bin').mkdir(parents=True)
    observer = str(Path(__file__).resolve())
    wrapper = EVIDENCE / 'bin' / 'yamllint'
    wrapper.write_text(f'#!{sys.executable} -I\nimport runpy, sys\n'
                       f'sys.argv[:1] = [{observer!r}, "invoke", {str(EVIDENCE)!r}]\n'
                       f'runpy.run_path({observer!r}, run_name="__main__")\n', encoding='utf-8')
    wrapper.chmod(0o755)
    state = dict(identity=metadata, real=real, defaults=defaults(), absolute=str(ABSOLUTE),
                 root=str(ROOT.resolve()), selected=selected, pending=None, cases={})
    save(STATE, state)
    save(EVIDENCE / 'runtime.json', metadata)
    (EVIDENCE / 'active').write_text('')
    active = shlex.quote(str(EVIDENCE / 'active'))
    with open(bash_env, 'a', encoding='utf-8') as handle:
        handle.write(f'\n# yamllint output_file observer (#5510): record each step stdout/stderr while active.\n'
                     f'if [ -e {active} ]; then {shlex.quote(sys.executable)} -I {shlex.quote(observer)} '
                     f'hook {shlex.quote(str(EVIDENCE))} || exit 1; '
                     f'export PATH={shlex.quote(str(EVIDENCE / "bin"))}:"$PATH"; fi\n')


def snapshot(state):
    """Every entry below the checkout (except .git and the evidence) and the absolute root."""
    found = []
    for label, top in (('root', Path(state['root'])), ('absolute', Path(state['absolute']))):
        for directory, names, files in os.walk(top):
            if directory == str(top):
                names[:] = [n for n in names if n not in ('.git', '.output-evidence')]
            for name in names + files:
                found.append(label + ':' + os.path.relpath(os.path.join(directory, name), top))
    return sorted(found)


def expect(case):
    state = load(STATE)
    require(state['pending'] is None, 'Previous Orb body was not invoked')
    started = list(state['cases'])
    require(len(started) < len(state['selected']) and state['selected'][len(started)] == case,
            'Missing or reordered expectation')
    state['cases'][case] = dict(before=snapshot(state), steps=[], body=None)
    state['pending'] = case
    save(STATE, state)


# --- checks -----------------------------------------------------------------

def destination(state, case):
    value = typed(case, state['absolute']).get('output_file', '')
    if not value:
        return None, None
    if os.path.isabs(value):
        relative = os.path.relpath(value, state['absolute'])
        require(not relative.startswith('..'), f'{case}: absolute destination outside the results root')
        return Path(value), 'absolute:' + relative
    return Path(state['root']) / value, 'root:' + os.path.normpath(value)


def validate_raw(case, values, default, raw):
    for name, env in PARAMETERS.items():
        value = values.get(name, default[name])
        actual = raw.get(env)
        if name in BOOLEANS:
            allowed = ('true', '1') if value else ('false', '0', '')
            require(actual in allowed, f'{case}: unexpected raw {env}: {actual!r}')
        else:
            require(actual == value, f'{case}: {env} was not passed unchanged: {actual!r}')


def check_connections(case, saving, step, body):
    same = lambda a, b: a['identity'] == b['identity']  # noqa: E731
    if saving:
        require(not body['stdout']['isatty'], f'{case}: yamllint stdout is a terminal while saving')
        require(not same(body['stdout'], step['stdout']),
                f'{case}: yamllint stdout is the step stdout although saving is enabled')
    else:
        require(same(body['stdout'], step['stdout']) and body['stdout']['isatty'] == step['stdout']['isatty'],
                f'{case}: saving is disabled but yamllint stdout is not the step stdout')
    require(same(body['stderr'], step['stderr']), f'{case}: yamllint stderr is not the step stderr')
    if saving:
        require(not same(body['stdout'], body['stderr']), f'{case}: yamllint stdout and stderr are one connection')


PARSABLE = r':\d+:\d+: \[warning\] line too long \(\d+ > 30 characters\) \(line-length\)'


def check_meaning(case, kind, data):
    """The reference output must have this case's meaning, so the comparison is not vacuous."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        text = None
    require(text is not None, f'{case}: reference output does not have the expected meaning (not UTF-8)')
    lines = text.splitlines()
    if kind == 'empty':
        ok = data == b''
    elif kind == 'warning':
        ok = len(lines) == 1 and text.endswith('\n') and re.fullmatch(re.escape(WARNING) + PARSABLE, lines[0])
    elif kind == 'listing':
        ok = (len(lines) == 2 and text.endswith('\n') and set(lines) ==
              {'output-fixtures/listing/keep.yml', 'output-fixtures/listing/sub/also.yaml'})
    elif kind == 'standard':
        ok = re.fullmatch(re.escape(WARNING) + r'\n  \d+:\d+ +warning +line too long '
                          r'\(\d+ > 30 characters\) +\(line-length\)\n\n', text)
    elif kind == 'colored':
        ok = (f'\x1b[4m{WARNING}\x1b[0m\n' in text and '\x1b[33mwarning\x1b[0m' in text
              and 'line too long' in text and '(line-length)' in text)
    else:
        counts = {target: 0 for target in LONG_TARGETS}
        for line in lines:
            target = next((t for t in LONG_TARGETS if re.fullmatch(re.escape(t) + PARSABLE, line)), None)
            if target is None:
                counts = None
                break
            counts[target] += 1
        ok = (len(data) > 65536 and text.endswith('\n')
              and counts == {LONG_TARGETS[0]: 1, LONG_TARGETS[1]: 1, LONG_TARGETS[2]: MANY})
    require(ok, f'{case}: reference output does not have the expected meaning ({kind})')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_case(state, case, before, after, environment):
    values, argv, kind = typed(case, state['absolute']), CASES[case][1], CASES[case][2]
    entry = state['cases'][case]
    body = entry['body']
    require(body is not None, f'{case}: the yamllint body was not invoked')
    require(body['status'] == 0, f'{case}: the yamllint body did not exit 0: {body["status"]!r}')
    require(body['argv'] == argv, f'{case}: argument mismatch: {body["argv"]!r}')
    validate_raw(case, values, state['defaults'], body['raw_parameters'])
    require(body['cwd'] == state['root'], f'{case}: the body ran in another directory')
    require(0 <= body['step'] < len(entry['steps']), f'{case}: no recorded step owns the body')
    step = entry['steps'][body['step']]
    path, key = destination(state, case)
    check_connections(case, path is not None, step, body)
    created, removed = set(after) - set(before), set(before) - set(after)
    require(not removed, f'{case}: entries disappeared: {sorted(removed)!r}')
    require(body['environment_flags'] == flags(environment), f'{case}: reference environment differs')
    reference = subprocess.run([state['real'], *argv], cwd=state['root'], env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=120, check=False)
    require(reference.returncode == 0 and reference.stderr == b'',
            f'{case}: reference run did not succeed cleanly: {reference.returncode}')
    check_meaning(case, kind, reference.stdout)
    evidence = Path(state['root']) / '.output-evidence'
    (evidence / 'reference').mkdir(exist_ok=True)
    (evidence / 'reference' / (case + '.out')).write_bytes(reference.stdout)
    record = dict(case=case, typed_parameters=values, raw_parameters=body['raw_parameters'], argv=argv,
                  body_status=body['status'], orb_step='succeeded: the following on_success step ran',
                  step_stdout=step['stdout'], step_stderr=step['stderr'],
                  body_stdout=body['stdout'], body_stderr=body['stderr'],
                  observed_steps=[dict(stdout=s['stdout'], stderr=s['stderr']) for s in entry['steps']],
                  reference=dict(status=reference.returncode, stdout_bytes=len(reference.stdout),
                                 stdout_sha256=digest(reference.stdout), stderr_bytes=len(reference.stderr)),
                  saving=path is not None)
    if path is None:
        require(not created, f'{case}: saving is disabled but entries were created: {sorted(created)!r}')
        return record
    require(created == {key}, f'{case}: expected only {key!r}, created {sorted(created)!r}')
    require(stat.S_ISREG(os.lstat(path).st_mode), f'{case}: the result is not a regular file')
    data = path.read_bytes()
    require(data == reference.stdout, f'{case}: saved bytes differ from the reference stdout')
    (evidence / 'saved').mkdir(exist_ok=True)
    (evidence / 'saved' / (case + '.out')).write_bytes(data)
    record['saved'] = dict(output_file=values['output_file'], bytes=len(data), sha256=digest(data),
                           equals_reference_stdout=True)
    return record


def reference_environment():
    return {k: v for k, v in os.environ.items() if not k.startswith('PARAM_')}


def finish():
    state = load(STATE)
    require(state['pending'] is None, 'Final Orb body was not invoked')
    require(list(state['cases']) == state['selected'], 'Missing, reordered or duplicated cases')
    after = snapshot(state)
    temporaries = [e for e in after if os.path.basename(e.split(':', 1)[1]).startswith(TEMPORARY_PREFIX)]
    require(not temporaries, f'Temporary output data was left behind: {temporaries!r}')
    boundaries = [state['cases'][case]['before'] for case in state['selected']] + [after]
    environment = reference_environment()
    results = [check_case(state, case, boundaries[i], boundaries[i + 1], environment)
               for i, case in enumerate(state['selected'])]
    save(Path(state['root']) / '.output-evidence' / 'results.json',
         dict(identity=state['identity'], real=state['real'], scope=SCOPE, cases=results, result='PASS'))
    (Path(state['root']) / '.output-evidence' / 'active').unlink()


def main(argv):
    if len(argv) > 1 and argv[1] == 'invoke':
        return invoke(Path(argv[2]), argv[3:])
    if len(argv) > 1 and argv[1] == 'hook':
        return hook(Path(argv[2]))
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'expect', 'finish'])
    parser.add_argument('case', nargs='?', choices=list(CASES))
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args(argv[1:])
    if args.action == 'prepare':
        prepare(args.local)
    elif args.action == 'expect':
        require(args.case is not None, 'Expected case required')
        expect(args.case)
    else:
        finish()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
        print('yamllint output_file observer: ' + str(error), file=sys.stderr)
        sys.exit(1)
