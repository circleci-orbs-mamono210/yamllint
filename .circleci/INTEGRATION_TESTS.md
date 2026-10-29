## Phase 5 integration and release gates (#5492)

The configuration adds four mandatory `compatibility-tests` instances while
keeping all eleven existing job bodies unchanged. The table describes the
configured coverage; only results from the applied revision's CircleCI run
establish CI success. Local runs and configuration expansion are supplementary.

| Job | Explicit install.version | Executor image | Role |
| --- | --- | --- | --- |
| `compatibility-1.37.1-py3.13` | 1.37.1 | cimg/python:3.13 | Older upstream: existing and added behavior |
| `compatibility-1.37.1-py3.14` | 1.37.1 | cimg/python:3.14 | Existing README fixed-version example on the default executor |
| `compatibility-1.38.0-py3.13` | 1.38.0 | cimg/python:3.13 | Compare upstream versions with Python held constant |
| `compatibility-1.38.0-py3.14` | 1.38.0 | cimg/python:3.14 | New upstream on the default executor |

Each job runs the real-upstream Phase 2/3/4 suites and the Phase 5 combinations,
then runs the actual inline `yamllint/execute` command with all parameters
omitted. `run-compatibility.py` checks the installed yamllint version, Python
minor version and checkout commit. Missing dependencies, failed suites or
incomplete/skipped test summaries fail the job.

### Assignment of all eleven verification scopes

`V+P` means both upstream and Python may affect behavior: all four pairs run
the case. `Neither` means source/argument structure independent of those
versions: one check on the exact revision is sufficient. Successful install
alone never substitutes for behavior verification.

| Scope | Dependency / allocation | Evidence and rationale |
| --- | --- | --- |
| Existing parameters and minimum configuration | V+P / four pairs; resource configuration once | Actual inline default execute; config/strict/format tests; existing eleven jobs below |
| Target/option boundary | V+P / four pairs; pure argv checks once | Real literal and multiple-target cases in list-files/combinations; Phase 1 recorder suite once |
| Standalone `-` refusal | Neither / once normal; four listing runs retained with Phase 4 | Phase 1 child-process refusal; Phase 4 listing refusal; exact code, Orb stderr and no body call |
| config_data effect and conflict | V+P / four pairs | Phase 2 real configuration controls and normal refusal; Phase 4 listing refusal and settings selection |
| no_warnings with strict/format | V+P / four pairs | Phase 3 statuses plus Phase 5 standard/parsable, strict on/off, hidden/visible warnings |
| list_files and configured selection | V+P / four pairs | Phase 4 discovery/file/data and simple exclusions |
| list_files with no_warnings | V+P / four pairs | Phase 5 both booleans, both strict values, standard/parsable, config file/data |
| New parameters omitted | V+P / four pairs | Actual default inline command and Phase 5 existing config_file/strict/format cases with all new variables absent |
| New and existing parameter combinations | V+P / four pairs | Phase 5 two literal targets, file/data, strict, format and warning display; Phase 4 list options |
| Version-specific file selection | V+P / four pairs | Phase 4 fixed expectations for each upstream version, separated from common patterns |
| Script embedding and parameter delivery | Neither / once before continue | Source/packed/official compiler output and compile-only parameter probes, including true/false and multiline data |

### Existing eleven purposes and fixed-version counterparts

| Existing job (unchanged body) | Fixed-version counterpart or independent configuration check |
| --- | --- |
| command-tests | Install followed by actual inline execute with all defaults, in every pair |
| resource-class-test | Existing medium allocation job retained once; expanded medium and default small declarations checked |
| custom-image-test | Both upstream versions on Python 3.13, with full behavior suites |
| install-command-test | Actual install command and resolved package version checked in every pair |
| install-version-test | Existing 1.37.1 install check retained; both fixed versions also have full behavior suites |
| negative-test | Phase 4 normal-lint invalid YAML control, separate from listing, in every pair |
| targets-test | Phase 4 literal/directory targets and Phase 5 multiple targets; Phase 1 shim unchanged |
| config-file-test | Phase 2 real default/config-file controls and Phase 5 file configuration |
| strict-test | Phase 3 strict warning status and Phase 5 visible/hidden warning combinations |
| format-test | Phase 3 parsable results and Phase 5 standard/parsable combinations |
| combined-parameters-test | Phase 5 two warning files with file/data, strict and parsable output; original selection controls and shim retained |

The pure Phase 1 suite runs in `compatibility-1.38.0-py3.14` only. The canonical
JSON hashes in `compatibility-contract.json` bind all eleven job bodies and
four inherited suites to the feature-owned revisions. Both #5491 CI shims and
their fault controls are unchanged. Their rerun is integrated regression,
not a new independent acceptance decision for the same negative cases.
`test-combinations.py` reuses the unchanged Phase 4 real-upstream recorder;
no new yamllint success-conversion shim is introduced.

### Checked continuation and publication boundary

After lint, setup pack, review and ShellCheck succeed, the continue job uses
`cimg/python:3.14`, checks its curl/jq/yq prerequisites, and installs the
checksum-pinned CircleCI CLI 1.11.0 for configuration processing.
`prepare-ci-contract.sh` extracts the setup pack's `orb.yml`, injects it into
the checked-out downstream source, and compiles the setup, downstream and
parameter-probe configurations with the official CLI.

`check-ci-contract.py` compares the actual source environment definitions,
packed scripts/API, expanded executable scripts, parameter values, fixed
versions/images, inherited jobs and success-only release dependencies.
`test-ci-contract.py` deliberately corrupts these observations to verify the
checker detects missing matrix jobs/dependencies, changed scripts/mappings,
failed-status acceptance, widened publish filters, misplaced Context and an
unverified continuation path. These controls do not simulate CI failure pipelines.

The verified `/tmp/yamllint-phase5/injected.yml` is passed directly to
orb-tools/continue. Its checkout, workspace attach and reinjection options
are disabled because the pre-steps already supplied the checked input.
The Orb remains inline source from the same revision, with no development
publish or registry fallback. Parameter probes are compiled only and never
continued; invalid probe inputs do not create intentionally failing CI jobs.

Downstream pack requires all eleven original jobs and the complete four-job
`compatibility-matrix` alias. Expanded config must name all fifteen success
dependencies. Production publish requires that pack, keeps the existing
release-tag/branch filters, and alone receives `CIRCLECI_ORBS`.
No release tag or publication is performed by these checks.

### Evidence and completion procedure

| Location in CircleCI artifacts | Contents / interpretation |
| --- | --- |
| Continue job: `phase5-config/` | Exact packed/injected/expanded/setup/probe YAML, CLI version, dependency tools, identity, comparison report and fault-control log |
| Each compatibility job: `compatibility/` | Actual yamllint/Python/packages, configured image, checkout SHA, source hashes, CI job/workflow references and full suite logs |
| Each original job: `runtime/runtime.json` | Resolved versions/packages, image, case and CI references; default installs are distinct from install-version-test |

Image tags are the required `cimg/python:3.13` and `3.14`; record their actual
Python patch and dependencies at runtime, not an assumed patch version.
The configured image is not represented as an observed immutable digest.
Runtime metadata alone is not a test-success claim: inspect the matching
job's final status, including the inline execute step after the suites.
Only an allowlist of CI identifiers is recorded; credentials and complete
process environments are never exported. Workspaces are workflow-scoped:
the setup artifact and downstream artifacts are correlated by the checkout
SHA and pipeline/job links, not by assuming a shared workspace across continue.

For #5492 AC1/2/4/7/9, retain a successful CircleCI run of the applied revision
covering every listed case and artifact. For AC3/5/6, retain the matching
comparison and failure-control artifacts as well. Pass that same revision,
scope table and CI evidence to #5497 and #5493. A later source/config change
requires the affected checks to run again. This does not establish publication
or published-Orb acceptance.

The #5492 child-ticket table is still a placeholder in the retrieved ticket
and no children were returned. This implementation does not settle that
administrative scope or mark AC8 complete; confirm the child list separately
before deciding to close #5492.

For supplemental local runs, install each required yamllint version and run:

```bash
python .circleci/run-compatibility.py --version 1.37.1 --python-version 3.13 --local --evidence-dir /tmp/yamllint-local
```

`--local` explicitly records that the configured cimg image was not executed.
It does not satisfy CircleCI acceptance, even when the host Python matches.

## Phase 4 file-listing checks (#5496)

`execute.list_files` is a boolean with a `false` default. Only `true` adds
`--list-files` before the target boundary. The existing `Execute yamllint`
step writes the upstream listing directly to stdout; the separate version
step is unchanged. No artifact or structured report is created by the Orb.
The same target parsing and configuration selection apply in both modes.

Run the suite once with each of yamllint 1.37.1 and 1.38.0 installed:

```bash
python3 .circleci/test-list-files.py -v
```

The suite requires Python 3.8+, Bash, PyYAML and real yamllint in the running
Python environment. Missing dependencies or unsupported yamllint versions
fail the suite. It prints the Python, yamllint, PyYAML and pathspec versions;
dependency installation and the fixed CI environment belong to #5492.

| Acceptance criterion | Verification in `test-list-files.py` |
| --- | --- |
| AC1: configured selection and exclusion | Directory with `yaml-files` and simple `ignore`; compare stdout, stderr, status and exact argv against the same installed upstream |
| AC2: listing does not lint; false preserves lint | Instrument real `linter.run` to fail if called; listing succeeds, a normal-lint control triggers the guard; unset/false retain normal valid/invalid YAML results |
| AC3: common validation and settings | Discovery, file-only and data-only selection; child executions with standalone `-` or both settings require status 2, Orb stderr, empty stdout and zero body calls |
| AC4: strict and format | Both strict values and all five valid upstream formats preserve the listing; invalid format and invalid settings preserve the same installed upstream's rejection |
| AC5: upstream pattern semantics | Simple common cases are separate from the fixed per-version negative-pattern cases below; no Orb-side correction |
| AC6: no independent file checks | Source only adds a CLI option; the real-linter guard and nonexistent/invalid fixtures corroborate absence of an Orb existence, readability or YAML-validity gate |
| AC7: listing success is not lint success | Nonexistent path and invalid YAML each appear in a successful listing but fail normal lint in separate calls |

The pattern fixture contains `fixtures/keep.yml`, `drop.yml`, `skip.yml`,
`extra.yaml`, `note.txt` and `sub/keep.yml` (all under `fixtures/`).
The following are fixed expected memberships, not fixed output ordering:

| Configuration | yamllint 1.37.1 | yamllint 1.38.0 |
| --- | --- | --- |
| Common: `yaml-files: ['*.yml']`, `ignore: ['fixtures/skip.yml']` | keep.yml, drop.yml, sub/keep.yml | Same |
| Negative `yaml-files: ['*.yml', '!drop.yml']`, no ignore | keep.yml, skip.yml, sub/keep.yml | Same, asserted separately |
| `yaml-files: ['*.yml', '*.yaml']`, `ignore: ['!keep.yml', 'fixtures/']` | Empty | keep.yml, sub/keep.yml |
| `yaml-files: ['*.yml', '*.yaml']`, `ignore: ['*.yml', '!fixtures/']` | keep.yml, drop.yml, skip.yml, extra.yaml, sub/keep.yml | extra.yaml |

Each listing is also compared byte-for-byte with a direct invocation of the
same installed version on the same fixture. The suite records dependency
versions; the table does not promise identical behavior for arbitrary future
dependencies. The Orb neither sorts nor deduplicates the upstream output.
Explicit paths, option-like names, spaces, literal shell text, duplicate
targets, `./-` and empty-target fallback are checked against upstream too.

The recording shim logs each argument array and calls the real upstream CLI
in the child process, preserving its actual exit status and output without
converting failures to success. The parent asserts exactly one body call and
the full observed result. Both refusal tests invoke the actual source script
as a subprocess and require zero body calls; the separate version step is
not part of that count. Executed mutations independently break each refusal
condition and prove the guard rejects unexpected success, a wrong code,
missing/misdirected diagnostics and a body call. Additional executed mutants
prove detection of no invocation, a missing listing flag, wrong status,
extra stdout/stderr and a dropped target.

Listing success is not proof of existence, readability, YAML validity or lint
success. Upstream argument and configuration validation still runs, and its
errors are propagated. Valid `strict`, `format` and `no_warnings` do not
change listing results; the `no_warnings` integration is owned by #5492.
These are source/local checks. #5492 owns the fixed cimg/python compatibility
matrix, mandatory CI wiring, packed/expanded execution and release dependencies;
handoff must identify the exact integrated revision and rerun these cases.
#5497 owns the full user documentation and #5493 owns publication.

## Phase 3 warning-display checks (#5495)

`execute.no_warnings` is a boolean with a `false` default. Only `true` adds
`--no-warnings` before the target boundary. It changes warning display, not
rule severity or exit-code handling. Warning-only input returns `0` without
strict mode and `2` with strict mode, even when warnings are hidden. Errors
remain visible and return `1` with either strict value.

Run the feature checks from the repository root:

```bash
python3 .circleci/test-no-warnings.py -v
```

The suite requires Python 3.8+, Bash, PyYAML and actual yamllint in the running
Python environment. Missing dependencies fail the suite. It prints the
installed yamllint and Python versions and does not install dependencies.

| Acceptance criterion | Verification in `test-no-warnings.py` |
| --- | --- |
| AC1: warning-only, no strict | Assert empty warning output and status `0` independently |
| AC2: warning-only, strict | Assert empty warning output and status `2` independently |
| AC3: error present | Use a fixture with both a warning and a trailing-spaces error; check error visibility, warning suppression and status `1` for both strict values |
| AC4: unset or false | Require unchanged argv, stdout, stderr and status against the same installed upstream without `--no-warnings`; compare unset and false results |

The verification shim calls real yamllint, captures its actual arguments,
status, stdout and stderr, and only returns success if all values exactly
match the expected observation. That expectation is first checked against
the required status and warning/error output conditions. A completion marker
and exactly-one-call check prevent an unexecuted command from passing.
Each acceptance case is also run through the upstream CLI entry point without
the verifier's success conversion, checking the Orb's real exit status.

Negative controls demonstrate detection of unexpected success, wrong status,
missing or extra output, changed arguments and no invocation. The suite also
checks source parameter wiring, `config_data`, and multiple selected targets.
These local checks do not establish a CircleCI run or a published-Orb result.
#5492 owns the fixed cimg/python compatibility matrix, CI integration,
`strict`/`format` and `list_files` integration, and publication dependencies.
#5497 owns the complete user documentation; #5493 owns publication.

## Phase 2 configuration-data checks (#5494)

`execute.config_data` is a string with an empty default. Empty values omit
`--config-data`; non-empty values are passed as one unchanged argument.
Both settings empty preserve discovery, and `config_file` alone preserves
file selection. Setting both to non-empty values returns status `2` with
`yamllint Orb: config_file and config_data cannot both be non-empty.` on
stderr, before the lint body is called. The version-display step is separate.

Run from the repository root in a Python environment with yamllint installed:

```bash
python3 .circleci/test-config-data.py -v
python3 .circleci/test-target-boundaries.py -v
```

The new suite requires Python 3.8+, Bash, PyYAML and actual yamllint in the
same Python environment. Missing yamllint fails the suite; dependencies are
not installed automatically. The Phase 1 suite additionally needs Bash 4+
for the existing CI shims, so macOS users should select that Bash on `PATH`.

| Acceptance criterion | Verification in `test-config-data.py` |
| --- | --- |
| AC1: one literal argument and effective configuration | Exact argv for multiline quoted YAML; real default-failure/config-success control |
| AC2: empty means omitted; non-empty is not normalized | Empty and unset cases; whitespace, newline, tab and other literal values |
| AC3: discovery and config-file behavior | Real local `.yamllint` discovery and explicit file overriding discovery |
| AC4: pre-execution conflict refusal | Child execution of the actual script; parent asserts status 2, Orb stderr and zero body calls |
| AC5: upstream owns interpretation and exit results | Same installed version invoked directly and through the script; compare status, stdout and stderr for malformed YAML, unknown rules, `relaxed`, whitespace and scalar inputs |
| AC6: refusal verifier detects faults | Execute five temporary mutants: success, wrong status, absent diagnostic, stdout-only diagnostic, and body invocation |
| AC7: no shell reevaluation | Exact argv and absence of side-effect files for shell metacharacters, including a real upstream case |

The suite also checks source parameter wiring and strict/parsable warning
behavior. Real-upstream output includes the installed version and Python
version. Assertions compare against the same installed upstream instead of
fixing its full diagnostics across versions. Invalid syntax and an unknown
rule must fail; arbitrary non-empty strings need only retain upstream behavior.

Configuration conflict validation is common input validation, before option
construction and the body call. #5496 owns list-files wiring and its refusal
checks. #5492 owns the mandatory CI integration, fixed release matrix,
packed-Orb/expanded-config comparisons, and publication dependencies.
These local checks do not establish a CircleCI run, the cimg/python matrix,
or verification of a published Orb. #5497 owns the complete user documentation.

## Phase 1 target-boundary checks (#5491)

The source change adds `--` between the Orb options and literal target paths.
The `targets-test` verifier now requires `--` as its first argument, then
checks the exact target count and values. The `combined-parameters-test`
verifier requires the boundary after the options and treats every remaining
argument as a target. Both forward the original arguments to real yamllint.
The existing invocation-count and completion-marker checks are retained.

Run the supplemental regression suite from the repository root:

```bash
python3 .circleci/test-target-boundaries.py -v
```

It requires Python 3.8 or newer, PyYAML, and Bash 4 or newer on `PATH`.
The existing CI shims use Bash `mapfile`; the macOS system Bash 3.2 is not
sufficient to replay those shims. The suite does not install dependencies.

The suite runs `src/scripts/execute.sh` in child processes and records exact
arguments using a controlled yamllint executable. It covers literal paths,
empty-line handling, the `.` fallback, option-like names, shell metacharacters,
exit-status propagation, and standalone `-` rejection. Rejection requires all
three conditions: status `2`, the Orb diagnostic on stderr, and no lint body
invocation. Fault-injected child scripts demonstrate that a wrong status,
missing diagnostic, or body invocation fails that assertion.

The suite also extracts and exercises the two verifier scripts and their
invocation guards directly from `.circleci/test-deploy.yml`. It checks valid
calls, missing or misplaced boundaries, missing or additional targets, changed
target values, and calls that never ran. It preserves the separate `--version`
path. These are local assertions using controlled executables; they do not
establish that CircleCI or real yamllint passed.

Actual yamllint probes must separately record the version, Python version,
tested source, inputs, status and output. Phase 5 (#5492) owns adding the new
rejection checks to the mandatory CI and publication dependencies. Phase 4
(#5496) owns connecting and testing list-files mode. Neither is implemented
by this Phase 1 change. The historical v2.0.0 coverage record follows.

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

The #5486 inline source-testing model, pack executors, publishing Context,
and release filters are preserved. #5488 established the eleven-job gate;
Phase 5 above adds the four compatibility jobs and verifies the exact inline
continuation input. Downstream pack still gates production publish. Setup
pack remains a prerequisite for injection and does not wait for downstream tests.

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

For release dependency verification, record the applied commit and the exact
configuration-expansion tool/version/command, retain source and fully
processed setup/downstream configurations, and compare their dependencies
and filters. Packing the Orb, injecting it, or resolving YAML anchors alone
is not a full CircleCI configuration expansion. If the processed view is
event-filtered, also retain a processed view that includes the release path;
a branch-only result without publish cannot verify that path.
Do not create a release tag just to test these dependencies.
For v2.1.0, the Phase 5 artifacts above provide this comparison; actual CI
completion and release outcomes remain separate records in #5492 and #5493.

Reference for exit codes:
[yamllint configuration: errors and warnings](https://yamllint.readthedocs.io/en/stable/configuration.html#errors-and-warnings).
