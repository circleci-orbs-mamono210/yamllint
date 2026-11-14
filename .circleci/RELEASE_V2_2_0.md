# v2.2.0 release procedure (#5513)

Target: `orbss/yamllint@2.2.0`, new tag `v2.2.0` (parent #5507).
This document is preparation. It is neither publication evidence nor
consumer evidence. Publication and the full-content comparison are recorded
under #5513. The published-consumer verification, including the actual D08
job, is #5514 and follows [CONSUMER_V2_2_0.md](CONSUMER_V2_2_0.md). The
v2.1.1 release (#5504) and the v2.1.0 outcome (#5493) stay as recorded.

## 1. Release candidate

### Conditions before the RC is fixed

| Item | Condition at this point |
| --- | --- |
| #5506 (including its cross-verification), #5508, #5509, #5510, #5511 | Their required conditions hold technically |
| #5512 and D08 | The consumer template, the D08 judgment and its criteria are prepared and pre-verified. The published D08 job, its exit status and the artifact are #5514 |
| D09 option (a) | The pre-publication child-process suites and embedding checks pass, and the premise holds: the failure handling in `src/scripts/execute.sh` does not depend on terminal detection, `BASH_ENV`, CircleCI-specific environment or files outside the Orb; its output helper is embedded in the script. Published equality is the comparison in section 3 |

### Final documents

- README and every example refer to exactly `orbss/yamllint@2.2.0` for
  current usage. Historical references stay historical: the v1 migration
  example (`orbss/yamllint@1.1.5`) and statements such as "added in v2.1.0".
  Check with `grep -rn "orbss/yamllint@" README.md src/examples`.
- CHANGELOG: `## [2.2.0] - <date>` with the planned publication day in JST,
  `[2.2.0]` linked to `v2.1.1...v2.2.0`, `[Unreleased]` linked to
  `v2.2.0...HEAD`, and every earlier entry unchanged.
- If publication will not happen on that day, change the date before the RC
  is fixed. If publication moves to another day after the RC is fixed, the
  RC changes (step 5 below).

### Fix and verify the RC

1. The RC is the full SHA of the commit on `main` that contains these
   documents and the #5512 assets.
2. Run the existing pipelines on exactly that revision. Require success of:
   - setup workflow `lint-pack`: `orb-tools/lint`, `orb-tools/pack`,
     `orb-tools/review`, `shellcheck/check`, and `orb-tools/continue` with
     the contract check and its fault controls;
   - downstream workflow `test-deploy`: the eleven original jobs,
     `compatibility-matrix` (four jobs), `output-file-matrix` (four jobs) and
     `orb-tools/pack`. Production publish runs only for the tag.
3. Keep from that revision: the `phase5-config` artifacts (including
   `orb.yml`, the RC packed Orb used in section 3, `contract-result.json`,
   `contract-negative-controls.log` and `consumer-*.yml`), the four
   `compatibility/results.json`, and the `output-file-runtime` and
   `boolean-runtime` results.
4. #5512's checks at the RC revision: `test-consumer-template.py`
   (18 methods) passed in `compatibility-1.37.1-py3.14` and
   `compatibility-1.38.0-py3.14`, and the setup contract check verified the
   consumer configuration with the packed Orb inline.
   `test-compare-orbs.py` (11 methods) passed in all four compatibility jobs.
5. Any change after the RC is checked, including the CHANGELOG date, makes
   a new RC. Re-run the affected checks.

## 2. Publication

### Immediately before

- Remote tag: `git ls-remote --exit-code --tags origin refs/tags/v2.2.0`.
  Exit status `2` means that the remote has no such tag. Any other failure
  leaves the state unknown.
- Registry: check that the published versions of `orbss/yamllint` do not
  include 2.2.0 (registry page, or `circleci orb info`). A failed request, or
  a response that does not clearly show the version list, leaves the state
  unknown.
- A failed request is not evidence of absence. If the tag or the version
  exists, or its state is unknown, stop and report it. Do not overwrite
  anything and do not choose another version.

### Tag and publish (after explicit human approval)

- Create the new tag `v2.2.0` on the RC commit and push only that tag.
  v2.1.1 and v2.1.0 used lightweight tags. Do not force-push or recreate a
  tag.
- The tag pipeline must show `orb-tools/review` with RC011 executed and
  passed (not skipped), every setup job, the nineteen required downstream
  jobs, `orb-tools/pack` and `orb-tools/publish` (production) succeeded.
- RC011 compares only the example and tag majors. Full references, the
  CHANGELOG date and the links are reviewed separately (section 1).
- Record the tag target (`git rev-parse "v2.2.0^{commit}"`), the tag pipeline
  number and URL, the workflow and job URLs, and the observed publication
  time in UTC and JST, for example the registry's creation time of 2.2.0.

## 3. Full-content comparison

| Role | File | Where it comes from |
| --- | --- | --- |
| `rc` | `phase5-config/orb.yml` | `orb-tools/continue` job of the RC pipeline: the packed Orb that the RC CI verified |
| `tag-ci` | `phase5-config/orb.yml` | `orb-tools/continue` job of the tag pipeline |
| `published` | registry source | `circleci orb source orbss/yamllint@2.2.0`, or another read of the registry source; record which |

The downstream `orb-tools/pack` job that feeds production publish stores no
artifact. The registry source stands for its output.

Run the tool from a clean checkout of the RC (the tag) with Python 3 and
PyYAML. The report records the tool's SHA-256 and the Python and PyYAML
versions.

```bash
python .circleci/compare-orbs.py \
  --rc rc-orb.yml --tag-ci tag-orb.yml --published published-orb.yml \
  --source rc="phase5-config/orb.yml, RC pipeline <number>, job <URL>" \
  --source tag-ci="phase5-config/orb.yml, tag pipeline <number>, job <URL>" \
  --source published="circleci orb source orbss/yamllint@2.2.0 (CLI <version>)" \
  --rc-commit <RC SHA> --tag v2.2.0 --tag-commit <tag target SHA> \
  --tag-pipeline <tag pipeline URL> --published-at <observed time with offset> \
  --checked-by <name> --output compare-report-v2.2.0.json
```

`PASS` (exit status `0`) requires all of the following. Anything else is
`FAIL` (exit status `1`) with its reasons in the report.

| Condition | Rejected case |
| --- | --- |
| Each input is one YAML document with standard tags and unique keys | Unreadable file, invalid YAML, a second document, duplicate keys, custom tags |
| The three inputs match in full, including scripts, examples, parameters and defaults | Any changed, added, removed or reordered value, including whitespace and line endings |
| The tool is the version pinned in `compatibility-contract.json` and runs from a clean checkout of the RC | Edited tool, another commit, modified tracked files, no git checkout |
| The tag points to the RC commit, and the tag is `v2.2.0` | Another commit or tag |
| The CHANGELOG date of 2.2.0 equals the publication day in JST | Another day, or no 2.2.0 heading |
| Every field and every input source is recorded without credentials | Blank field, missing source, token-like text |

The comparison treats each file as a YAML representation. Mappings are
compared regardless of key order, sequences in order, and every scalar by its
resolved tag and exact text. Comments, indentation and quoting may differ;
nothing inside a value is trimmed or normalized. The report also records the
raw and canonical SHA-256 of each input and whether the raw bytes are
identical. The decision uses the full-content comparison. A CI success is
not used to infer equality.

Keep the report and all three inputs, including failed attempts. The tool
never replaces an existing report.

## 4. Records: planned and actual

| Item | Planned | Actual |
| --- | --- | --- |
| Orb version | 2.2.0 | Record after publication |
| Git tag | v2.2.0 | Tag target SHA |
| RC commit | Fixed in section 1 | Same SHA, with its pipeline |
| Publication time | The CHANGELOG date (JST) | Observed time, UTC and JST |
| Tag pipeline | Not applicable | Pipeline and job URLs, RC011 result |
| Full-content comparison | Not applicable | Report file, result and input hashes |

Planned values are not evidence. The comparison report ties the RC, tag, tag
pipeline, publication time and comparison result together. Updating the
Redmine fields `orb_version` and `release_tag` is a separate record operation
that needs its own approval. This document authorizes no tag, publication or
Redmine change.

## 5. After publication

#5514 verifies the published Orb with [CONSUMER_V2_2_0.md](CONSUMER_V2_2_0.md):
branch `verify/yamllint-v2.2.0` one commit after the release commit, the
generated configuration as the only change, the success-required jobs and the
D08 job confirmed in the CircleCI UI. If that verification fails, record the
successful publication (#5513) and the failed verification separately. Never
overwrite the published version, recreate the tag or roll back automatically.
