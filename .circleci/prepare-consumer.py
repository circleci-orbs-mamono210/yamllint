#!/usr/bin/env python3
"""Generate and check the published-consumer configuration for v2.2.0 (#5512).

consumer/config.template.yml is the only source of the consumer
.circleci/config.yml. A generated copy differs from the template only by the
release commit that replaces the placeholder.

  generate         write the configuration for one release commit.
  verify-checkout  first observer step of every consumer job: dedicated branch,
                   one commit after the release commit, only .circleci/config.yml
                   changed, and that file equals the generated configuration.
  inline           PRE-PUBLICATION STRUCTURE CHECK ONLY: replace the registry
                   Orb reference by a packed Orb so the official compiler can
                   expand the configuration before the release exists. The
                   result is never run and is not evidence about the published Orb.

check-ci-contract.py imports check_config and check_expanded for the setup
contract check; test-consumer-template.py and test-ci-contract.py hold their
fault controls.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / '.circleci/consumer/config.template.yml'
CONFIG = '.circleci/config.yml'
PLACEHOLDER = '__RELEASE_COMMIT__'
PLACEHOLDERS = 4  # one RELEASE_COMMIT per job
ORB = 'orbss/yamllint@2.2.0'
BRANCH = 'verify/yamllint-v2.2.0'
IMAGE = 'cimg/python:3.14'
VERSIONS = ('1.37.1', '1.38.0')
JOBS = ('minimal', 'boolean-acceptance', 'output-file-acceptance', 'd08-failed-lint-artifact')
D08 = 'd08-failed-lint-artifact'
CHECKOUT_STEP = 'verify-consumer-checkout'
# Never part of a consumer configuration, as a key or inside any value.
FORBIDDEN = ('setup', 'continuation', 'orb-tools', 'context', 'publish', 'inject', 'src/', 'CIRCLE_TOKEN')
# (consumer job, source job in test-deploy.yml, first and last observer step names)
OBSERVED = (
    ('boolean-acceptance', 'compatibility-tests',
     'Prepare fixtures and real-upstream observer', 'Verify all body calls and results'),
    ('output-file-acceptance', 'output-file-tests',
     'Prepare output_file fixtures and step observer', 'Verify output_file observations'),
)
EXPANDED_JOBS = {'minimal': ('minimal', None, 1), D08: (D08, '1.38.0', 1),
                 **{f'{job}-{version}': (job, version, 10)
                    for job in ('boolean-acceptance', 'output-file-acceptance') for version in VERSIONS}}
WORKFLOWS = {
    'consumer-acceptance': ['minimal'] + [
        {job: {'name': f'{job}-{version}', 'yamllint-version': version}}
        for job in ('boolean-acceptance', 'output-file-acceptance') for version in VERSIONS],
    'd08-failed-step-artifact': [D08],
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_module(name):
    path = REPO / '.circleci' / name
    spec = importlib.util.spec_from_file_location(name.replace('-', '_').removesuffix('.py'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate(release, template=None):
    """The consumer configuration text: the template with the release commit filled in."""
    require(re.fullmatch(r'[0-9a-f]{40}', release or ''), 'The release commit must be a full lowercase SHA')
    text = TEMPLATE.read_text(encoding='utf-8') if template is None else template
    require(text.count(PLACEHOLDER) == PLACEHOLDERS, 'Unexpected number of release commit placeholders')
    return text.replace(PLACEHOLDER, release)


def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=REPO, text=True).strip()


def verify_checkout(environment=None):
    """The consumer commit is the release commit plus the generated configuration, nothing else."""
    environment = os.environ if environment is None else environment
    release = environment.get('RELEASE_COMMIT', '')
    require(environment.get('VERIFICATION_SCOPE') == 'consumer', 'Expected VERIFICATION_SCOPE=consumer')
    require(environment.get('CIRCLECI') == 'true', 'Consumer verification requires CircleCI')
    require(environment.get('CIRCLE_BRANCH') == BRANCH, 'Use the dedicated consumer branch ' + BRANCH)
    head = git('rev-parse', 'HEAD')
    require(environment.get('CIRCLE_SHA1') == head, 'Checkout does not match the CI revision')
    require(subprocess.run(['git', 'diff', '--quiet', 'HEAD'], cwd=REPO, check=False).returncode == 0,
            'Tracked checkout is dirty')
    require(git('rev-list', '--parents', '-n', '1', 'HEAD').split() == [head, release],
            'The consumer commit must be exactly one commit after the release commit')
    require(git('diff', '--name-only', release, 'HEAD').splitlines() == [CONFIG],
            'Only .circleci/config.yml may differ from the release commit')
    template = subprocess.check_output(['git', 'show', f'{release}:.circleci/consumer/config.template.yml'],
                                       cwd=REPO, text=True)
    require((REPO / CONFIG).read_text(encoding='utf-8') == generate(release, template),
            '.circleci/config.yml is not the release template with only the release commit replaced')
    return dict(consumer_commit=head, release_commit=release, branch=BRANCH, configured_orb=ORB)


# --- structure checks --------------------------------------------------------

def strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


def step_name(step):
    if isinstance(step, str):
        return step
    name = next(iter(step))
    return step['run'].get('name') if name == 'run' and isinstance(step['run'], dict) else name


def observer_steps(job, first, last):
    names = [step_name(step) for step in job['steps']]
    require(names.count(first) == 1 and names.count(last) == 1, 'Observer step missing or duplicated')
    return job['steps'][names.index(first):names.index(last) + 1]


def executes(job):
    return [({} if step == 'yamllint/execute' else step['yamllint/execute'] or {}) for step in job['steps']
            if step == 'yamllint/execute' or (isinstance(step, dict) and 'yamllint/execute' in step)]


def check_config(config, source, release):
    """Static structure of a generated consumer configuration (before expansion)."""
    d08 = load_module('verify-consumer-d08.py')
    require(set(config) == {'version', 'orbs', 'commands', 'jobs', 'workflows'} and config['version'] == 2.1,
            'Unexpected top-level consumer configuration')
    require(config['orbs'] == {'yamllint': ORB}, 'The consumer must reference only the published ' + ORB)
    for text in strings(config):
        for word in FORBIDDEN:
            require(word not in text, f'Forbidden mechanism in the consumer configuration: {word}')
    for name in ('verify-boolean-parameters.py', 'verify-output-file.py'):
        observer = load_module(name)
        require(observer.CONSUMER_ORB == ORB and observer.CONSUMER_BRANCH == BRANCH,
                f'{name} still targets another consumer branch or Orb version')
    require(load_module('verify-output-file.py').JOBS['consumer'] == (CONFIG, 'output-file-acceptance'),
            'Output observer reads another consumer job')
    require(config['commands'] == {CHECKOUT_STEP: {'steps': [{'run': {
        'name': 'Verify consumer checkout', 'command': 'python .circleci/prepare-consumer.py verify-checkout'}}]}},
        'Consumer checkout verification changed')
    require(tuple(config['jobs']) == JOBS, 'Consumer job set changed')
    for name, job in config['jobs'].items():
        environment = dict(job['environment'])
        expected = {'VERIFICATION_SCOPE': 'consumer', 'VERIFICATION_IMAGE': IMAGE, 'RELEASE_COMMIT': release}
        if name == D08:
            expected['EXPECTED_YAMLLINT'] = d08.YAMLLINT
        elif name != 'minimal':
            expected['EXPECTED_YAMLLINT'] = '<< parameters.yamllint-version >>'
            require(job['parameters'] == {'yamllint-version': {'type': 'enum', 'enum': list(VERSIONS)}},
                    'Fixed yamllint versions changed')
        require(environment == expected, f'{name}: verification identity changed')
        require(job['executor'] == ('yamllint/default' if name == 'minimal'
                                    else {'name': 'yamllint/default', 'image': IMAGE}), f'{name}: executor changed')
        steps = job['steps']
        require(steps[0] == 'checkout' and [step_name(s) for s in steps].count(CHECKOUT_STEP) == 1,
                f'{name}: checkout or its verification is missing')
        for step in steps:
            if isinstance(step, dict) and isinstance(step.get('run'), dict):
                run = step['run']
                require('environment' not in run and not run.get('background', False),
                        f'{name}: an observer step must not set parameters or run in the background')
                require(run['command'].startswith('python .circleci/'), f'{name}: unexpected command')
                require(run.get('when', 'on_success') == ('always' if run['name'] == d08.CHECK_STEP else 'on_success'),
                        f'{name}: step condition changed')
    minimal = config['jobs']['minimal']['steps']
    require(minimal[:4] == ['checkout', 'yamllint/install', 'yamllint/execute', CHECKOUT_STEP]
            and step_name(minimal[4]) == 'Record minimal workflow result', 'Minimal workflow changed')
    for name, source_name, first, last in OBSERVED:
        job = config['jobs'][name]
        require(job['steps'][1] == {'yamllint/install': {'version': '<< parameters.yamllint-version >>'}}
                and job['steps'][2] == CHECKOUT_STEP, f'{name}: fixed installation changed')
        require(observer_steps(job, first, last) == observer_steps(source['jobs'][source_name], first, last),
                f'{name}: observed cases differ from the verified source job')
        require(step_name(job['steps'][3]) == first and len(executes(job)) == 10,
                f'{name}: an unobserved Orb call was added')
    job = config['jobs'][D08]
    require([step_name(step) for step in job['steps']] == [
        'checkout', 'yamllint/install', CHECKOUT_STEP, 'Prepare D08 fixture and result directory',
        'yamllint/execute', d08.CHECK_STEP, 'store_artifacts', 'store_artifacts'], 'D08 step sequence changed')
    require(job['steps'][1] == {'yamllint/install': {'version': d08.YAMLLINT}}, 'D08 yamllint version changed')
    require(executes(job) == [d08.EXECUTE], 'D08 must call yamllint/execute exactly once with its fixed parameters')
    require(job['steps'][6] == {'store_artifacts': {
        'path': d08.EXECUTE['output_file'], 'destination': d08.ARTIFACT}}, 'D08 result artifact changed')
    require(job['steps'][7] == {'store_artifacts': {
        'path': str(d08.EVIDENCE_DIR), 'destination': 'yamllint-d08-evidence'}}, 'D08 evidence artifact changed')
    require({name: workflow['jobs'] for name, workflow in config['workflows'].items()} == WORKFLOWS
            and all(set(workflow) == {'jobs'} for workflow in config['workflows'].values()),
            'Consumer workflows changed; D08 must stay outside the success-required workflow')


def runs(job, name=None):
    found = [step['run'] for step in job['steps'] if isinstance(step, dict) and isinstance(step.get('run'), dict)]
    return found if name is None else [run for run in found if run.get('name') == name]


def check_expanded(expanded, config, packed):
    """Compiled consumer configuration, with the packed Orb standing in for the registry Orb."""
    d08 = load_module('verify-consumer-d08.py')
    command = packed['commands']['execute']
    body = runs(command, d08.BODY_STEP)
    require(len(body) == 1, 'Expected one packed execute body step')
    script = body[0]['command'].replace('\\<<', '<<')
    mapping = {env: re.fullmatch(r'<<\s*parameters\.(\w+)\s*>>', value).group(1)
               for env, value in body[0]['environment'].items()}
    defaults = {name: definition['default'] for name, definition in command['parameters'].items()}
    require(set(expanded['jobs']) == set(EXPANDED_JOBS), 'Expanded consumer job set changed')
    for name, (source_name, version, count) in EXPANDED_JOBS.items():
        job = expanded['jobs'][name]
        require(job['docker'][0]['image'] == IMAGE, f'{name}: consumer image changed')
        bodies = runs(job, d08.BODY_STEP)
        require(len(bodies) == count, f'{name}: unexpected number of "{d08.BODY_STEP}" steps')
        wanted = executes(config['jobs'][source_name])
        for values, run in zip(wanted, bodies):
            require(run['command'].strip() == script.strip(), f'{name}: body step is not the Orb script')
            require(run['environment'] == {env: values.get(parameter, defaults[parameter])
                                           for env, parameter in mapping.items()},
                    f'{name}: typed parameters were not delivered unchanged')
            require(run.get('when', 'on_success') == 'on_success' and not run.get('background', False),
                    f'{name}: body step condition changed')
        installs = runs(job, 'Install yamllint')
        require(len(installs) == 1 and installs[0]['environment'] == {'PARAM_VERSION': version or ''},
                f'{name}: installed yamllint version changed')
    names = [run.get('name') for run in runs(expanded['jobs'][D08])]
    require(names.count(d08.BODY_STEP) == 1 and names.count(d08.VERSION_STEP) == 1
            and names.index(d08.BODY_STEP) == names.index(d08.VERSION_STEP) + 1,
            'D08: "Execute yamllint" must be unique and directly follow "Show yamllint version"')
    require(names == d08.JOB_STEPS, 'D08: expanded step names differ from the judged step list')
    shown = list(d08.ENVIRONMENT_STEPS)
    for step in expanded['jobs'][D08]['steps']:
        kind = step if isinstance(step, str) else next(iter(step))
        if kind == 'run':
            shown.append(step['run'].get('name') if isinstance(step['run'], dict) else None)
        else:
            require(kind in d08.SPECIAL_STEPS, f'D08: step "{kind}" has no known name in the CircleCI UI')
            shown.append(d08.SPECIAL_STEPS[kind])
    require(shown == d08.UI_STEPS, 'D08: the steps the UI will show differ from the step list the record must hold')
    check = runs(expanded['jobs'][D08], d08.CHECK_STEP)[0]
    require(check.get('when') == 'always', 'D08: the result file check must always run')
    for text in strings(expanded):
        require('context' not in text and 'continuation' not in text, 'Forbidden mechanism after expansion')


def inline(config_text, packed_text):
    """Pre-publication only: the same configuration with the packed Orb inline."""
    reference = f'  yamllint: {ORB}\n'
    require(config_text.count(reference) == 1, 'Expected one registry Orb reference')
    indented = ''.join('    ' + line if line.strip() else line for line in packed_text.splitlines(True))
    return ('# PRE-PUBLICATION STRUCTURE CHECK ONLY. Never run this file.\n'
            '# The registry Orb reference is replaced by the packed source Orb.\n'
            + config_text.replace(reference, '  yamllint:\n' + indented))


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['generate', 'verify-checkout', 'inline'])
    parser.add_argument('--release-commit')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--packed', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv[1:])
    if args.action == 'verify-checkout':
        print(verify_checkout())
        return 0
    require(args.output is not None, '--output is required')
    if args.action == 'generate':
        text = generate(args.release_commit)
    else:
        require(args.config and args.packed, 'inline needs --config and --packed')
        text = inline(args.config.read_text(encoding='utf-8'), args.packed.read_text(encoding='utf-8'))
    args.output.write_text(text, encoding='utf-8')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print('yamllint consumer: ' + str(error), file=sys.stderr)
        sys.exit(1)
