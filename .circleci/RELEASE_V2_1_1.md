# v2.1.1 release procedure (#5504)

Target: `orbss/yamllint@2.1.1`, new tag `v2.1.1`.
This document is preparation, not publication or consumer acceptance evidence.
The [v2.1.0 failure](BOOLEAN_RUNTIME_FIX.md) remains recorded under #5493.
Do not overwrite v2.1.0, reuse its successful source CI as v2.1.1 evidence,
or treat later v2.1.1 success as a passing v2.1.0 consumer result.

## Final release candidate

1. Apply the reviewed files. All public parameters retain their types/defaults.
   Current README/example references must be exactly `orbss/yamllint@2.1.1`;
   explicitly historical references remain historical.
2. Replace CHANGELOG's `RELEASE_DATE` with the agreed intended date before
   committing, then compare it with the actual publication date later.
   Keep `2.1.1` -> `v2.1.0...v2.1.1`, `Unreleased` -> `v2.1.1...HEAD`, and
   all earlier release history. A date in a heading is not a publication time.
3. Fix the full RC SHA including final documentation. Run the existing setup
   and downstream pipelines on that exact revision. Retain all eleven original
   jobs and four matrix jobs, source/packed/expanded contract and fault-control
   artifacts, and all behavior/refusal/boolean-runtime results.
4. Each matrix job must complete the feature suites, omitted-parameter inline
   execution and ten observed typed Orb calls. Inspect raw parameter values,
   expected argv/status/output, identity and final job status together.
   `results.json` missing, incomplete or marked local is not CircleCI success.
5. Preserve success-only dependencies from every required test to downstream
   pack and production publish. Do not alter contexts or filters. Any change
   after the RC is fixed requires a new RC and affected verification.

## Publication through the existing release route

Immediately before publication, inspect both remote tag `v2.1.1` and Registry
version `orbss/yamllint@2.1.1`. A failed request is not evidence of absence.
If either already exists or cannot be established, inspect/resolve the state;
do not overwrite it or silently select another version.

With publication authorized and the RC verified, create/push only the new tag
on that SHA through the established workflow. The tag pipeline must run RC011
without a skip and pass all setup prerequisites, eleven original jobs, four
matrix jobs, downstream pack and production publish. RC011 checks the example
and tag majors only; review full version references/date/links separately.
Record the tag target, pipeline/workflow/job URLs and observed publication
UTC/JST timestamp. Retain the registry metadata.

## Full artifact comparison

From a clean checkout of the exact RC, pack `src` with CircleCI CLI 1.11.0.
Fetch the published `orbss/yamllint@2.1.1` source after publication is observed.
Compare local RC pack, tag-CI packed artifact and registry source. The package's
`tools/compare_orbs.py` compares every parsed YAML field including script
strings and examples, rejects duplicate keys, and records raw and canonical
SHA-256 hashes. Mapping order/comments/formatting may differ; scripts and
fields must not be removed or trimmed to conceal differences. Retain all
inputs and reports, including failures.

## Independent registry consumer

Use a fresh sibling worktree with branch `verify/yamllint-v2.1.1` starting at
the verified release SHA. The package's `tools/prepare_consumer.py` installs
the dedicated configuration and identical tested observer, then binds the
release SHA in both jobs. Review/commit/push that branch only; never merge
its configuration to main.

The config directly imports `orbss/yamllint@2.1.1`. It has no setup/continue,
inline source replacement, publish job or publishing Context, and executes no
checked-out `src/scripts`. Required jobs are the default minimal workflow and
fixed acceptance 1.37.1/1.38.0 on `cimg/python:3.14`. Each acceptance job runs
the eight required original cases plus omitted/explicit-false boolean controls.
The observer records real argv/status/output and raw allowlisted parameters;
it does not normalize the Orb's environment. Expected upstream nonzero status
is accepted only after exact assertions. Version display is not a body call.

Record consumer SHA/branch/config and observer hashes, release ancestry,
resolved runtime/dependencies, pipeline/job URLs, minimal result and all
acceptance observations. The observer's local mode is supplemental only.

Standalone `-`, configuration conflict and invalid strict refusals are traced
through pre-publication child-process CI, embedding/parameter checks and full
published equality. Do not label that chain as direct published refusal tests.

## Completion

Complete the package's `RELEASE_RECORD_TEMPLATE.json` with real evidence:
RC -> tag -> tag CI/RC011/tests/pack/publish -> registry equality -> consumer.
Keep failed or unexecuted outcomes explicit. The single-ticket/no-child policy
is fixed for #5504. Ticket updates, protected release fields and closure follow
their separately authorized operations; this file/package authorizes none.
#5493's handoff/closure requires its own decision and retains its failed
v2.1.0 consumer outcome. Do not mark its original consumer AC as passed.
