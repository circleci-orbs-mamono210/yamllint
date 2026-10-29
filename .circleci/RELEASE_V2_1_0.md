# v2.1.0 release procedure (#5493)

Target: `orbss/yamllint@2.1.0`, tag `v2.1.0`.
This procedure and versioned release notes are preparation, not publication
evidence. Keep publication and consumer verification as separate outcomes.

## Fix the release candidate

1. Confirm the required outcomes of #5491, #5494, #5495, #5496, #5492 and #5497.
2. Confirm every current README/example reference is exactly `2.1.0` (the
   README's explicitly historical v1 migration example remains historical).
3. Replace the explicit `RELEASE_DATE` placeholder in CHANGELOG with the
   agreed intended release day before committing. Verify it against the
   actual publication date later; do not invent a publication timestamp.
4. Keep `2.1.0` linked to `v2.0.0...v2.1.0` and `Unreleased` linked to
   `v2.1.0...HEAD`. Preserve the previous release history.
5. Fix the exact RC commit including these final documents and validate it.
   Any subsequent change requires the affected checks again. Retain the
   `phase5-config/`, four `compatibility/`, and eleven runtime artifacts
   together with all job results from that revision.

Use the existing setup and downstream pipelines. All required feature,
refusal, compatibility and configuration checks must pass before downstream
pack and production publish. Do not change the Context or release filters.

## Tag and publish

Check both the remote tag and the registry immediately before publishing.
The absence of a Git tag is not evidence that the registry version is absent.
A failed CLI request is also not evidence of absence. If the version exists,
or its state is unknown, stop and inspect it; do not overwrite or silently
choose another version.

With an explicitly approved publication and verified RC, create the new tag
on that commit and push only that tag using the existing release pipeline.
Do not force-update/recreate an existing tag or run an alternate publish path.

The tag pipeline must show RC011 **executed and passed**, not skipped. In
orb-tools 12.5.0, RC011 compares example/tag majors only; independently check
all full references, CHANGELOG date and links. A green branch review does not
prove tag-time RC011. Confirm all upstream checks, tests, pack and production
publish, with the tag pointing to the validated RC.

## Compare the published artifact

Using CircleCI CLI 1.11.0, pack `src` from a clean checkout of the exact RC.
Fetch `circleci orb source orbss/yamllint@2.1.0` only after publication has
been observed. Compare the full documents, including examples and executable
script strings. Record raw hashes and any formatting-only normalization;
do not delete fields or trim scripts to make a mismatch disappear.
Retain the packed and published files and comparison result.

## Independent consumer verification

Create a dedicated `verify/yamllint-v2.1.0` branch from the release commit.
Its `.circleci/config.yml` directly imports `orbss/yamllint@2.1.0` and uses
no setup, continue, inline injection, publish or publishing Context. It must
not execute checkout's `src/scripts` as a substitute for the published Orb.
Do not merge this consumer-only configuration into main.

Required representative coverage: default checkout/install/execute,
effective `config_file` and `config_data`, warning suppression with strict
off/on, selected file listing, and ordinary/hyphen-leading/literal `./-`
paths. Capture expected upstream nonzero results with real yamllint, exact
status and required output checks; an unexecuted body must fail verification.
Any new observer/shim must have its own failure-detection controls.

Standalone `-` and simultaneous settings refusals are not required direct
published-consumer executions. Trace them through RC pre-publication CI,
packed/expanded script and parameter comparisons, and published equality.
Do not describe this chain as a direct published refusal execution.

## Completion record

Record RC commit, tag/target, tag pipeline, non-skipped RC011, all test/pack/
publish results, pre-publication refusal artifacts, packed/expanded checks,
published source/hash comparison, actual publication time with timezone,
consumer commit/config/job links and runtime/results. A published version
with a failing consumer test is published but not fully verified; retain both
facts and do not automatically roll it back.

Confirm the #5493 child-ticket scope separately before AC8. Release custom
fields and ticket closure use their own approved recording operations; this
procedure does not authorize Redmine writes. Preparation or source-only tests
do not satisfy the release-completion criteria.
