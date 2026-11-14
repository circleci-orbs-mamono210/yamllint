# v2.2.0 published-consumer verification: template, judgment and record (#5512)

Target: the published `orbss/yamllint@2.2.0`, verified on branch
`verify/yamllint-v2.2.0` by #5514. This document and the files it names are
preparation. They are not a run of the published Orb and not release
evidence. The split between pre-publication and post-publication checks is
owned by the roadmap (`220_ロードマップ` version 2, Phases 2 and 4).

## Files

| File | Role |
| --- | --- |
| `consumer/config.template.yml` | The only source of the consumer `.circleci/config.yml` |
| `prepare-consumer.py` | `generate`, `verify-checkout`, structure checks, and the pre-publication `inline` helper |
| `verify-boolean-parameters.py` | Existing boolean observer; consumer branch and Orb now v2.2.0 |
| `verify-output-file.py` | #5510 step observer; now also accepts the consumer scope |
| `verify-consumer-d08.py` | D08: `prepare`, in-job `check`, outside `judge` |
| `consumer/d08-record.template.json` | Form for the D08 UI record |
| `test-consumer-template.py` | Fault controls for all of the above (18 methods) |

All of them are pinned in `compatibility-contract.json`. The final release
candidate (#5513) therefore fixes their content together with the Orb.

## Creating the consumer commit

1. Start branch `verify/yamllint-v2.2.0` at the release commit.
2. `python .circleci/prepare-consumer.py generate --release-commit <release SHA> --output .circleci/config.yml`
3. Commit that single file. Do not edit it, add other changes or a second
   commit, and never merge the branch to main.

The only difference from the template is the release commit in four
`RELEASE_COMMIT` lines. Every job runs `verify-checkout` and stops unless the
branch is the dedicated one, the commit is exactly one commit after the
release commit, only `.circleci/config.yml` differs, and that file equals the
release commit's template with the placeholder replaced. If an expectation,
fixture or judgment must change after publication, do not patch the consumer
branch: re-evaluate the affected pre-publication checks and the mapping to
the published artifact first.

The configuration imports the registry Orb directly. It contains no
setup/continue, inline Orb, publish job or Context. Checked-out `.circleci`
scripts only observe and judge; no checked-out `src/` script is executed.

## Jobs and what each one establishes

Workflow `consumer-acceptance`: every job must succeed.

| Job | Runtime | Evidence kind |
| --- | --- | --- |
| `minimal` | Default executor, default install | Minimal README workflow; job status and `minimal/minimal.json` |
| `boolean-acceptance-1.37.1`, `-1.38.0` | `cimg/python:3.14`, fixed yamllint | Boolean delivery and upstream results (ten cases) |
| `output-file-acceptance-1.37.1`, `-1.38.0` | `cimg/python:3.14`, fixed yamllint | Saved content and connections of real `output_file` steps (ten cases) |

Workflow `d08-failed-step-artifact`: job `d08-failed-lint-artifact`
(yamllint 1.38.0, `cimg/python:3.14`) is expected to fail. It is not part of
the success-required source CI and is recorded separately.

Keep the two acceptance evidences apart:

- **Boolean observation** (`boolean-runtime/results.json`). The observer
  captures yamllint's output through a pipe as text and returns `0` after
  its checks. It shows typed boolean delivery and upstream's results,
  including strict warning (`2`), error (`1`) and silent strict warning
  (`2`). It is not evidence of byte equality, of the terminal state, or of
  an Orb step that exits non-zero.
- **Saved-content observation** (`output-file-runtime/results.json`). This
  is the #5510 method, unchanged: no pipe or pseudo-terminal is added, the
  recorder at the body position runs the real yamllint with the inherited
  connections and returns its real exit status, and every body must exit `0`.

### Saved-content cases and their checks

The typed parameters are identical to the source job `output-file-tests`;
the structure check compares the two step lists.

| Required representative case | Case(s) in `output-file-acceptance-*` | Expected result |
| --- | --- | --- |
| Saving disabled | `saving-omitted`, `saving-empty` | yamllint keeps the step's stdout; no entry is created |
| Normal warning, not strict | `absolute-parsable` | One warning line saved |
| Success without output | `relative-strict-clean`, `config-file` | 0-byte file |
| `no_warnings` | `hidden-warning` | 0-byte file |
| `config_file` | `config-file` | Saved with a configuration file |
| `config_data` | every case except `config-file` | Supplied configuration is effective |
| `list_files` | `list-files` | The listing is saved |
| Additional | `auto-format`, `colored-format`, `long-literal-path` | Non-terminal format; colors kept; literal path and more than 64 KiB |

For each case, `results.json` ties together the typed parameters, raw
`PARAM_*` values, argv, the body's real exit status (`0`), the step's
stdout/stderr and yamllint's stdout/stderr (terminal or not, type, identity),
and the saved file's size and SHA-256. The final step requires:

- saving disabled: yamllint's stdout is the step's stdout;
- saving enabled: yamllint's stdout is a non-terminal connection different
  from the step's stdout, and exactly one new regular file exists;
- yamllint's stderr is the step's stderr in both modes;
- the saved bytes equal a separate reference run of the same yamllint with a
  pipe as stdout, whose stderr is empty;
- no temporary `.yamllint-orb-output-*` file remains.

Limits, as in #5510: the bytes that reach the CircleCI log are not captured,
and streaming, save/forwarding failures and destination refusals are not
executed against the published Orb. Under D09 option (a) they are traced
through the pre-publication child-process suites, the embedding checks and
equality of the published Orb to the verified packed Orb (#5513).

## D08: artifact after a failed real step

The job calls `yamllint/execute` once:

| Parameter | Value |
| --- | --- |
| `targets` | `d08-fixtures/error.yml` (written by the prepare step: `---\nmessage: lint error  \n`) |
| `config_data` | `extends: default` |
| `format` | `parsable` |
| `output_file` | `/tmp/yamllint-d08-results/lint.txt` |

Expected: the body step exits `1`, and the file contains exactly

```text
d08-fixtures/error.yml:2:20: [error] trailing spaces (trailing-spaces)
```

Nothing stands before the yamllint body and nothing converts its status.

### Identifying the body step in the UI

- The job has exactly one step named `Execute yamllint`, directly after
  `Show yamllint version`. The setup contract check confirms this on the
  compiled configuration before publication.
- In the CircleCI UI, confirm that this step failed and that its exit status
  is `1`. A failure of the version display, the preparation or any other
  step is not a substitute.
- Confirm the failure reason: copy the whole output the UI shows for this
  step, without CircleCI's closing line that reports the exit code. With
  `output_file`, the Orb forwards yamllint's output to the step log, so the
  output must be exactly the lint error line above. Another message, an
  additional line (for example an Orb `output_file` error) or a blank value
  is not a pass.
- If the name does not identify the step uniquely, compare the command shown
  in the UI with the compiled configuration and the packed Orb script.
  Storing the command text is not required.
- If the UI does not show the exit status, the output or the step mapping,
  record `unconfirmed`. A red job alone is not a pass. The CircleCI API is
  not used.

### Steps the UI shows

Record the result of every step the UI shows for the job. The expected list,
in order, is:

| # | Step in the UI | Origin |
| --- | --- | --- |
| 1 | `Spin up environment` | CircleCI |
| 2 | `Preparing environment variables` | CircleCI |
| 3 | `Checkout code` | `checkout` |
| 4 | `Install yamllint` | `yamllint/install` |
| 5 | `Verify consumer checkout` | `verify-consumer-checkout` |
| 6 | `Prepare D08 fixture and result directory` | `run` |
| 7 | `Show yamllint version` | `yamllint/execute` |
| 8 | `Execute yamllint` | `yamllint/execute` (the body; must fail) |
| 9 | `Check D08 result file` | `run`, `when: always` |
| 10 | `Uploading artifacts` | `store_artifacts` (result file) |
| 11 | `Uploading artifacts` | `store_artifacts` (check evidence) |

Every step except `Execute yamllint` must succeed. The names of CircleCI's
own steps are those shown for the Docker jobs of this repository's CI. The
setup contract check derives rows 3 to 11 from the compiled configuration
and compares them with this list. If the UI shows a different list, record
it as shown; the judgment then fails.

### In-job check (`Check D08 result file`, `when: always`)

It judges only the result file: the fixture is unchanged, the file exists,
is a regular file, has exactly the expected bytes, and nothing else is in
the result directory. It writes `yamllint-d08-evidence/d08-check.json`. A
step cannot read the previous step's exit status, so this check says nothing
about whether `Execute yamllint` failed. `when: always` only makes it run.

### Outside judgment

Download `yamllint-d08-results/lint.txt` and
`yamllint-d08-evidence/d08-check.json` from the job's Artifacts tab, fill a
copy of `consumer/d08-record.template.json` from the UI, then run:

```bash
python .circleci/verify-consumer-d08.py judge \
  --record <record.json> --artifact <lint.txt> --check-evidence <d08-check.json>
```

`PASS` (exit `0`) requires all of the following. Anything else is `FAIL` or
`UNCONFIRMED` (exit `1`).

| Condition | Rejected case |
| --- | --- |
| `Execute yamllint` is the failed step, with exit status `1` | Execute succeeded; another exit status; status not confirmed |
| The failure reason recorded from the UI is exactly the expected lint error output | Another reason; additional output; blank or not confirmed |
| Every step the UI shows is recorded once, in the order above, with its status | A step left out (for example an artifact upload), an extra or reordered step; a status not confirmed |
| Every step other than `Execute yamllint` succeeded | A different or additional failed step |
| The in-job check step succeeded and its evidence is `PASS` | File missing or different in the job |
| The retrieved artifact equals the expected bytes | Different content; artifact not retrieved |
| Evidence fixture hash, typed parameters, yamllint 1.38.0, Python 3.14, job name, commit, release commit and job URL match the record | Another fixture, runtime or job |
| The job is failed in CircleCI | A green job |
| Method is the CircleCI UI; confirmer and time are recorded | Missing record fields |

A `PASS` covers D08 only. The CircleCI job and its workflow stay failed.

### Record form

`consumer/d08-record.template.json` holds the job URL, consumer and release
commits, confirmer, time, method, job status, the body step (name, preceding
step, how it was identified, status, exit status, failure reason), the
eleven steps above with their status, the in-job check result and how the
artifact was retrieved. A blank value counts as not confirmed. Record no
credential, request header, API response or step output URL; the judgment
rejects a record that contains such fields.

## What was verified before publication

- `test-consumer-template.py` runs in both Python 3.14 compatibility jobs:
  generation changes only the release commit; the structure check rejects
  forbidden changes; an observer that still names the v2.1.1 branch or Orb
  is rejected; the checkout check accepts only "release commit + generated
  configuration"; the D08 file check and judgment reject a missing file,
  different content, a successful execute, a failure in another step, another
  exit status and results that could not be obtained. The judgment also
  rejects a failure reason other than the expected lint error output, a
  blank failure reason, and a record that leaves out, adds or reorders a
  step, for example one that keeps only the six named run steps. The D08 Orb
  step in these controls is emulated with the checked-out script; that is a
  control of the judgment, not D08 evidence.
- The setup contract check generates the configuration with the current
  revision as a provisional release commit, replaces the registry reference
  by the packed Orb, compiles it with the official CLI and checks the job
  set, images, versions, delivered parameters, the absence of forbidden
  mechanisms, the uniqueness and position of `Execute yamllint`, and that the
  D08 steps the UI will show match the step list of the record. That
  replacement is recorded for this structure check only and does not count
  as direct execution of the published Orb. `test-ci-contract.py` holds the
  matching fault controls.

Results of these checks belong to the revision that ran them. Publication
(#5513) and the consumer run (#5514) are separate records.
