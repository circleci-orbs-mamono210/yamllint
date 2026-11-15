# v2.3.0 Phase 1 measurement plan, H9 (#5543)

Target: the Phase 1 design investigation of v2.3.0 (parent #5542). This
document fixes the execution conditions of H9 and the candidate list and
observation plan that #5544 and #5545 both use.

This document is a plan. It is not a measurement record, not an adoption of
any D01-D08 option, not a product change, and not an approval to run
anything. Nothing here declares an environment supported. The approval that
#5544 and #5545 need is recorded in section 11 by a human, and it is empty
until then.

## 1. Basis

| Item | Value |
| --- | --- |
| Roadmap | `230_ロードマップ`, Redmine project 318, Wiki version 1 |
| Parent ticket | #5542 (Phase 1), children #5543 - #5548 |
| Repository baseline | `2fc343180c9e13660889ac5643b75fbcabd513ea` (main at the time this plan was written) |
| Published Orb baseline | `orbss/yamllint@2.2.0`, published 2026-11-14T04:21:08Z (registry, read 2026-11-15 JST) |
| Final decision owner | D01-D08 adoption is #5547; this document only prepares evidence |

The basis does not move to a later Wiki version or a later commit on its
own. If a later basis becomes necessary while measuring, the difference and
its effect are reported and a human decides which version is used, per
#5542 "成果物を後で改訂する場合".

## 2. Facts read from the baseline commit

These are read from the files at the baseline commit, not assumed. Every
case below is written against them.

| Fact | Source |
| --- | --- |
| Installation runs `python -m pip install yamllint`, or `yamllint==<version>` when `install.version` is non-empty. The name used is `python`, not `python3`. | `src/scripts/install.sh` |
| The version display step runs `yamllint --version`, resolved from `PATH`. | `src/scripts/show-version.sh` |
| Linting and listing run `yamllint` resolved from `PATH`, in a run step separate from the version display. | `src/commands/execute.yml`, `src/scripts/execute.sh` |
| Saving requires `python3` on `PATH`; absence is refused with exit status 2 before yamllint starts. The helper runs as `python3 -I` and imports only `os`, `select`, `stat`, `sys`. | `src/scripts/execute.sh` |
| Destination refusals happen before yamllint starts: newline in the path, a name of `""`, `.` or `..`, a missing or non-directory parent, any existing entry, a path equal to a target, a path inside a target directory, a path equal to `config_file`. Paths are resolved with `os.path.realpath` and no `~`, variable or glob expansion. | `src/scripts/execute.sh` |
| Exit status priority: a non-zero yamllint status wins; otherwise a relay or save problem fails the step with status 2. | `src/scripts/execute.sh` |
| The default executor image is `cimg/python:3.14`; `resource_class` is an enum defaulting to `small`. | `src/executors/default.yml` |
| The repository lint configuration is `extends: relaxed` with `line-length.max: 200`, so target selection follows upstream `relaxed` behaviour. | `.yamllint` |
| The setup pipeline runs `orb-tools/lint`, `orb-tools/pack`, `orb-tools/review`, `shellcheck/check` and `orb-tools/continue`; `test-deploy` runs 11 single jobs plus two 4-case matrices, and `orb-tools/pack` requires all 19; `orb-tools/publish` ignores every branch, matches only tags `^v[0-9]+\.[0-9]+\.[0-9]+$`, and uses context `CIRCLECI_ORBS`. | `.circleci/config.yml`, `.circleci/test-deploy.yml` |
| The CI contract checks do not enumerate repository Markdown files, so adding this document does not change the packed Orb or any contract fixture. | `.circleci/check-ci-contract.py`, `.circleci/prepare-ci-contract.sh` |

Consequence used by the plan: in an environment that provides `python3` but
not `python`, the existing installation path fails on the command name
alone, independently of any PEP 668 marker. The two conditions are measured
separately and never recorded as one result.

## 3. Candidate environments

Identifiers are stable for #5544 and #5545. Values marked "planned" have
not been observed; they are expectations that case M-00 verifies first.
Measured values replace them only in the measurement records, never here.

| ID | Image reference | Role | `python` (planned) | `python3` (planned) | PEP 668 marker (planned) | Stage A preparation (planned) |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | `cimg/python:3.14` | Existing baseline, part of the fixed four combinations | present | present | absent | none |
| E02 | `cimg/python:3.13` | Existing baseline, part of the fixed four combinations | present | present | absent | none |
| E03 | `ubuntu:22.04` | D06 mandatory candidate 1: `python3` only, marker absent, pip usable, no virtual environment | absent | present after stage A | absent | `apt-get install python3 python3-pip git ca-certificates openssh-client` as root |
| E04 | `ubuntu:24.04` | D06 mandatory candidate 2: real marker in the base environment, installation into a separate virtual environment | absent | present after stage A | present | same as E03 |
| E05 | `debian:12` | Reserve for E04 only. Not executed unless E04 fails M-00 | absent | present after stage A | present | same as E03 |

Consumer-side preparation runs in two stages, so that the need for it is
measured instead of assumed:

- **Stage A**, before M-00's second reading, installs only what is needed to
  reach the repository and to run `python3` and pip. It deliberately leaves
  out the distribution's virtual-environment package. M-00 records that the
  package is absent.
- **Stage B** happens inside M1-03, and only if creating a virtual
  environment fails without it. The failure, the package install and the
  retry are three separate readings. In E01 and E02 no stage B is expected,
  and the plan records that no install was needed.

Both stages are consumer-side work. Neither is an Orb capability, and #5544
records them as consumer-side preparation.

Mapping to the mandatory candidates required by #5542 C3:

- "`python3` のみの環境" -> E03. The condition measured is the absence of a
  `python` command together with a usable `python3` and pip, with no
  virtual environment and no marker.
- "実在する管理標識を持つ基底環境から別仮想環境へ導入する環境" -> E04
  (reserve E05). The condition measured is a real `EXTERNALLY-MANAGED`
  file in the base interpreter's standard library directory, a refusal when
  installing into that base environment, and a separate success when
  installing into a virtual environment.

E01 and E02 are present so that every observation has a baseline reading
from an environment the project already supports. They do not satisfy
either mandatory candidate.

### 3.1 How the marker is measured

The marker is never inferred from an image name. In every candidate, M-00
records all of the following and keeps them separate:

1. `python3 -c 'import sysconfig; print(sysconfig.get_path("stdlib"))'`,
   then `ls -l "<that directory>/EXTERNALLY-MANAGED"` with its exit status.
2. `ls -l /usr/lib/python3*/EXTERNALLY-MANAGED` with its exit status, as a
   second reading that does not depend on `sysconfig`.
3. The first 20 lines of the file when it exists.
4. `python3 -c 'import sys; print(sys.prefix, sys.base_prefix)'`, so that
   "inside or outside a virtual environment" is recorded independently of
   the marker.
5. The same four readings again after the consumer-side preparation of
   section 3, because package installation can change them.

A test that only hides the `python` or `python3` command is never recorded
as a managed-environment result. Where a marker is expected but absent, or
absent but present, M-00 stops that candidate and the case is handled by
section 3.2.

### 3.2 Image pinning, and what to do when a precondition fails

Pinning method: the tag reference in the table. A digest is not observable
from inside the container, so the identity actually recorded is
`/etc/os-release`, `uname -m`, `python3 -VV`, the resolved stdlib path, and
the installed versions of the packages stage A added, of `pip`, and of the
virtual-environment package if and when stage B adds it in M1-03. The
`ubuntu:*` and `debian:*` tags are mutable, so a later run can
differ; the record, not the tag, identifies what ran. If a human needs a
re-runnable identity, the digest shown in the CircleCI job's image line is
recorded by the human for the following runs. Architecture is expected to
be `x86_64` on the CircleCI Docker executor and is recorded, not assumed.

If M-00 shows that a candidate does not satisfy its role:

1. The candidate is not silently replaced and the measurement for it does
   not continue.
2. The observed values, the role it failed, and the effect on D06 and on
   the mandatory range are recorded in the measurement record.
3. For E04 only, the reserve E05 may be used, because it carries the same
   role. Using it is reported with the reason.
4. Any other change or removal of a candidate is a human decision under
   #5542 C3: the reason, the effect on D06 and the mandatory range, and the
   formal Roadmap change required are recorded before the candidate set
   changes. A reduced mandatory range is never adopted by omission.

## 4. Observation items to cases

The eight observation items are the ones required by #5542 "実測記録に必要
な項目". Every item has at least one owning case. "ref" marks a reading
that only re-identifies what the owning case established.

| # | Observation item | #5544 (M1) | #5545 (M2) |
| --- | --- | --- | --- |
| 1 | Execution environment identity | M-00, M1-01 (owner) | M-00 (ref) |
| 2 | Management marker | M-00, M1-02 (owner) | M-00 (ref) |
| 3 | venv and pip | M1-03 (owner) | - |
| 4 | Consumer-side preparation | M-00, M1-03 (owner) | M-00 (ref) |
| 5 | Handoff between run steps | - | M2-01, M2-02 (owner) |
| 6 | Placement and saving | M1-05 (placement, owner) | M2-04 (decision owner), M2-05 (saving interpreter, owner) |
| 7 | Files created by installation | M1-04 (owner) | M2-03 (ref, target selection only) |
| 8 | Shape of the execution target | M1-06 (installation destination, owner) | M2-03 (display, lint, listing target, owner) |

Case to issue mapping: M-00 runs in both stages. M1-xx belongs to #5544.
M2-xx belongs to #5545. D numbers are the roadmap's design questions; the
cases produce material for them and decide nothing.

## 5. Cases for #5544

Every case is run per candidate. Each case records the exact command, its
exit status, its stdout and stderr, and the observed values. A case that
cannot be run records the reason and the limit it places on the judgment;
it is never recorded as a pass.

### M-00 Preconditions and identity

- Input: candidate ID, image reference, the stage A commands of section 3.
- Operation: record identity and marker readings of section 3.1 before and
  after stage A; record `id -u`, `uname -m`, `/etc/os-release`,
  `command -v python python3 pip pip3 git`, `python3 -VV`, the package
  versions installed by stage A, and that the distribution's
  virtual-environment package is not yet installed.
- Observation: items 1, 2, 4.
- Judgment: the candidate satisfies its role in section 3 exactly. A
  `python` command found in E03, E04 or E05, or a marker state opposite to
  the role, fails the precondition.
- If missing: stop that candidate and apply section 3.2. Do not continue to
  M1-01.

### M1-01 Identity of the measured revision

- Input: the checked out experiment branch.
- Operation: record the branch name, the experiment commit SHA, its
  subject line, `git status --porcelain`, `sha256sum .circleci/config.yml`,
  the CircleCI pipeline number, workflow ID and job URL.
- Observation: item 1.
- Judgment: two different SHAs are involved and they are not compared with
  each other. The plan version is the commit of this file on `main`. The
  experiment commit is the commit on the throwaway branch that carries the
  measurement configuration. The recorded experiment commit SHA must equal
  the approved experiment commit for this stage in section 11.1, the
  recorded configuration hash must equal the approved hash for this stage,
  and the working tree must be clean.
- If missing: stop. An unidentified revision cannot support #5542 C2.

### M1-02 Refusal in the base environment

- Input: the baseline `src/scripts/install.sh` and a direct pip call.
- Operation: three readings, each recorded separately.
  1. `PARAM_VERSION="" bash src/scripts/install.sh`.
  2. `PARAM_VERSION=1.38.0 bash src/scripts/install.sh`.
  3. `python3 -m pip install yamllint==1.38.0` against the base
     environment, with no option that bypasses the marker.
- Observation: items 2, 3. The exit status, the first error line, and
  whether the failure is the missing `python` command or the marker.
- Judgment: a `python: command not found` result and an
  `externally-managed-environment` result are different findings and are
  recorded as such. Neither is recorded as a venv result.
- If missing: record the status that did occur. Do not add `sudo`, remove
  the marker, or pass any pip option that overrides it; the roadmap keeps
  that out of scope for D02.

### M1-03 Virtual environment and pip preparation

- Input: the candidate after stage A, which deliberately has not installed
  the distribution's virtual-environment package.
- Operation: readings in this order, each recorded separately.
  1. `python3 -m venv /tmp/meas/venv`, the first attempt, measured in the
     stage A state, with its exit status and diagnostic.
  2. The state that attempt left: the listing of `/tmp/meas/venv/bin` and
     whether `pyvenv.cfg` exists.
  3. `/tmp/meas/venv/bin/python -m pip --version`, with its exit status.
  4. `python3 -m venv --without-pip /tmp/meas/venv-nopip`, which does not
     need `ensurepip`, so that creation and pip bootstrapping are separated.
  5. `python3 -c 'import ensurepip'`, to record whether the module is there.
  6. Stage B, only when the first attempt did not produce a usable virtual
     environment: its exit status was not 0, or there is no
     `/tmp/meas/venv/bin/python`, or reading 3 failed. The partial result is
     moved to `/tmp/meas/venv-partial` and listed, so M1-05 can use it as
     real remains of an interrupted creation. Then the distribution's
     virtual-environment package is installed, its version recorded, and a
     second `python3 -m venv` attempt and pip check follow.
  7. `/tmp/meas/venv/bin/python -m pip install yamllint==1.38.0`.
  Record the privileges each step needed and whether any needed root.
- Why the condition is not "no interpreter": the standard library's
  `venv` places the interpreter before it bootstraps pip. When `ensurepip`
  is missing, creation fails with a non-zero status but `bin/python` and
  `pyvenv.cfg` are already there, and the environment has no pip. An
  interpreter alone is therefore not evidence of a usable environment.
- Observation: items 3, 4.
- Judgment: creation and installation succeed in a separate virtual
  environment even where M1-02 was refused, and the readings show whether
  stage B was needed at all. Where it was, the install and the retry are
  recorded as consumer-side preparation and never as an Orb capability.
  A candidate where the first attempt already succeeds with a usable pip is
  recorded as needing no stage B, not as having had one. A virtual
  environment with an interpreter and no usable pip is not a success.
- If missing: record which of creation, `ensurepip`, the package install,
  pip, or the network failed, and the privileges that were needed.

### M1-04 Files created by installation

- Input: a fixture tree under the working directory containing known
  `*.yml`, `*.yaml` and non-YAML files, with the repository `.yamllint` in
  effect.
- Operation: record `yamllint --list-files .` before creating anything.
  Create a virtual environment inside the working directory, install
  yamllint into it, and record `yamllint --list-files .` again, with the
  diff, the count, and the paths added. Repeat with the destination outside
  the working directory. Repeat the inside case with an `ignore` entry
  covering the virtual environment directory, and with `targets` naming
  only the fixture directory.
- Observation: item 7.
- Judgment: whether files created by installation can enter the selection,
  where they are, and which of configuration, target selection and
  placement changes that. Existence is a measured result, not a given.
- If missing: record the listing that was obtained and what remains
  unknown. Do not alter `ignore` in any product file to hide a finding.

### M1-05 Placement, existing paths, interrupted runs, reuse, carry-in

- Input: the virtual environment destination used above, plus prepared
  conflicting paths, all under `/tmp/meas`.
- Operation, each recorded separately: creation onto a path that is an
  existing non-empty directory; onto an existing regular file; onto an
  existing complete virtual environment; onto prepared remains of an
  interrupted creation; onto the real remains M1-03 kept in
  `/tmp/meas/venv-partial`, where it exists, with a pip check afterwards;
  a second creation after a successful one; a
  relative path, a path containing `~`, and a path containing a `$`
  variable reference, recorded as written and as resolved.
- Observation: item 6, placement side.
- Judgment: which refusals and which successes occur, and what a command
  can tell from its inputs alone. No reuse, deletion or re-creation
  behaviour is implemented as product behaviour by this case.
- If missing: record the case as not run with its reason.

Carry-in from another job is measured on E01 only, as a pair of jobs that
persist and attach a workspace. For E03, E04 and E05 it is recorded as not
applicable with the reason that a workspace needs further consumer-side
preparation in those images, and the limit this places on D04 is stated in
the record.

### M1-06 Installation destination and execution target shape

- Input: the virtual environment of M1-03.
- Operation: record `command -v yamllint` before and after, the absolute
  path of the installed executable, its first line, `python -m pip show -f
  yamllint` paths, and whether the destination is on `PATH` without further
  action.
- Observation: item 8, destination side.
- Judgment: the destination and the version installed are identifiable, and
  whether `PATH` resolution reaches it. The display and lint targets are
  measured by #5545, not here.
- If missing: record what was resolvable.

### M1-07 Evidence index

- Operation: produce the per-candidate table that maps each observation to
  the file, job URL and exit status that supports it, and the list of cases
  not run with reasons.
- Judgment: #5544 C6 can be read from this table alone, including that no
  verification configuration reached `main`.

## 6. Cases for #5545

These start only after #5544 is complete and its deliverable version is
fixed, per #5545 "対象範囲". M-00 is repeated so that the environment is
re-identified in the new pipeline. M2-00 records the experiment commit, its
subject line and the configuration hash, and they are compared with the
#5545 rows of section 11.1 exactly as M1-01 does for #5544.

### M2-01 Explicit handoff across run steps

- Input: the virtual environment created in an earlier run step of the same
  job.
- Operation: step A creates and installs, and writes the destination to a
  file. Step B, a separate `run` step, reads the file and runs the
  interpreter and yamllint by absolute path: `--version`, `--list-files`,
  and a lint of the fixture tree. Step C runs after a consumer's own
  intervening step that changes `PATH`.
- Observation: item 5.
- Judgment: what an explicitly named destination still resolves to across
  the step boundary, and what a consumer's own step can disturb. A result
  from a child process inside one step is never recorded as a step boundary
  result.
- If missing: record the step that failed and its status.

### M2-02 `BASH_ENV` handoff

- Input: the same virtual environment, and the `BASH_ENV` file as the job
  received it.
- The content of that file is never printed, copied into a record or
  uploaded. A project environment variable in it could be a credential, and
  section 9 keeps credentials out of every record. The readings below are
  all indirect, and they answer the same questions.
- Operation, each recorded separately.
  1. Before any append: the file's byte count, line count and the first 12
     characters of its SHA-256, plus the byte count and full hash kept aside
     for reading 3. None of its lines are read out.
  2. Append `export MEAS_MARKER_KEPT=1` and an export of the destination.
     Record the new byte count and hash prefix.
  3. In a separate run step: `PATH`, `command -v yamllint`, the value of
     `MEAS_MARKER_KEPT`, and whether the bytes that were there before the
     append are unchanged, judged by re-hashing exactly that byte range and
     comparing it with the hash kept in reading 1. A changed or truncated
     range is reported as such, still without printing it.
  4. Append a destination string containing a benign substitution marker,
     once unquoted and once quoted, then read both back in a later step.
     Only these two values, which the plan itself wrote, are printed. This
     shows whether a value is evaluated as a shell instruction.
  5. A second append in the same job, to observe repeated calls.
- Observation: item 5.
- Judgment: the difference from M2-01 in what the later step sees, whether
  the consumer's own `BASH_ENV` content survives, and whether a value can
  act as an instruction. No method is adopted here; D03 is #5547.
- If missing: record the reading obtained and what remains unknown. If the
  file is absent, record that and do not create one to make the case run.

### M2-03 Display, lint and listing targets

- Input: two virtual environments with different yamllint versions, and the
  base environment.
- Operation: record for each of `yamllint --version`, a lint run, and
  `--list-files`: the executable actually resolved, its absolute path,
  `python -c 'import yamllint; print(yamllint.__file__)'` for the selected
  interpreter, and whether `python -m yamllint --version` works. Repeat
  with a different yamllint present earlier on `PATH`, and with the
  destination's executable absent from `PATH`.
- Observation: items 8, and item 7 as a reference reading of target
  selection.
- Judgment: whether the version displayed, the version that linted and the
  version that listed are the same installation, and whether a module
  launch is available. A launch method is not assumed to work before it is
  measured.
- If missing: record the resolution that occurred.

### M2-04 Who can judge placement

- Input: the baseline `src/scripts/execute.sh`, a fixture target tree, and
  a `config_file`.
- Operation: run the script with `PARAM_OUTPUT_FILE` set, in turn, to a
  path inside a target directory, a path equal to a target file, a path
  equal to `config_file`, a path whose parent does not exist, a path that
  already exists, a path containing `..`, and a path outside every target.
  Record each exit status and the exact diagnostic. Separately record the
  inputs that the installation step receives, to show what it does not know
  about targets.
- Observation: item 6, decision side.
- Judgment: the information each command has, the refusals a machine can
  make from it, and the constraints that can only be documentary.
  Information that is not obtained is never recorded as obtained.
- If missing: record the case as not run.

### M2-05 Interpreter used for saving

- Input: the baseline save helper, which needs `python3` on `PATH` and
  imports `os`, `select`, `stat`, `sys`, and runs as `python3 -I`.
- Operation: four readings. (a) baseline, `python3` on `PATH`. (b) a `PATH`
  without `python3`, to record the refusal and its exit status. (c) a
  `PATH` whose only `python3` is the selected virtual environment's, to
  record whether saving works and what it depends on. (d) a working
  directory containing a `select.py` file, to record whether the `-I`
  isolation still ignores it. Also record the presence of the four modules
  in the virtual environment's interpreter, and a run with saving disabled
  to confirm no save dependency is added to it.
- Observation: item 6, saving side.
- Judgment: both D05 options are described by measured dependencies,
  separation and diagnostics. Using one interpreter for both is not a pass
  criterion. A result that weakens the isolation the current `-I` provides
  is not recorded as a working option.
- If missing: record which reading failed.

### M2-06 Output contract and exit status priority

- Operation, part 1: with saving disabled and enabled, record stdout,
  stderr, the version display, the saved file's bytes, and the exit status
  for a clean tree; a tree with a lint error; a warning-only tree without
  and with strict mode; a warning-only tree with warnings hidden; a
  destination refused before the run; and a destination whose parent
  directory is not writable. The last one is refused by permission bits
  only where the default user is not root, so `id -u` is recorded with it
  and a root candidate records it as not applicable.
- Operation, part 2, the priority between a lint status and a save failure
  that happens while the result is being written. Four readings, each
  recorded separately:
  1. A control run over a tree that produces many warnings and no error,
     with saving enabled. Expected to show the lint status and a saved file.
  2. A control run over a tree that produces many errors, with saving
     enabled.
  3. Reading 1's run repeated with `RLIMIT_FSIZE` set below the size of the
     output, applied to the Orb script only. The step log passes through a
     pipe, which the limit does not restrict, so the record itself is
     written by an unlimited process.
  4. Reading 2's run repeated the same way.
  Then record whether each destination exists afterwards, and whether any
  temporary file was left behind. This is the same fault mechanism the
  repository already uses in `.circleci/test-output-file.py`, and the limit
  applies to root as well, so every candidate can run it.
- Observation: item 6.
- Judgment: the existing separation of stdout, stderr and version display,
  new-file-only behaviour, collision refusal, and the priority in which a
  non-zero yamllint status wins over a save problem, are unchanged by any
  environment selection used in these cases. Readings 3 and 4 establish the
  priority directly: a save failure after a successful lint, and a save
  failure after a non-zero lint, are different results and are recorded as
  such. A status converted to 0 anywhere in the pipeline is never used as
  evidence of a step's non-zero exit.
- If missing: record the case as not run. If the limit does not make the
  write fail, record the sizes observed and say that the priority was not
  established, rather than inferring it.

### M2-07 Failure codes, diagnostics and limits

- Operation: collect every exit status and first diagnostic line from M2-01
  to M2-06 into one table, grouped by environment selection, pre-start
  refusal, lint failure and save failure, and note where a status alone
  cannot distinguish two causes.
- Judgment: #5545 C6 and C7 can be read from this table, and the limits
  passed to D07 and D08 are explicit.

## 7. H2 and H7 planning issues

Recorded here because they change what is measured. They are not decided
here.

| Issue | Effect on this plan |
| --- | --- |
| H2, whether a Python-selection-only route without a virtual environment is in the mandatory range | E03 exists so the route has a measured success path, and M1-02 and M1-03 keep "no `python` command" and "marker present" apart. The plan does not assume the route is adopted. |
| H7, the option of not using `sudo` and not bypassing protection | No case adds `sudo`, removes the marker, or passes a pip option that overrides it. The refusal in M1-02 is recorded as a result, not worked around. |
| H7, the option of not changing target selection implicitly | M1-04 measures the created files and records the conditions under which they enter the selection. No product `ignore` or target default is changed to hide them. |
| H7, the option of no implicit substitution | M2-03 measures what resolution actually happens when the destination is not on `PATH`; it does not implement a fallback. |

No new public parameter name, type or default is defined by this document.
Where a case needs to name a destination, it uses an environment variable
of the experiment configuration, which is a temporary experiment mechanism
and not a proposed Orb input. The distinction between a compared method and
a temporary experiment mechanism is stated in each case above.

## 8. H9 execution conditions

| Item | Condition |
| --- | --- |
| Measurement drafting, case design, configuration drafting, record drafting, evidence mapping | Claude, Redmine user ID 11 |
| Branch push, pipeline start, CircleCI UI confirmation, artifact download, commit to `main`, Redmine journal entries, approvals | the human, Redmine user ID 3 |
| Repository | `circleci-orbs-mamono210/yamllint` |
| CI project | `gh/circleci-orbs-mamono210/yamllint`, the existing project |
| Place of execution | CircleCI Docker executor, `resource_class: small`, on throwaway branches of that repository |
| Temporary configuration | `.circleci/config.yml` is replaced on the throwaway branch by the stage's measurement configuration. It is a non-setup configuration and defines only the measurement jobs. It is not committed to `main`, so it is identified by content hash, not by a path in this repository. |
| Approved configuration content | #5544: SHA-256 `576cdc1a4d1c0510d22fca6c1a1b13ed314bac85dfc4aaaa361d10b447dde4cf`. #5545: SHA-256 `aec39ba06b7444726565ab87ffe0ee4396e9e68c64555567c2b8b32d8a6a68b8`. A different hash is a different configuration and needs its own approval. |
| Branches | `exp/230-m1` for #5544, `exp/230-m2` for #5545. Never merged. Deleted after section 9 evacuation is confirmed. |
| Plan version and experiment commit | Two different commits. The plan version is the commit of this file on `main`. The experiment commit is the commit on the throwaway branch that carries the measurement configuration. Section 11.1 records each separately, the experiment commit once per stage. |
| Order of commit, approval, push and start | 1. The human creates the experiment commit locally and does not push it. A commit SHA depends only on the local commit, so pushing it later does not change it. 2. The human records that SHA and the configuration hash in section 11.1 and completes the approval. 3. The human pushes the branch. 4. The pipeline stops at the job `hold-until-approved`, of type `approval`, and nothing is measured until the human approves it in the CircleCI UI. Section 11.1 is the authoritative approval; the hold is a safeguard that keeps the start of the measurement separate from the push and gives the start its own timestamp. |
| Why `[ci skip]` is not used | On GitHub OAuth and Bitbucket Cloud pipelines, a skip tag in the commit message also blocks a later trigger from the API or the web app, so it cannot be combined with a manual start after the approval. The hold job does not have that limitation. |
| Revision identification | Each job records the experiment commit SHA, its subject line and `sha256sum .circleci/config.yml`. All three go into the measurement record with the pipeline number, workflow ID and job URLs. The SHA and the hash must equal the values approved for that stage in section 11.1; a mismatch stops the stage. |
| Keeping it out of `main` | The measurement configuration and its fixtures exist only on the throwaway branches. The only files this phase adds to `main` are this plan and the two measurement records of section 9. `git log --oneline main -- .circleci/config.yml` and a diff of `main` against the baseline are recorded after the runs to show no verification configuration reached `main`. |
| Experiment resources | Everything the cases create lives under `/tmp/meas` or inside the job's checkout, both discarded with the container. No file outside the job container is created, changed or deleted. |
| Privileges | In E03, E04 and E05 the image's default user is root, so the preparation runs `apt-get` without `sudo`; M-00 records `id -u`. In E01 and E02 no case uses `sudo`. |
| Cleanup | None is required outside the container. The branch deletion above is the only persistent cleanup, and it happens only after evacuation. |

### 8.1 CI consumption

Because the throwaway branch replaces `.circleci/config.yml` with a
non-setup configuration, the 5 setup jobs and the 19 `test-deploy` jobs of
`main` do not run on it, and no job in the measurement configuration is
named `orb-tools/pack` or `orb-tools/publish`.

| Stage | Jobs | Notes |
| --- | --- | --- |
| #5544, `exp/230-m1` | 6: 4 candidate jobs, plus the carry-in producer and consumer pair on E01 | Plus the approval hold, which runs on no executor. E05 adds 1 only if E04 fails M-00 |
| #5545, `exp/230-m2` | 4 candidate jobs | Plus the approval hold |

All jobs use `resource_class: small`. No job references the `CIRCLECI_ORBS`
context, no tag is created, and `orb-tools/publish` cannot be reached from
these branches: in the `main` configuration it already ignores every branch
and matches only `^v[0-9]+\.[0-9]+\.[0-9]+$` tags, and it is absent from
the measurement configuration. A re-run after a plan revision repeats the
same job counts and is recorded as a separate run with its own approval
reference.

## 9. Evidence retention and evacuation

Retention of CircleCI-hosted evidence, read from CircleCI documentation on
2026-11-15 JST:

| Object | Retention | Note |
| --- | --- | --- |
| Artifacts | 30 days by default, and 30 days is also the maximum that can be configured | The organisation can lower it under Plan, Usage Controls, so the default is not assumed. The actual setting is confirmed before the first run and recorded in section 11 |
| Workspaces and caches | 15 days by default, lowerable the same way | Only the E01 carry-in pair uses a workspace |
| Pipeline and job data, including step output | By plan: 90 days on Free, 180 days on Performance and Custom Performance, 2 years on Scale | The plan of this organisation is confirmed before the first run and recorded in section 11 |

The cross-check in #5547 and in the parent #5542 can therefore outlive the
artifacts. The plan does not rely on CircleCI retention for any evidence it
needs later.

| Step | Owner | Timing |
| --- | --- | --- |
| Every case writes its commands, exit statuses and observed values to files under `/tmp/meas`, which the job uploads with `store_artifacts` | the configuration | each run |
| Download the artifacts and keep the job URLs | the human, ID 3 | on the day of the run, and in any case before the artifact retention confirmed in section 11 expires. If that setting is not confirmed, the download happens on the day of the run and the stage does not continue until it is confirmed. No fixed number of days is assumed from the default |
| Draft `.circleci/MEASUREMENT_V2_3_0_M1.md` for #5544 and `.circleci/MEASUREMENT_V2_3_0_M2.md` for #5545, embedding the evidence that a later judgment needs, with the pipeline, workflow, job and commit identifiers | Claude, ID 11 | after the download |
| Review and commit those records to `main` | the human, ID 3 | before the branch is deleted |
| Record the commit SHA and the record file names in a journal entry on #5544 and #5545 | the human, ID 3 | after the commit |

The durable record is therefore the repository history on `main` plus the
Redmine journal, both of which have no expiry here. A CircleCI link is kept
as a pointer, never as the only copy. Nothing that the job prints is
treated as safe to copy without review: no API key, token, password,
session value, authorization credential or private key is written into an
artifact, a record file, a journal entry or this document, and if one
appears in a job log the value is not reproduced and the human is asked to
revoke or reissue it.

## 10. Boundaries this plan keeps

- The measurement is Phase 1 design investigation. It does not replace the
  Phase 4 or Phase 6 verification of a finished product, and a completed
  measurement is not a CI pass, an implementation or a publication.
- No case changes `src/`, the contract fixtures, the existing jobs, or any
  guarantee that the fixed four combinations already provide.
- The existing route keeps its API and default behaviour; no case requires
  `install` for a consumer that only calls `execute`.
- Adoption of D01-D08, the mandatory range, the formal Roadmap update and
  publication are separate decisions with separate approvals.

## 11. Approval record

The approval and the run start times are recorded separately, and they are
judged by different tickets. Run start times cannot be part of what #5543
needs, because #5544 may not start before #5543 is complete.

### 11.1 Approval, before any run. This is what #5543 C6 needs

Completed by the human before #5544 starts. #5543 C6 asks for the approval
itself and for the link between its object, plan version, scope, approver
and the approval time with its time zone. It does not ask for a run that
has not happened yet.

| Item | Value |
| --- | --- |
| Approved plan version: this file's commit on `main` | (SHA) |
| Approved scope | (H9 conditions of section 8, candidate list of section 3, cases of sections 5 and 6) |
| #5544: approved experiment commit on `exp/230-m1` | (SHA of the local commit, read before it is pushed) |
| #5544: approved configuration | SHA-256 `576cdc1a4d1c…`, full value in section 8 |
| #5545: approved experiment commit on `exp/230-m2` | (SHA of the local commit, read before it is pushed) |
| #5545: approved configuration | SHA-256 `aec39ba06b74…`, full value in section 8 |
| Confirmed artifact retention setting | (days, from Plan, Usage Controls) |
| Confirmed CircleCI plan and its pipeline-data retention | (value) |
| Approval to push `exp/230-m1` and run its pipeline | (approved / not approved) |
| Approval to push `exp/230-m2` and run its pipeline | (approved / not approved) |
| Approval of the experiment resource range of section 8 | (approved / not approved) |
| Approval to commit the measurement records to `main` | (approved / not approved) |
| Approver | (Redmine user ID) |
| Approval date and time, with time zone | (YYYY-MM-DD hh:mm JST) |

Both experiment commits can be created locally from `main` before anything
is pushed, because neither configuration depends on a measurement result.
The plan-version row and the experiment-commit rows hold different SHAs and
are never compared with each other. If #5544 leads to a revised #5545
configuration, a new #5545 commit row and configuration row, with their own
approval time, are added before #5545 starts.

Ticket registration is not an approval to run. A record without a time zone
is not an approval. #5543 C6 is met when this table is complete; #5544 and
#5545 do not start before then.

### 11.2 Runs, recorded afterwards by #5544 and #5545

Not part of #5543's completion. Each stage records its own row in its
measurement record, and the comparison with 11.1 belongs to #5542 C2,
#5544 C1 and #5545 C1: the start must be later than the approval time of
the plan version that run used, in one time zone.

| Stage | Plan version used | Experiment commit recorded by the job | Configuration hash recorded by the job | Hold approved at, with time zone | Run start, with time zone | Where recorded |
| --- | --- | --- | --- | --- | --- | --- |
| #5544 | (SHA) | (`exp/230-m1`, SHA) | (SHA-256) | (YYYY-MM-DD hh:mm JST) | (YYYY-MM-DD hh:mm JST) | `.circleci/MEASUREMENT_V2_3_0_M1.md` |
| #5545 | (SHA) | (`exp/230-m2`, SHA) | (SHA-256) | (YYYY-MM-DD hh:mm JST) | (YYYY-MM-DD hh:mm JST) | `.circleci/MEASUREMENT_V2_3_0_M2.md` |

The recorded experiment commit and configuration hash are compared with the
rows approved for the same stage in 11.1. The hold time and the run start
are both expected to be later than the 11.1 approval time.

A re-run after a plan revision gets its own row, its own approval reference
in 11.1, and its own configuration hash. An approval obtained after a run
started does not cover that run.

## 12. Open questions for the human

1. Whether the path of this document, `.circleci/MEASUREMENT_PLAN_V2_3_0.md`,
   is the intended location for the Phase 1 plan, and whether the two
   measurement records of section 9 belong beside it. The repository has no
   ADR directory at the baseline commit, and `.circleci/*.md` is where the
   release, consumer and integration documents live.
2. Whether E03 `ubuntu:22.04` is acceptable as mandatory candidate 1. It is
   chosen because a distribution Python there is expected to provide
   `python3` without `python` and without the marker, which is the
   combination the role needs; the expectation is verified by M-00.
3. Whether the staged consumer-side preparation of section 3 may be used
   for the measurement in E03, E04 and E05. This is a question about the
   measurement only. H3, how a candidate that needs OS packages is treated
   in the supported range, is decided after the measurement: the roadmap
   places its judgment at "Phase 1 の実測後", and #5544's readings of stage
   A and stage B are the material for it. Approving the preparation here
   does not decide H3, and H3 is not asked before the measurement.
4. Whether the carry-in limitation of M1-05, measured on E01 only, is an
   acceptable limit for D04 at this phase.
5. The artifact retention setting and the CircleCI plan, for section 9 and
   the two confirmation rows of section 11.1.

## 13. Revision history

| Revision | Change |
| --- | --- |
| First version, commit `d17c81c` on branch `5543` | Initial plan. |
| Second version, commit `f4dd82a` on branch `5543` | Five corrections after review, plus the H3 timing note. Section 11 was split so that the approval, which #5543 C6 needs, no longer waits for run start times, which #5544 and #5545 record; the approved configurations are now bound by content hash, and each job records the hash it ran. M2-06 gained a direct reading of the priority between a lint status and a save failure during writing, using the `RLIMIT_FSIZE` fault the repository already uses. Section 3 and M1-03 now stage the consumer-side preparation, so the need for the virtual-environment package is measured rather than installed in advance. M2-02 no longer reads the `BASH_ENV` content; survival is judged by re-hashing the remembered byte range. Section 9 no longer assumes the 30-day default and ties evacuation to the confirmed retention setting. Section 12 records that H3 is decided after the measurement. |
| This version | Two corrections after the second review. M1-03's stage B condition no longer relies on the interpreter being absent: `venv` places the interpreter before it bootstraps pip, so a creation that fails for lack of `ensurepip` still leaves `bin/python`. Stage B now follows from the creation status, the interpreter, and a pip check inside the environment, and the partial result is kept for M1-05. Section 8 and section 11 now separate the plan version from the experiment commit: the experiment commit is created locally, approved per stage by SHA together with its configuration hash, and only then pushed, and an approval hold in each measurement workflow keeps the start separate from the push. The #5544 job count in section 8.1 was corrected from 5 to 6. |

The earlier versions stay in the branch history. The corrections above change
how the cases are run and how the approval is recorded; they do not change
the candidate roles, the observation items, or the boundaries of section 10.
