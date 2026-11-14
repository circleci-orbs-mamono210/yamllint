#!/usr/bin/env python3
"""#5513 full-content Orb comparison checks: python3 .circleci/test-compare-orbs.py -v.

Fault controls for compare-orbs.py, which records the comparison of the
release candidate's packed Orb, the tag pipeline's packed Orb and the
published Orb:

* reformatted copies of the same Orb match;
* any change to a script, example, parameter or other field is a mismatch,
  reported at its path and for the input that differs;
* input that is not one unambiguous YAML document is not compared;
* the record passes only with every field, from a clean checkout of the
  release candidate with the pinned tool, with the tag on that commit and the
  CHANGELOG date equal to the publication day in JST.

The Orb used here is assembled from src/ in the way `circleci orb pack` does.
These are controls of the tool, not release evidence. Local runs are
supplementary.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / '.circleci/compare-orbs.py'
RC = 'a1' * 20
PIPELINE = 'https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/1'


def load():
    spec = importlib.util.spec_from_file_location('compare_orbs', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = load()


def packed_source():
    """The Orb as a mapping assembled from src/, with script includes resolved."""
    src = ROOT / 'src'
    orb = yaml.safe_load((src / '@orb.yml').read_text(encoding='utf-8'))
    for kind in ('commands', 'executors', 'jobs', 'examples'):
        if (src / kind).is_dir():
            orb[kind] = {path.stem: yaml.safe_load(path.read_text(encoding='utf-8'))
                         for path in sorted((src / kind).glob('*.yml'))}

    def include(value):
        if isinstance(value, dict):
            return {key: include(item) for key, item in value.items()}
        if isinstance(value, list):
            return [include(item) for item in value]
        match = re.fullmatch(r'<<include\((.+)\)>>', value.strip()) if isinstance(value, str) else None
        return (src / match.group(1)).read_text(encoding='utf-8') if match else value
    return include(orb)


class BlockDumper(yaml.SafeDumper):
    """Multi-line strings as literal blocks where YAML allows it, as packed Orbs show them."""


BlockDumper.add_representer(str, lambda dumper, value: dumper.represent_scalar(
    'tag:yaml.org,2002:str', value, style='|' if '\n' in value else None))


def render(orb, style='pack-like'):
    if style == 'pack-like':
        return yaml.dump(orb, Dumper=BlockDumper, sort_keys=True, indent=4, allow_unicode=True, width=10 ** 6)
    if style == 'insertion-order':
        return '# reformatted copy\n' + yaml.safe_dump(orb, sort_keys=False, allow_unicode=True, width=60)
    if style == 'json':
        return json.dumps(orb, ensure_ascii=False, indent=1)
    return yaml.safe_dump(orb, default_flow_style=True, width=80)


def execute_step(orb):
    return next(step['run'] for step in orb['commands']['execute']['steps']
                if step['run'].get('name') == 'Execute yamllint')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(repo, *arguments):
    return subprocess.check_output(
        ['git', '-c', 'user.name=test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false',
         *arguments], cwd=repo, text=True, stderr=subprocess.STDOUT).strip()


class Content(unittest.TestCase):
    """The comparison itself: what matches, what differs and what is not compared."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-compare-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.orb = packed_source()

    def files(self, **texts):
        paths = {}
        for role, text in texts.items():
            path = self.base / f'{role}-{len(list(self.base.iterdir()))}.yml'
            path.write_bytes(text if isinstance(text, bytes) else text.encode('utf-8'))
            paths[role.replace('_', '-')] = path
        return paths

    def test_reformatted_copies_of_the_packed_source_match(self):
        reference = render(self.orb)
        self.assertIn('command: |', reference)  # scripts as literal blocks, as in a packed Orb
        for style in ('pack-like', 'insertion-order', 'json', 'flow'):
            inputs, content, found, problems = compare.compare(
                self.files(rc=reference, tag_ci=reference, published=render(self.orb, style)))
            with self.subTest(style=style):
                self.assertEqual((content, problems), ('MATCH', []))
                self.assertEqual(found, {'tag-ci vs rc': [], 'published vs rc': []})
                self.assertEqual(len({entry['canonical_sha256'] for entry in inputs}), 1)
                self.assertEqual(len({entry['raw_sha256'] for entry in inputs}) == 1, style == 'pack-like')

    def test_any_change_to_scripts_examples_or_fields_is_a_mismatch(self):
        body = '$.commands.execute.steps'
        mutations = [
            ('one character of the execute script', body,
             lambda o: execute_step(o).update(command=execute_step(o)['command'].replace('exit 2', 'exit 3', 1))),
            ('trailing newline of the script removed', body,
             lambda o: execute_step(o).update(command=execute_step(o)['command'].rstrip('\n'))),
            ('trailing space added to a script line', body,
             lambda o: execute_step(o).update(command=execute_step(o)['command'].replace('\n', ' \n', 1))),
            ('CRLF line endings in the script', body,
             lambda o: execute_step(o).update(command=execute_step(o)['command'].replace('\n', '\r\n'))),
            ('example removed', '$.examples.output_file', lambda o: o['examples'].pop('output_file')),
            ('example usage changed', '$.examples.example.usage.orbs.yamllint',
             lambda o: o['examples']['example']['usage']['orbs'].update(yamllint='orbss/yamllint@2.1.1')),
            ('parameter default changed', '$.commands.execute.parameters.output_file.default',
             lambda o: o['commands']['execute']['parameters']['output_file'].update(default=' ')),
            ('boolean default written as text', '$.commands.execute.parameters.strict.default',
             lambda o: o['commands']['execute']['parameters']['strict'].update(default='false')),
            ('description whitespace', '$.description', lambda o: o.update(description=o['description'] + ' ')),
            ('top-level field removed', '$.display', lambda o: o.pop('display')),
            ('parameter added', '$.commands.execute.parameters.extra',
             lambda o: o['commands']['execute']['parameters'].update(extra={'type': 'string', 'default': ''})),
            ('steps reordered', body, lambda o: o['commands']['execute']['steps'].reverse()),
            ('executor default image changed', '$.executors.default.parameters.image.default',
             lambda o: o['executors']['default']['parameters']['image'].update(default='cimg/python:3.13')),
        ]
        reference = render(self.orb)
        for label, path, change in mutations:
            changed = copy.deepcopy(self.orb)
            change(changed)
            _, content, found, problems = compare.compare(
                self.files(rc=reference, tag_ci=reference, published=render(changed)))
            with self.subTest(label):
                self.assertEqual((content, problems), ('MISMATCH', []))
                self.assertEqual(found['tag-ci vs rc'], [])
                self.assertTrue(found['published vs rc'][0]['path'].startswith(path), found['published vs rc'])

    def test_differences_are_reported_for_the_input_that_differs(self):
        changed = copy.deepcopy(self.orb)
        execute_step(changed)['command'] += '# appended\n'
        same, other = render(self.orb), render(changed)
        for roles, differing in ((dict(rc=same, tag_ci=other, published=same), ['tag-ci vs rc']),
                                 (dict(rc=same, tag_ci=same, published=other), ['published vs rc']),
                                 (dict(rc=other, tag_ci=same, published=same), ['tag-ci vs rc', 'published vs rc'])):
            _, content, found, _ = compare.compare(self.files(**roles))
            with self.subTest(differing=differing):
                self.assertEqual(content, 'MISMATCH')
                self.assertEqual(sorted(pair for pair, items in found.items() if items), sorted(differing))
                self.assertEqual(found[differing[0]][0]['difference'], 'value differs')

    def test_scalar_tags_and_spellings_are_kept(self):
        different = [('a: 1', 'a: "1"'), ('a: 1', 'a: 1.0'), ('a: 1', 'a: 01'), ('a: true', 'a: "true"'),
                     ('a: true', 'a: yes'), ('a: true', 'a: True'), ('a: null', 'a: ""'), ('a: null', 'a: ~'),
                     ('a: 2026-11-14', 'a: "2026-11-14"'), ('a: x', 'a: "x "'), ('a: [1, 2]', 'a: [2, 1]'),
                     ('a: {}', 'a: []'), ('a: !!set {x: null}', 'a: {x: null}'), ('a: 2.1', 'a: 2.10')]
        same = [("a: 'x'", 'a: "x"'), ('a: x', "a: 'x'"), ('a: |\n  l1\n  l2\n', 'a: "l1\\nl2\\n"'),
                ('a: >\n  l1\n  l2\n', 'a: "l1 l2\\n"'), ('{b: 1, a: 2}', 'a: 2\nb: 1\n'),
                ('a: 1  # comment', 'a: 1'), ('a: !!str 1', 'a: "1"'), ('a:\n    - 1\n', 'a: [1]')]
        for left, right, expected in [(*pair, False) for pair in different] + [(*pair, True) for pair in same]:
            with self.subTest(left=left, right=right):
                self.assertEqual(compare.canonical(left.encode()) == compare.canonical(right.encode()), expected)

    def test_aliases_and_merge_keys_are_resolved(self):
        pairs = [
            ('x: &a [1, 2]\ny: *a\n', 'x: [1, 2]\ny: [1, 2]\n'),
            ('b: &b {k: 1, m: 2}\nd:\n  <<: *b\n  k: 3\n', 'b: {k: 1, m: 2}\nd: {m: 2, k: 3}\n'),
            ('b: &b {k: 1}\nc: &c {j: 2}\nd:\n  <<: [*b, *c]\n', 'b: {k: 1}\nc: {j: 2}\nd: {k: 1, j: 2}\n'),
            ('b: &b {k: 1}\nd: &d\n  <<: *b\n  k: 2\ne: *d\nf: *d\n', 'b: {k: 1}\nd: {k: 2}\ne: {k: 2}\nf: {k: 2}\n'),
        ]
        for left, right in pairs:
            with self.subTest(left=left):
                self.assertEqual(compare.canonical(left.encode()), compare.canonical(right.encode()))

    def test_input_that_is_not_one_unambiguous_document_is_not_compared(self):
        rejected = [
            (b'a: 1\na: 2\n', 'duplicate mapping key'),
            (b'a:\n  b: 1\n  b: 1\n', 'duplicate mapping key'),
            (b'b: &b {k: 1}\nd:\n  <<: *b\n  k: 2\n  k: 3\n', 'duplicate mapping key'),
            (b'a: "unclosed\n', 'invalid YAML'),
            (b'', 'no YAML document'),
            (b'# only a comment\n', 'no YAML document'),
            (b'a: 1\n---\nb: 2\n', 'single document'),
            (b'- a\n- b\n', 'not a mapping'),
            (b'a: !!python/object/apply:os.system ["true"]\n', 'unsupported YAML tag'),
            (b'a: !custom x\n', 'unsupported YAML tag'),
            (b'\xff\xfe\x00', 'not UTF-8'),
            (b'a: &x [*x]\n', 'recursive'),
            (b'a: *missing\n', 'invalid YAML'),
            (b'a:\n  <<: 1\n', 'invalid merge key'),
        ]
        for data, message in rejected:
            with self.subTest(data=data):
                with self.assertRaisesRegex(compare.InputError, message):
                    compare.canonical(data)
        valid = render(self.orb)
        for role in ('rc', 'tag_ci', 'published'):
            roles = dict(rc=valid, tag_ci=valid, published=valid)
            roles[role] = b'a: 1\na: 1\n'
            inputs, content, found, problems = compare.compare(self.files(**roles))
            with self.subTest(role=role):
                self.assertEqual((content, found), ('NOT COMPARED', {}))
                self.assertEqual(problems, [role.replace('_', '-') + ": duplicate mapping key 'a' at line 2"])
        paths = self.files(rc=valid, tag_ci=valid)
        paths['published'] = self.base / 'missing.yml'
        _, content, _, problems = compare.compare(paths)
        self.assertEqual(content, 'NOT COMPARED')
        self.assertTrue(problems[0].startswith('published: cannot read'), problems)


class Record(unittest.TestCase):
    """The command-line record: complete, consistent, from the pinned tool at the RC."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='yamllint-record-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.repo = self.base / 'rc'
        (self.repo / '.circleci').mkdir(parents=True)
        self.tool = self.repo / '.circleci/compare-orbs.py'
        shutil.copy2(TOOL, self.tool)
        self.manifest = self.repo / '.circleci/compatibility-contract.json'
        self.manifest.write_text(json.dumps({'feature_suite_sha256': {'compare-orbs.py': sha256(self.tool)}}))
        (self.repo / 'CHANGELOG.md').write_text('# Changelog\n\n## [Unreleased]\n\n## [2.2.0] - 2026-11-14\n')
        git(self.repo, 'init', '-q')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', 'release candidate')
        self.rc = git(self.repo, 'rev-parse', 'HEAD')
        self.orb = packed_source()
        self.inputs = {}
        for role, style in (('rc', 'pack-like'), ('tag-ci', 'pack-like'), ('published', 'json')):
            self.inputs[role] = self.base / f'{role}.yml'
            self.inputs[role].write_text(render(self.orb, style), encoding='utf-8')
        self.count = 0

    def run_tool(self, tool=None, sources=None, **changes):
        self.count += 1
        output = self.base / f'report-{self.count}.json'
        values = dict(rc=self.inputs['rc'], tag_ci=self.inputs['tag-ci'], published=self.inputs['published'],
                      rc_commit=self.rc, tag='v2.2.0', tag_commit=self.rc, tag_pipeline=PIPELINE,
                      published_at='2026-11-14T20:43:54+09:00', checked_by='reviewer', output=output)
        values.update(changes)
        sources = {'rc': 'phase5-config/orb.yml of the RC pipeline', 'tag-ci': 'phase5-config/orb.yml of the tag '
                   'pipeline', 'published': 'circleci orb source orbss/yamllint@2.2.0'} if sources is None else sources
        argv = [sys.executable, str(tool or self.tool)]
        for name, value in values.items():
            if value is not None:
                argv += ['--' + name.replace('_', '-'), str(value)]
        for role, text in sources.items():
            argv += ['--source', f'{role}={text}']
        result = subprocess.run(argv, cwd=self.base, capture_output=True, text=True, timeout=60, check=False)
        report = json.loads(output.read_text(encoding='utf-8')) if output.exists() else None
        return result, report

    def test_complete_release_record_passes(self):
        result, report = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((report['result'], report['content'], report['problems']), ('PASS', 'MATCH', []))
        self.assertEqual(report['orb'], 'orbss/yamllint@2.2.0')
        self.assertEqual(report['release'], dict(
            rc_commit=self.rc, tag='v2.2.0', tag_commit=self.rc, tag_pipeline=PIPELINE,
            published_at='2026-11-14T20:43:54+09:00', published_at_utc='2026-11-14T11:43:54+00:00',
            published_at_jst='2026-11-14T20:43:54+09:00', changelog_date='2026-11-14'))
        for entry in report['inputs']:
            path = self.inputs[entry['role']]
            self.assertEqual((entry['path'], entry['raw_sha256']), (str(path), sha256(path)))
            self.assertEqual(entry['canonical_sha256'], report['inputs'][0]['canonical_sha256'])
            self.assertTrue(entry['obtained_how'])
        self.assertEqual([entry['role'] for entry in report['inputs']], ['rc', 'tag-ci', 'published'])
        self.assertFalse(report['raw_identical'])
        self.assertEqual(report['differences'], {'tag-ci vs rc': [], 'published vs rc': []})
        self.assertEqual(report['method'], compare.METHOD)
        self.assertEqual(report['tool']['sha256'], sha256(self.tool))
        self.assertEqual(report['tool']['pinned_sha256'], sha256(self.tool))
        self.assertEqual(report['tool']['checkout'], dict(commit=self.rc, clean=True))
        self.assertEqual((report['tool']['path'], report['checked_by']), ('.circleci/compare-orbs.py', 'reviewer'))
        self.assertEqual(json.loads(result.stdout), report)

    def test_inconsistent_or_incomplete_records_fail(self):
        other = 'b2' * 20
        changelog = self.base / 'CHANGELOG-without-heading.md'
        changelog.write_text('# Changelog\n\n## [Unreleased]\n')
        cases = [
            ('the tag does not point to the release candidate commit', dict(tag_commit=other)),
            ('rc_commit must be a full 40-character commit SHA', dict(rc_commit='abc1234')),
            ('the tag must be v2.2.0', dict(tag='v2.2.1')),
            ('tag_pipeline must be an https URL', dict(tag_pipeline='http://example.invalid/pipeline')),
            ('published_at needs a UTC offset', dict(published_at='2026-11-14T20:43:54')),
            ('published_at is not an ISO 8601 date and time', dict(published_at='yesterday')),
            ('differs from the publication date in JST 2026-11-15', dict(published_at='2026-11-14T16:00:00Z')),
            ('checked_by is blank', dict(checked_by='  ')),
            ('CHANGELOG has no "## [2.2.0] - YYYY-MM-DD" heading', dict(changelog=changelog)),
            ('must not contain credentials', dict(tag_pipeline=PIPELINE + '?circle-token=abc')),
        ]
        for message, changes in cases:
            result, report = self.run_tool(**changes)
            with self.subTest(message):
                self.assertEqual((result.returncode, report['result'], report['content']), (1, 'FAIL', 'MATCH'))
                self.assertTrue(any(message in problem for problem in report['problems']), report['problems'])
        source_cases = [
            ('how the published input was obtained is not recorded', {'rc': 'a', 'tag-ci': 'b'}),
            ('source rc is blank', {'rc': ' ', 'tag-ci': 'b', 'published': 'c'}),
            ('source tag-ci must not contain credentials', {'rc': 'a', 'tag-ci': 'Authorization: x', 'published': 'c'}),
        ]
        for message, sources in source_cases:
            result, report = self.run_tool(sources=sources)
            with self.subTest(message):
                self.assertEqual((result.returncode, report['result']), (1, 'FAIL'))
                self.assertTrue(any(message in problem for problem in report['problems']), report['problems'])

    def test_tool_must_be_the_pinned_tool_in_a_clean_rc_checkout(self):
        original = self.tool.read_bytes()
        self.tool.write_bytes(original + b'# edited\n')
        _, report = self.run_tool()
        self.assertEqual(report['result'], 'FAIL')
        self.assertIn('the tool differs from the version pinned in .circleci/compatibility-contract.json',
                      report['problems'])
        self.assertIn('tracked files are modified in the checkout', report['problems'])
        self.tool.write_bytes(original)
        (self.repo / 'README.md').write_text('after the release candidate\n')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', 'later change')
        _, report = self.run_tool()
        self.assertEqual(report['problems'], ['the tool did not run from a checkout of the release candidate commit'])
        self.manifest.write_text(json.dumps({'feature_suite_sha256': {'compare-orbs.py': '0' * 64}}))
        git(self.repo, 'commit', '-q', '-am', 'pin changed')
        head = git(self.repo, 'rev-parse', 'HEAD')
        _, report = self.run_tool(rc_commit=head, tag_commit=head)
        self.assertEqual(report['problems'],
                         ['the tool differs from the version pinned in .circleci/compatibility-contract.json'])
        loose = self.base / 'loose/.circleci/compare-orbs.py'
        loose.parent.mkdir(parents=True)
        shutil.copy2(self.tool, loose)
        _, report = self.run_tool(tool=loose)
        self.assertIn('the tool did not run from a git checkout of the release candidate', report['problems'])

    def test_failures_are_reported_and_reports_are_never_replaced(self):
        changed = copy.deepcopy(self.orb)
        execute_step(changed)['command'] = execute_step(changed)['command'].replace('exit 2', 'exit 0', 1)
        self.inputs['published'].write_text(render(changed), encoding='utf-8')
        result, report = self.run_tool()
        self.assertEqual((result.returncode, report['result'], report['content'], report['problems']),
                         (1, 'FAIL', 'MISMATCH', []))
        self.assertEqual(report['differences']['tag-ci vs rc'], [])
        self.assertTrue(report['differences']['published vs rc'][0]['path'].startswith('$.commands.execute.steps'))
        result, report = self.run_tool(published=self.base / 'missing.yml')
        self.assertEqual((result.returncode, report['content']), (1, 'NOT COMPARED'))
        self.assertTrue(report['problems'][0].startswith('published: cannot read'), report['problems'])
        existing = self.base / f'report-{self.count}.json'
        before = existing.read_bytes()
        self.count -= 1  # write to the same report path again
        result, _ = self.run_tool()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('reports are never replaced', result.stderr)
        self.assertEqual(existing.read_bytes(), before)

    def test_command_line_requires_every_record_field(self):
        result, report = self.run_tool(checked_by=None)
        self.assertEqual((result.returncode, report), (2, None))
        self.assertIn('--checked-by', result.stderr)
        result, report = self.run_tool(sources={'rc': 'a', 'tag-ci': 'b', 'published': 'c', 'local': 'd'})
        self.assertEqual(report, None)
        self.assertIn('--source takes ROLE=TEXT', result.stderr)
        result, _ = self.run_tool(tag_commit=None)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
