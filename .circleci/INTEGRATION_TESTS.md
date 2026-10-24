## v2.0.0 integration test coverage

This matrix tracks #5487 against the #5486 baseline commit
`9829e024c0d643550f0c4fb234da43d98af2acf7`.
Tests run against the source Orb injected by the setup workflow.

### Existing cases and their assertions

| Job | Purpose and input | Expected result | Change in #5487 |
| --- | --- | --- | --- |
| `command-tests` | Default executor; install and execute with no parameters after checkout | Install succeeds; the repository passes its `.yamllint` configuration | Preserved |
| `resource-class-test` | `yamllint/default` with `resource_class: medium`; default install and execute | Job runs with the requested executor configuration and lint succeeds | Preserved |
| `custom-image-test` | `yamllint/default` with `image: cimg/python:3.13` | Install and execute succeed in that image | Preserved |
| `install-command-test` | `cimg/python:3.14`; default install | `yamllint --version` succeeds | Preserved |
| `install-version-test` | Install `version: "1.37.1"` | Python package metadata equals `1.37.1` | Preserved |
| `negative-test` | `/tmp/yamllint-negative/invalid.yml`, containing a tab indentation error | yamllint exits `1` | Tightened from any nonzero status to exactly `1`; path and invalid input preserved |
| `targets-test` | `targets-test/valid/`, one explicit file, and two newline-separated files; invalid YAML remains outside the selected directory | Exactly the requested arguments reach yamllint; all three invocations succeed | Existing directory and multiple-file calls preserved; single-file case, argument checks, and invocation count added |
| `config-file-test` | Existing long line in `config-file-test/test.yml`; `config-file-test/yamllint-ci.yml` disables the line-length rule | Default configuration exits `1`; Orb execution with `config_file` succeeds | Default failure tightened to exactly `1`; custom-config assertion preserved |
| `strict-test` | Existing `strict-test/test.yml` and `strict-test/yamllint.yml`, with line-length warnings | `strict: false` succeeds; `strict: true` passes `--strict` and produces exactly `2` | Preserved |
| `format-test` | Existing `format-test/test.yml` and `format-test/yamllint.yml`; `format: parsable` | `--format parsable` is present; exit `0`; output has `path:line:column: [warning]` format | Preserved |

The executor cases above exercise the configured executor through CircleCI;
they do not claim to introspect its allocated resources from inside the job.
No existing job or fixture path is renamed. The seven jobs marked
"Preserved" are unchanged from the baseline.

### Target selection cases

`targets-test` retains these fixtures:

- `targets-test/valid/first.yml`
- `targets-test/valid/second.yml`
- `targets-test/invalid/invalid.yml`

The verifier compares the actual argument array with
`targets-test/expected-targets.txt` before calling the real yamllint executable.
This detects a dropped second target even when both valid files would pass.
It checks these three invocations in order:

1. One directory: `targets-test/valid/`.
2. One file: `targets-test/valid/first.yml`.
3. Two files: `first.yml` and `second.yml` supplied on separate parameter lines.

`targets-test/verified-calls.txt` must contain three successful invocations.
`targets-test/bin/yamllint` is a verifier, not a replacement linter: it delegates
to the installed executable and propagates any failure.

### New combined case

New job: `combined-parameters-test`.

| Item | Input or assertion |
| --- | --- |
| `targets` | `combined-test/selected/first.yml` and `combined-test/selected/second.yml`, separated by a newline |
| `config_file` | `combined-test/yamllint.yml`: line-length maximum 20, severity warning |
| `strict` | `true` |
| `format` | `parsable` |
| Unselected fixture | `combined-test/unselected/invalid.yml`: invalid tab indentation |
| Default-config control | Both selected files include a document marker and pass default configuration in strict mode with exit `0` |
| Invalid-fixture control | The unselected invalid file exits exactly `1` when explicitly linted |
| Argument assertion | All three options and exactly the two selected targets reach the real executable |
| Configuration assertion | The selected files, which pass the default configuration, emit line-length warnings with the supplied configuration |
| Exit assertion | The real executable returns exactly `2`, proving warning-only strict behavior |
| Output assertion | Both selected files have parsable line-length warnings; every output line belongs to one of those files and has that format |
| Invocation assertion | `combined-test/verified` is created only after all assertions succeed and must exist in the final step |

The verifier at `combined-test/bin/yamllint` forwards `--version` unchanged.
For the combined invocation it captures the real exit code, checks that it is
exactly `2`, validates the output, and only then returns success. Unexpected
statuses such as `0`, `1`, or `127` fail the test. Expected failures are never
unconditionally discarded with `|| true`.

All fixtures and verifier scripts are generated by the jobs in
`.circleci/test-deploy.yml`; they are not additional checked-in source files.

### CI evidence and release boundary

The workflow now invokes the existing ten jobs plus
`combined-parameters-test`. Record the commit SHA, pipeline URL, and each of
the eleven job results when this revision is run on CircleCI. Local replay of
shell steps is supplemental evidence, not proof of the Docker executors or a
successful CircleCI pipeline.

The #5486 inline-injection configuration, pack executors, publishing Context,
and release filters are preserved. #5488 adds success-only dependencies from
all eleven integration tests to the downstream `orb-tools/pack`, and from
that pack to `orb-tools/publish`. The setup pack remains a prerequisite for
inline injection; it does not wait for downstream tests.

### Release dependency checks (#5488)

The setup `orb-tools/continue` requires lint, setup pack, review, and
ShellCheck to succeed before injecting the source Orb and continuing.
Every setup job, integration test, and downstream pack accepts all tags.
Only production publish receives the `CIRCLECI_ORBS` Context.

| Pipeline input and prerequisite result | Downstream pack | Production publish |
| --- | --- | --- |
| Branch or PR; setup and all tests succeed | Runs | Excluded by branch filter |
| Non-release tag; setup and all tests succeed | Runs | Excluded by tag filter |
| Release tag; any setup prerequisite fails | Not reached through continue | Not reached |
| Release tag; any integration test fails or is canceled | Blocked | Blocked |
| Release tag; all tests succeed, downstream pack fails | Fails | Blocked |
| Release tag; setup, all tests, and downstream pack succeed | Succeeds | Eligible |

The release tag pattern remains `^v[0-9]+\.[0-9]+\.[0-9]+$`.
For example, `v2.0.0` matches, while `v2.0.0-rc.1` does not.
These are static configuration expectations, not evidence that failure or
release pipelines were executed. Actual publication also depends on the
existing Context permissions and CircleCI execution environment.

To finish #5488 verification, record the applied commit and the exact
configuration-expansion tool/version/command, retain source and fully
processed setup/downstream configurations, and compare their dependencies
and filters. Packing the Orb, injecting it, or resolving YAML anchors alone
is not a full CircleCI configuration expansion. If the processed view is
event-filtered, also retain a processed view that includes the release path;
a branch-only result without publish cannot verify that path.
Until this comparison is recorded, #5488 AC4 remains incomplete.
Do not create a release tag just to test these dependencies.
The v2.0.0 release remains a later task (#5490).

Reference for exit codes:
[yamllint configuration: errors and warnings](https://yamllint.readthedocs.io/en/stable/configuration.html#errors-and-warnings).
