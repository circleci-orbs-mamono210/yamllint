# Boolean runtime regression (#5504)

## Observed failure in published v2.1.0

Release/source commit: `b8b87391ceb1ce8fc746ea3f690e22c67011bfdd`.
Consumer branch: `verify/yamllint-v2.1.0`, commit
`11b6156a480bcecef515d155b0f9dfe8dcc56d86`.

- [Pipeline 135](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/135)
  (`5722efb3-8a29-4ec3-9720-b39cad4eef2d`), workflow
  `524e2489-526e-4e3d-94ab-947e2ebb92fd` failed.
- Minimal [job 1727](https://circleci.com/gh/circleci-orbs-mamono210/yamllint/1727)
  passed. Acceptance [1726](https://circleci.com/gh/circleci-orbs-mamono210/yamllint/1726)
  (1.37.1) and [1728](https://circleci.com/gh/circleci-orbs-mamono210/yamllint/1728)
  (1.38.0) failed at `hidden-warning`, after the first three cases passed.
  Subsequent cases did not run; their success must not be inferred.
- Both `last-observation.json` artifacts contain argv without `--no-warnings`,
  upstream status `0`, a visible line-length warning on stdout and empty stderr.
  The requested YAML boolean was `no_warnings: true`, with `strict: false`.
- Recorded runtime: configured `cimg/python:3.14`, actual Python `3.14.10`,
  pathspec `1.1.1`, PyYAML `6.0.3`, and the respective fixed yamllint version.

v2.1.0 publication itself succeeded in pipeline 134/publish job 1725.
Publication and consumer failure are separate facts. Neither the v2.1.0 tag
nor its registry artifact is changed by this fix.

## Inferred cause and controlled reproduction

The failed CI did **not** record the raw `PARAM_NO_WARNINGS` value. Therefore
`1` in that particular job is an inference, not a directly observed value.
CircleCI documents boolean environment representations as integers `1`/`0`:
[Reusing configuration](https://circleci.com/docs/reference/reusing-config/).
The old execute script accepted `true` only for `no_warnings`/`list_files`,
while its existing strict handling already accepted both textual and numeric
representations. The expanded command passed typed booleans directly.

Controlled local reproduction with real yamllint 1.37.1 and 1.38.0 confirmed
that the old conditions omit the requested flags for numeric `1`. Four cases
fail: hidden warning, hidden strict warning, visible error (argument mismatch),
and file listing. Textual values pass. The repaired conditions pass both
encodings. Local results are not evidence of the original CI's raw value or
of a new CircleCI run. The earlier local replay used textual conversion only
and consequently missed this runtime boundary.

## Repair and acceptance boundaries

Only the two enable conditions change. Public parameter definitions/defaults,
strict validation, configuration selection, literal target handling, refusals,
and upstream status propagation remain in place. Users continue to pass YAML
booleans, never numeric replacements in the public configuration.

All four required source-CI matrix jobs now execute typed Orb calls and record
raw allowlisted parameter values without modifying them. Child-process tests
explicitly model both encodings; old-condition controls must fail. Observer
fault controls detect missing flags, wrong status/output, and missing/duplicate
bodies. Config fault controls protect the complete sequence and publication
dependencies. See [INTEGRATION_TESTS.md](INTEGRATION_TESTS.md).

Release acceptance still requires the exact final RC's CI, tag-time RC011,
production publication, full packed/published equality and a separate registry
consumer run. A passing source test cannot fill those evidence fields.
#5493's v2.1.0 consumer failure remains historical; v2.1.1 results belong to
#5504. No child tickets are required for this implementation/release scope.
