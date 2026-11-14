#!/usr/bin/env python3
"""Full-content comparison of the release Orbs, written as the release record (#5513).

Compares, in full, the packed Orb that the release candidate's CI verified,
the packed Orb that the tag pipeline generated and the published Orb source,
and records the comparison together with the release it belongs to:

  python .circleci/compare-orbs.py \\
      --rc rc-orb.yml --tag-ci tag-orb.yml --published published-orb.yml \\
      --source rc="<how it was obtained>" --source tag-ci="..." --source published="..." \\
      --rc-commit <SHA> --tag v2.2.0 --tag-commit <SHA> --tag-pipeline <URL> \\
      --published-at <ISO 8601 with offset> --checked-by <name> \\
      --output compare-report.json

Method. Each input is read as bytes (raw SHA-256) and parsed as exactly one
YAML document with PyYAML's safe composer. Only standard YAML tags are
accepted and mapping keys must be unique. Aliases and merge keys are
resolved. The resulting representation is compared as a whole: mappings
regardless of key order, sequences in order, and every scalar by its resolved
tag and exact text. Commands, jobs, executors, examples, parameters, defaults
and script strings are all included; nothing is removed, trimmed or
normalized inside a value. Comments, indentation, quoting and key order may
differ. The canonical SHA-256 is computed over that representation.

The record is accepted only when it is complete and consistent: the tool is
the version pinned in compatibility-contract.json and runs from a clean
checkout of the release candidate, the tag points to that commit, and the
CHANGELOG date of the version equals the publication date in JST.

Exit status 0 only for PASS: every input parsed, all inputs match and the
record has no problem. Otherwise 1; the report is still written. The tool
fetches nothing and does not use CI results.
"""
import argparse
import datetime
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORB = 'orbss/yamllint'
VERSION = '2.2.0'
ROLES = ('rc', 'tag-ci', 'published')
REFERENCE = 'rc'
MAX_DIFFERENCES = 50
JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')
COMMIT = re.compile(r'[0-9a-f]{40}')
SECRET = re.compile(r'token|authorization|password|secret|cookie|api[_-]?key|private[_-]?key', re.I)
YAML_TAG = 'tag:yaml.org,2002:'
MERGE = YAML_TAG + 'merge'
ALLOWED_TAGS = {YAML_TAG + name for name in (
    'str', 'int', 'float', 'bool', 'null', 'timestamp', 'binary', 'value', 'merge',
    'seq', 'map', 'set', 'omap', 'pairs')}
METHOD = ('Whole-file YAML representation comparison: one document, standard tags only, unique mapping '
          'keys, aliases and merge keys resolved; mappings regardless of key order, sequences in order, '
          'scalars by resolved tag and exact text. Comments, indentation, quoting and key order may '
          'differ; nothing inside a value is trimmed or normalized. Raw and canonical SHA-256 are recorded.')


class InputError(Exception):
    """The input cannot be compared as a single, unambiguous YAML document."""


# --- canonical representation -------------------------------------------------

def _key_signature(node):
    """Signature of a mapping key before merge keys are applied (for duplicate detection)."""
    if isinstance(node, yaml.ScalarNode):
        return json.dumps(['scalar', node.tag, node.value], ensure_ascii=False)
    if isinstance(node, yaml.SequenceNode):
        return json.dumps(['sequence', node.tag, [_key_signature(item) for item in node.value]])
    return json.dumps(['mapping', node.tag, sorted([_key_signature(k), _key_signature(v)] for k, v in node.value)])


def _validate(root):
    """Reject unsupported tags and duplicate keys anywhere in the document."""
    seen, pending = set(), [root]
    while pending:
        node = pending.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if node.tag not in ALLOWED_TAGS:
            raise InputError(f'unsupported YAML tag {node.tag!r} at line {node.start_mark.line + 1}')
        if isinstance(node, yaml.MappingNode):
            keys = set()
            for key, value in node.value:
                if key.tag != MERGE:
                    signature = _key_signature(key)
                    if signature in keys:
                        shown = key.value if isinstance(key, yaml.ScalarNode) else '<complex key>'
                        raise InputError(f'duplicate mapping key {shown!r} at line {key.start_mark.line + 1}')
                    keys.add(signature)
                pending.extend((key, value))
        elif isinstance(node, yaml.SequenceNode):
            pending.extend(node.value)


def _canonical(node, flattener, cache, active):
    if id(node) in cache:
        return cache[id(node)]
    if id(node) in active:
        raise InputError(f'recursive alias at line {node.start_mark.line + 1}')
    active.add(id(node))
    if isinstance(node, yaml.ScalarNode):
        result = ['scalar', node.tag, node.value]
    elif isinstance(node, yaml.SequenceNode):
        result = ['sequence', node.tag, [_canonical(item, flattener, cache, active) for item in node.value]]
    else:
        try:
            flattener.flatten_mapping(node)
        except (yaml.YAMLError, RecursionError) as error:
            raise InputError(f'invalid merge key: {error}') from error
        items = {}
        for key, value in node.value:  # merged pairs first, explicit pairs override them
            canonical_key = _canonical(key, flattener, cache, active)
            items[json.dumps(canonical_key, ensure_ascii=False)] = [
                canonical_key, _canonical(value, flattener, cache, active)]
        result = ['mapping', node.tag, [items[signature] for signature in sorted(items)]]
    active.discard(id(node))
    cache[id(node)] = result
    return result


def canonical(data):
    """Canonical representation of the single YAML document in data (bytes)."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as error:
        raise InputError(f'not UTF-8 text: {error}') from error
    loader = yaml.SafeLoader(text)
    try:
        root = loader.get_single_node()  # rejects a second document
    except yaml.YAMLError as error:
        raise InputError(f'invalid YAML: {error}') from error
    finally:
        loader.dispose()
    if root is None:
        raise InputError('the file holds no YAML document')
    if not isinstance(root, yaml.MappingNode) or root.tag != YAML_TAG + 'map':
        raise InputError('the top level is not a mapping')
    try:
        _validate(root)
        return _canonical(root, yaml.SafeLoader(''), {}, set())
    except RecursionError as error:
        raise InputError('the document is recursive or too deeply nested') from error


def canonical_sha256(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --- differences --------------------------------------------------------------

def _segment(key):
    if key[0] == 'scalar' and key[1] == YAML_TAG + 'str':
        text = key[2]
        return '.' + text if re.fullmatch(r'[A-Za-z0-9_-]+', text) else '[' + json.dumps(text, ensure_ascii=False) + ']'
    return '[' + json.dumps(key, ensure_ascii=False) + ']'


def _summary(value):
    if value[0] == 'scalar':
        text = value[2]
        return dict(tag=value[1].removeprefix(YAML_TAG), length=len(text),
                    sha256=sha256(text.encode('utf-8')), start=text[:60])
    return dict(kind=value[0], tag=value[1].removeprefix(YAML_TAG), entries=len(value[2]))


def differences(reference, other, path='$', found=None):
    """Paths where other differs from reference (at most MAX_DIFFERENCES)."""
    found = [] if found is None else found
    if len(found) >= MAX_DIFFERENCES:
        return found
    if reference[:2] != other[:2]:
        found.append(dict(path=path, difference='kind or tag differs',
                          reference=_summary(reference), other=_summary(other)))
    elif reference[0] == 'scalar':
        if reference[2] != other[2]:
            found.append(dict(path=path, difference='value differs',
                              reference=_summary(reference), other=_summary(other)))
    elif reference[0] == 'sequence':
        if len(reference[2]) != len(other[2]):
            found.append(dict(path=path, difference=f'{len(reference[2])} items in the reference, '
                                                   f'{len(other[2])} in the other input'))
        for index, (left, right) in enumerate(zip(reference[2], other[2])):
            differences(left, right, f'{path}[{index}]', found)
    else:
        left = {json.dumps(key, ensure_ascii=False): (key, value) for key, value in reference[2]}
        right = {json.dumps(key, ensure_ascii=False): (key, value) for key, value in other[2]}
        for signature in sorted(left.keys() | right.keys()):
            if len(found) >= MAX_DIFFERENCES:
                break
            if signature not in right:
                found.append(dict(path=path + _segment(left[signature][0]), difference='missing in the other input'))
            elif signature not in left:
                found.append(dict(path=path + _segment(right[signature][0]), difference='only in the other input'))
            else:
                differences(left[signature][1], right[signature][1], path + _segment(left[signature][0]), found)
    return found


def compare(paths):
    """Compare the inputs (role -> path). Returns (inputs, content, differences_by_pair, problems)."""
    inputs, parsed, problems = [], {}, []
    for role, path in paths.items():
        entry = dict(role=role, path=str(path))
        try:
            data = Path(path).read_bytes()
        except OSError as error:
            problems.append(f'{role}: cannot read {path}: {error.strerror or error}')
            inputs.append(entry)
            continue
        entry.update(bytes=len(data), raw_sha256=sha256(data))
        try:
            parsed[role] = canonical(data)
            entry['canonical_sha256'] = canonical_sha256(parsed[role])
        except InputError as error:
            problems.append(f'{role}: {error}')
        inputs.append(entry)
    if len(parsed) != len(paths):
        return inputs, 'NOT COMPARED', {}, problems
    found = {f'{role} vs {REFERENCE}': differences(parsed[REFERENCE], parsed[role])
             for role in paths if role != REFERENCE}
    content = 'MATCH' if all(entry['canonical_sha256'] == inputs[0]['canonical_sha256'] for entry in inputs) \
        else 'MISMATCH'
    if content == 'MISMATCH' and not any(found.values()):
        problems.append('canonical hashes differ but no difference was located')
    return inputs, content, found, problems


# --- release record -----------------------------------------------------------

def _git(*arguments):
    return subprocess.run(['git', '-C', str(ROOT), *arguments], capture_output=True, text=True, check=False)


def checkout_state():
    head, status = _git('rev-parse', 'HEAD'), _git('status', '--porcelain', '--untracked-files=no')
    if head.returncode != 0 or status.returncode != 0:
        return dict(commit=None, clean=None)
    return dict(commit=head.stdout.strip(), clean=status.stdout.strip() == '')


def pinned_tool_sha256():
    try:
        manifest = json.loads((ROOT / '.circleci/compatibility-contract.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return (manifest.get('feature_suite_sha256') or {}).get(Path(__file__).name)


def changelog_date(path, version):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError:
        return None
    match = re.search(r'^## \[' + re.escape(version) + r'\] - (\d{4}-\d{2}-\d{2})$', text, re.M)
    return match.group(1) if match else None


def record_problems(args, sources, tool_sha256, checkout, changelog):
    problems = []
    texts = dict(checked_by=args.checked_by, tag_pipeline=args.tag_pipeline,
                 **{f'source {role}': text for role, text in sources.items()})
    for name, text in texts.items():
        if not text.strip():
            problems.append(f'{name} is blank')
        if SECRET.search(text):
            problems.append(f'{name} must not contain credentials or token-like text')
    for role in ROLES:
        if role not in sources:
            problems.append(f'how the {role} input was obtained is not recorded (--source {role}=...)')
    for name in ('rc_commit', 'tag_commit'):
        if not COMMIT.fullmatch(getattr(args, name)):
            problems.append(f'{name} must be a full 40-character commit SHA')
    if args.rc_commit != args.tag_commit:
        problems.append('the tag does not point to the release candidate commit')
    if args.tag != 'v' + args.version:
        problems.append(f'the tag must be v{args.version}')
    if not re.fullmatch(r'https://\S+', args.tag_pipeline):
        problems.append('tag_pipeline must be an https URL')
    published = None
    try:
        published = datetime.datetime.fromisoformat(args.published_at)
    except ValueError:
        problems.append('published_at is not an ISO 8601 date and time')
    if published is not None and published.tzinfo is None:
        problems.append('published_at needs a UTC offset')
        published = None
    if tool_sha256 != pinned_tool_sha256():
        problems.append('the tool differs from the version pinned in .circleci/compatibility-contract.json')
    if checkout['commit'] is None:
        problems.append('the tool did not run from a git checkout of the release candidate')
    else:
        if checkout['commit'] != args.rc_commit:
            problems.append('the tool did not run from a checkout of the release candidate commit')
        if not checkout['clean']:
            problems.append('tracked files are modified in the checkout')
    if changelog is None:
        problems.append(f'CHANGELOG has no "## [{args.version}] - YYYY-MM-DD" heading')
    elif published is not None and published.astimezone(JST).date().isoformat() != changelog:
        problems.append(f'the CHANGELOG date {changelog} differs from the publication date in JST '
                        f'{published.astimezone(JST).date().isoformat()}')
    return problems, published


def parse_sources(values):
    sources = {}
    for value in values or []:
        role, separator, text = value.partition('=')
        if not separator or role not in ROLES:
            raise SystemExit(f'--source takes ROLE=TEXT with ROLE one of {", ".join(ROLES)}: {value!r}')
        if role in sources:
            raise SystemExit(f'--source {role} is given twice')
        sources[role] = text
    return sources


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--rc', type=Path, required=True,
                        help='packed Orb that the release candidate pipeline verified (phase5-config/orb.yml)')
    parser.add_argument('--tag-ci', type=Path, required=True,
                        help='packed Orb generated by the tag pipeline (phase5-config/orb.yml)')
    parser.add_argument('--published', type=Path, required=True, help='published Orb source from the registry')
    parser.add_argument('--source', action='append', metavar='ROLE=TEXT',
                        help='how each input was obtained (pipeline, job, command); give all three roles')
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--rc-commit', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--tag-commit', required=True, help='commit the tag points to, as observed')
    parser.add_argument('--tag-pipeline', required=True, help='URL of the tag pipeline')
    parser.add_argument('--published-at', required=True, help='observed publication time, ISO 8601 with offset')
    parser.add_argument('--checked-by', required=True)
    parser.add_argument('--changelog', type=Path, default=ROOT / 'CHANGELOG.md')
    parser.add_argument('--output', type=Path, required=True, help='new file for the JSON report')
    args = parser.parse_args(argv[1:])
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit(f'{args.output} already exists; reports are never replaced')
    sources = parse_sources(args.source)
    tool_sha256 = sha256(Path(__file__).read_bytes())
    checkout = checkout_state()
    changelog = changelog_date(args.changelog, args.version)
    inputs, content, found, problems = compare({'rc': args.rc, 'tag-ci': args.tag_ci, 'published': args.published})
    for entry in inputs:
        entry['obtained_how'] = sources.get(entry['role'], '')
    record, published = record_problems(args, sources, tool_sha256, checkout, changelog)
    problems += record
    result = 'PASS' if content == 'MATCH' and not problems else 'FAIL'
    report = dict(
        result=result, content=content, problems=problems,
        orb=f'{ORB}@{args.version}',
        release=dict(rc_commit=args.rc_commit, tag=args.tag, tag_commit=args.tag_commit,
                     tag_pipeline=args.tag_pipeline, published_at=args.published_at,
                     published_at_utc=published.astimezone(datetime.timezone.utc).isoformat() if published else None,
                     published_at_jst=published.astimezone(JST).isoformat() if published else None,
                     changelog_date=changelog),
        inputs=inputs,
        raw_identical=len({entry.get('raw_sha256') for entry in inputs}) == 1,
        differences=found,
        method=METHOD,
        tool=dict(path='.circleci/' + Path(__file__).name, sha256=tool_sha256, pinned_sha256=pinned_tool_sha256(),
                  checkout=checkout, python=platform.python_version(), pyyaml=yaml.__version__),
        checked_by=args.checked_by,
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        note=('The release fields are declared by the confirmer and checked for consistency only. '
              'A CI success is not used. PASS covers the compared files and this record only.'))
    text = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    try:
        with open(args.output, 'x', encoding='utf-8') as output:
            output.write(text)
    except OSError as error:
        raise SystemExit(f'cannot write the report {args.output}: {error.strerror or error}') from error
    print(text, end='')
    return 0 if result == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
