[![CircleCI Build Status](https://circleci.com/gh/circleci-orbs-mamono210/yamllint.svg?style=shield "CircleCI Build Status")](https://circleci.com/gh/circleci-orbs-mamono210/yamllint) [![CircleCI Orb Version](https://badges.circleci.com/orbs/orbss/yamllint.svg)](https://circleci.com/orbs/registry/orb/orbss/yamllint) [![GitHub License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://raw.githubusercontent.com/circleci-orbs-mamono210/yamllint/main/LICENSE)

# yamllint Orb

CircleCI Orb for running yamllint.

This documentation targets **orbss/yamllint@2.2.0**. Releases up to 2.1.1 do
not have `output_file`. Development verification uses the packed source Orb
injected inline. Registry availability (#5513) and independent consumer
verification (#5514) are tracked separately; a source test result alone does
not establish either outcome.

## Usage

The following minimal configuration uses `orbss/yamllint@2.2.0`.
The referenced release must be available in the Orb Registry.

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.2.0

jobs:
  lint:
    executor: yamllint/default
    steps:
      - checkout
      - yamllint/install
      - yamllint/execute

workflows:
  lint:
    jobs:
      - lint
```

## Migrating from v1 to v2

For v2.2.0, update the Orb reference to `orbss/yamllint@2.2.0`, and rename the
`yamllint/execute` parameter `config-file` to `config_file` in every
invocation. There is no compatibility alias for `config-file` in v2;
a configuration that still passes the old name must be updated before
it can use v2.

The following examples assume `.yamllint-ci` already exists in your repository.

### Before: v1

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@1.1.5

jobs:
  lint:
    executor: yamllint/default
    steps:
      - checkout
      - yamllint/install
      - yamllint/execute:
          targets: .circleci/
          config-file: .yamllint-ci
          strict: true
          format: parsable

workflows:
  lint:
    jobs:
      - lint
```

### After: v2.2.0

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.2.0

jobs:
  lint:
    executor: yamllint/default
    steps:
      - checkout
      - yamllint/install
      - yamllint/execute:
          targets: .circleci/
          config_file: .yamllint-ci
          strict: true
          format: parsable

workflows:
  lint:
    jobs:
      - lint
```

The existing parameter names, types and defaults are retained in v2.2.0.
Target interpretation has the specific migration changes described below.
The complete `execute` API is:

| Parameter | Type | Default | Behavior in v2.2.0 |
| --- | --- | --- | --- |
| `targets` | string | `.` | Literal file/directory paths, one per line; applies to lint and listing |
| `config_file` (v1: `config-file`) | string | `""` | Configuration path; mutually exclusive with non-empty `config_data` |
| `config_data` | string | `""` | YAML configuration or upstream configuration name; empty means unspecified |
| `strict` | boolean | `false` | Enable strict mode so warnings produce a non-zero exit status |
| `no_warnings` | boolean | `false` | Hide warning output without changing the exit status |
| `list_files` | boolean | `false` | Print upstream-selected paths without linting |
| `format` | string | `""` | Pass an output format to yamllint; an empty value keeps its default format |
| `output_file` | string | `""` | Added in v2.2.0. Save yamllint's stdout to a new file at this path; an empty value disables saving |

`format` remains a string parameter, not an Orb enum. Format values are
interpreted by the installed yamllint version. The underlying yamllint CLI
option remains `--config-file`; only the Orb parameter name changes.

The minimum `checkout` → `yamllint/install` → `yamllint/execute` configuration
shown in Usage is unchanged. Ordinary file/directory configurations with the
new parameters omitted continue to work. When migrating, also check for the
target-interpretation changes below. The `install.version` parameter,
executor image and resource-class options, and custom image requirements are
also unchanged; their details are documented below.

## Migrating from v2.0 to v2.1

Each non-empty `targets` line is passed literally after the CLI option
terminator `--`. A value such as `--version` is now a **path**, not an option.
Move options out of `targets` and use the corresponding Orb parameters.
Paths containing spaces, quotes or wildcard characters are not split,
glob-expanded or evaluated as shell code. Empty lines are ignored; if no
targets remain, the Orb uses `.`. Whitespace-only lines are literal paths,
not empty lines.

A target line exactly equal to `-` is rejected before the lint/listing body
with exit status `2` and an Orb diagnostic. Previously it could reach
yamllint's stdin mode. Use `./-` for a file named `-`; stdin is not an Orb
interface. These changes were adopted for v2.1.0 in #5491; they are behavior
changes for callers that relied on stdin or options inside `targets`.
Ordinary file/directory use and existing parameter defaults are preserved.

```yaml
steps:
  - yamllint/execute:
      targets: |
        -example.yml
        ./-
```

Both files must be present for normal lint. See the self-contained
[target-path example](src/examples/target_paths.yml) and [CHANGELOG](CHANGELOG.md).

## Migrating from v2.1 to v2.2

No change is required. v2.2.0 adds one optional `execute` parameter,
`output_file` (string, default `""`). While it is omitted or empty, the Orb
checks no destination, creates no file and does not relay stdout: yamllint
keeps the step's stdout, and the output, exit statuses and refusals described
for v2.1 are unchanged.

Saving has its own requirements and failure rules. Read
[Save the output to a file](#save-the-output-to-a-file) before setting
`output_file`.

## Executor

The default executor uses:

```text
cimg/python:3.14
```

A custom Docker image can be specified with the `image` parameter.
`image` is a string; its default is `cimg/python:3.14`.

```yaml
executor:
  name: yamllint/default
  image: cimg/python:3.13
```

### Resource class

The `resource_class` parameter can be used to configure the CircleCI resource
class for the default executor.

```yaml
executor:
  name: yamllint/default
  resource_class: medium
```

The default value of `resource_class` is `small`.
This parameter remains an enum.

The following values are currently supported:

- `small`
- `medium`
- `medium+`
- `large`

The `image` and `resource_class` parameters can be used together.

```yaml
executor:
  name: yamllint/default
  image: cimg/python:3.13
  resource_class: medium
```

### Custom image requirements

The selected image must provide the runtime environment required by the Orb.

At minimum, a custom image must provide:

- Bash
- a `python` command
- pip available through `python -m pip`
- a Python environment that allows packages to be installed with pip

The Orb is primarily intended to be used with CircleCI convenience images such
as `cimg/python`.

Images that provide only `python3`, do not include Bash, or prevent package
installation with `python -m pip` may require additional setup before using
this Orb.

## Install yamllint

Use the `install` command to install yamllint.

```yaml
steps:
  - yamllint/install
```

By default, the latest available version of yamllint is installed using:

```bash
python -m pip install yamllint
```

### Install a specific version

Use the `version` parameter to install a specific version of yamllint.
It is a string with default `""`; an empty value keeps the default install.

```yaml
steps:
  - yamllint/install:
      version: "1.37.1"
```

This is equivalent to:

```bash
python -m pip install "yamllint==1.37.1"
```

This README's `1.37.1` example on the default `cimg/python:3.14` executor
is one of the four [verified combinations](#verified-compatibility).
The Orb version (`2.2.0`) and installed yamllint version (`1.37.1`) are
different version choices. A default install may resolve to a newer upstream
version; it is not a fixed-version compatibility guarantee.

## Execute yamllint

Use the `execute` command to run yamllint against the checked out repository.

```yaml
steps:
  - checkout
  - yamllint/install
  - yamllint/execute
```

By default, the `execute` command runs yamllint against the current directory.

```bash
yamllint -- .
```

### Specify a target

The `targets` parameter can be used to lint a specific file or directory.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
```

### Specify multiple targets

Multiple targets can be specified using one target per line.

```yaml
steps:
  - yamllint/execute:
      targets: |
        .circleci/
        src/
```

The default value of `targets` is `.`.

### Specify a configuration file

The `config_file` parameter can be used to explicitly specify a yamllint
configuration file.

```yaml
steps:
  - yamllint/execute:
      config_file: .yamllint-ci
```

The `config_file` parameter can be combined with `targets`.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
      config_file: .yamllint-ci
```

Configuration selection is shared by normal lint and `list_files`:

| `config_file` | `config_data` | Result |
| --- | --- | --- |
| Empty | Empty | Normal upstream configuration discovery |
| Non-empty | Empty | Use the specified file |
| Empty | Non-empty | Pass the supplied configuration string to upstream |
| Non-empty | Non-empty | Orb refusal: status `2`, stderr diagnostic, no lint/listing body call |

### Specify configuration data

`config_data: ""` means unspecified: the Orb omits `--config-data` entirely.
Non-empty values, including whitespace, newlines and quotes, are passed
unchanged as **one argument**. The Orb does not trim them, merge settings,
repair invalid YAML or fall back to defaults when upstream rejects them.
yamllint owns configuration parsing, rule validation and named configurations
such as `relaxed`.

```yaml
steps:
  - yamllint/execute:
      targets: src/
      config_data: |
        extends: relaxed
        rules:
          line-length:
            max: 200
```

A named upstream configuration can also be passed directly:

```yaml
steps:
  - yamllint/execute:
      config_data: relaxed
```

Leave `config_file` empty when using either form. See the complete
[configuration-data example](src/examples/config_data.yml).

### Enable strict mode

Set `strict` to `true` to enable yamllint strict mode.

```yaml
steps:
  - yamllint/execute:
      strict: true
```

When strict mode is enabled, warnings cause yamllint to return a non-zero
exit status.

The default value of `strict` is `false`.

The `strict` parameter can be combined with `targets` and `config_file`.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
      config_file: .yamllint-ci
      strict: true
```

### Specify an output format

The `format` parameter is a string, with an empty string as its default.
It can be used to specify the yamllint output format.

```yaml
steps:
  - yamllint/execute:
      format: parsable
```

If `format` is not specified, yamllint uses its default output format.

The `format` parameter can be combined with the other `execute` parameters.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
      config_file: .yamllint-ci
      strict: true
      format: parsable
```

### Hide warnings without changing the result

`no_warnings: true` suppresses warning output. It does not disable rules,
change severity, turn off strict mode or convert a failure to success.
Omitted or `false` keeps the existing output and exit behavior.

```yaml
steps:
  - yamllint/execute:
      no_warnings: true
      strict: true
      format: parsable
```

| Detected result | `strict` | `no_warnings` | Output and exit status |
| --- | --- | --- | --- |
| Warnings only | `false` | `true` | Warnings hidden; `0` |
| Warnings only | `true` | `true` | Warnings hidden; `2` |
| Errors present | Either | `true` | Errors visible; `1` |

A silent step can therefore fail with status `2`. See the complete
[warning-display example](src/examples/no_warnings.yml).

### List selected files without linting

```yaml
steps:
  - yamllint/execute:
      targets: src/
      config_data: |
        extends: relaxed
        yaml-files: ['*.yml', '*.yaml']
      list_files: true
```

The execution step writes upstream's selected paths to stdout. The separate
version-display step still runs. `targets`, configuration discovery,
`config_file`/`config_data`, exclusions and both Orb refusal rules apply.

With `output_file` omitted or empty, the Orb creates no file. With
`output_file` set, the listing written to stdout is also saved to that file;
see [Save the output to a file](#save-the-output-to-a-file). A saved listing
is not proof of lint success, and it is not a structured report defined by
the Orb. Uploading it as an artifact is done by your own `store_artifacts`
step, not by the Orb.

Successful listing does **not** establish that a path exists, can be read,
contains valid YAML or passes lint. For example, upstream can list an
explicit nonexistent path or invalid YAML without linting it. Run normal
`execute` separately to assess lint results. The Orb adds no file checks,
sorting or deduplication guarantees beyond upstream.

Valid `strict`, `no_warnings` and `format` values do not change listing
results. Validation still applies: an invalid `format` or configuration can
fail upstream, and an invalid `strict` value is not accepted by the Orb.
`list_files: false` or omission keeps normal lint behavior.

File selection follows the installed yamllint version. The `yaml-files` and
`ignore` pattern handling differs between 1.37.1 and 1.38.0, including some
negative-pattern combinations. The Orb does not normalize those differences.
See the version-specific fixtures in
[INTEGRATION_TESTS.md](.circleci/INTEGRATION_TESTS.md#phase-4-file-listing-checks-5496)
and the complete [listing example](src/examples/list_files.yml).

### Save the output to a file

`output_file` (string, default `""`) is added in v2.2.0. When it is set,
yamllint's stdout is still written to the step's stdout, and the same bytes
are saved to a new file at that path. When it is omitted or empty, nothing
in the sections above changes.

```yaml
steps:
  - checkout
  - run:
      name: Prepare yamllint result directory
      command: mkdir -p /tmp/yamllint-results
  - yamllint/install:
      version: "1.38.0"
  - yamllint/execute:
      targets: .
      format: parsable
      output_file: /tmp/yamllint-results/lint.txt
  - store_artifacts:
      path: /tmp/yamllint-results
      destination: yamllint-results
```

This lints the checkout and saves the output to a new file outside it. See
the complete [output-file example](src/examples/output_file.yml).

#### What the file contains

- Only the stdout of the yamllint lint/listing call. The Orb adds no header,
  version, timestamp or success message, and does not reformat the output.
- stderr is not saved; it stays on the step's stderr. The output of the
  separate version-display step is not saved either.
- With `list_files: true`, the file contains the listing. A listing does not
  establish lint success.
- If yamllint prints nothing and saving succeeds, a 0-byte file is created.
- If yamllint exits non-zero, for example `1` for lint errors, its output is
  still saved and that exit status is returned.

**The file is a list of diagnostics, not a result.** An empty file can
belong to a failed step: `no_warnings: true` with `strict: true` exits `2`
without output, and an error that yamllint reports only on stderr, such as
an invalid configuration, leaves the file empty. Neither the existence of
the file nor an empty file means that lint passed. Judge success by the
step's exit status and the CI result.

#### Where the file can be saved

The Orb checks the destination before yamllint starts. If a rule below is
not met, the step exits `2` with a diagnostic on stderr that starts with
`yamllint Orb: output_file:`. yamllint is not run and nothing is created.

- **The path is literal.** `~`, environment variables, globs and shell
  expressions are not expanded, and leading or trailing whitespace is not
  removed. `~/reports/lint.txt` and `$HOME/reports/lint.txt` do **not** point
  to the home directory; they name directories literally called `~` and
  `$HOME` below the working directory. Write the real path, such as
  `/tmp/yamllint-results/lint.txt`. A relative path starts from the step's
  working directory. A path containing a newline or carriage return is
  refused.
- **The parent directory must already exist.** The Orb does not create it.
- **Only a new file is written.** An existing regular file, directory,
  symbolic link (including a broken one) or special file is never replaced
  or appended to. If an entry with the same name appears while yamllint is
  running, it is left unchanged and the step exits `2` (or yamllint's own
  non-zero status).
- **The file must be outside every target directory**, and must differ from
  every target file and from `config_file`. Paths are compared after
  resolving symbolic links and forms such as `..`. With `targets: .`, which
  is the default, the file must therefore be outside the working directory.
  `ignore` settings and file extensions do not relax this rule.
- **`python3` must be on `PATH`** when saving. It is not needed while
  `output_file` is empty.

A path cannot be reused. A second `execute` call with the same `output_file`
in one job is refused, and so is a re-run on a machine that keeps files
between runs, such as a self-hosted runner. Use a different new path for each
call, or delete beforehand only those old results whose content and ownership
you have checked. The Orb never deletes old files, and `mkdir -p` in the
example above does not remove an old `lint.txt`.

#### Output format while saving

- Saving disabled: the Orb does not relay stdout. yamllint writes directly
  to the step's stdout, as in v2.1.
- Saving enabled: yamllint's stdout is connected to a pipe, never to a
  terminal, and the Orb creates no pseudo-terminal. Output is forwarded to
  the step's stdout as it arrives; yamllint's own buffering is not changed.
- An explicit `format` is passed to yamllint unchanged. With
  `format: colored`, the color control characters appear in the log and in
  the file; the Orb does not remove them.
- With `format` empty or `auto`, yamllint chooses the format itself from its
  environment, including whether its stdout is a terminal. Because stdout is
  not a terminal while saving, automatic colors and layout can differ from a
  run without `output_file`. Set an explicit value such as `format: parsable`
  when the saved format must be stable.

#### Exit status while saving

| yamllint | Saving and log forwarding | Step exit status |
| --- | --- | --- |
| Not started: an existing Orb input refusal | Not started | `2`; no file |
| Not started: destination refused or not preparable | Not started | `2`; no file |
| Exits `0` | Both succeed | `0` |
| Exits non-zero | Both succeed | yamllint's status; the output is saved |
| Exits `0` | Saving or forwarding fails | `2` |
| Exits non-zero | Saving or forwarding fails | yamllint's status; the failure is also reported on stderr |

Saving problems are reported on stderr with the `yamllint Orb: output_file:`
prefix. When saving fails, no partial file is left at `output_file`. When
only forwarding to the step log fails and the complete output was saved, the
file is kept, and the step still fails as shown above. If yamllint cannot be
started at all, no result file is created.

#### Upload the file as an artifact

The Orb only creates the file inside the job. Uploading is done by the
`store_artifacts` step in your configuration; the Orb does not upload or
share files and does not change their retention.

CircleCI's regular `store_artifacts` step also runs after an earlier step
has failed (see the
[configuration reference](https://circleci.com/docs/reference/configuration-reference/#the-when-attribute)).
In the configuration above, `lint.txt` is therefore uploaded when yamllint
finds errors and the `execute` step exits `1`. The job is still failed: a
successful upload is not a successful lint.

A canceled or timed-out job has no such guarantee, and v2.2.0 does not
guarantee a complete file or upload in that case. Adding an upload in a
`teardown` step does not add a guarantee from the Orb. While yamllint runs,
the Orb keeps a temporary file named `.yamllint-orb-output-<random>.tmp` in
the same directory and removes it when the step ends normally; a forcibly
stopped step can leave it behind. Uploading the whole directory can then
include that unfinished file. Only the file at `output_file` is a completed
output. Set `path` to that file if nothing else should be uploaded.

### Interpret failures with the diagnostics

Orb input refusals return `2` before the lint/listing body:

- A target line exactly equal to `-`.
- Both `config_file` and `config_data` non-empty.
- An invalid `strict` value reaching the execution script (diagnostic:
  `Invalid strict value: ...`). The public parameter is boolean; CircleCI
  can reject an invalid parameter type before the script runs.

The first two diagnostics start with `yamllint Orb:`. The separate command
step that displays `yamllint --version` is outside the body-not-invoked
guarantee and may already have run.

With `output_file` set (v2.2.0), the execution step also returns `2`, with a
diagnostic on stderr that starts with `yamllint Orb: output_file:`, when:

- The destination is refused or cannot be prepared. yamllint is not run.
  These checks run after the three refusals above.
- yamllint exits `0`, but saving the file or forwarding its stdout to the
  step log fails.

Status `2` is also used by upstream for strict warnings and argument errors
such as an invalid `format`. **An exit code alone does not uniquely identify
the cause.** Inspect the diagnostic, inputs and execution context.

With `output_file` omitted or empty, the Orb propagates upstream's exit
status without an independent remapping. With `output_file` set, a non-zero
upstream status is still returned unchanged; only an upstream `0` becomes `2`
when saving or log forwarding fails. See
[Exit status while saving](#exit-status-while-saving).

## Verified compatibility

The historical Phase 5 source-Orb CI at
[commit 9bdc52b](https://github.com/circleci-orbs-mamono210/yamllint/commit/9bdc52b627986e18a6da4ba02c8a621387f554e1)
ran source checks for these four pairs:

| yamllint | Configured image | Coverage role |
| --- | --- | --- |
| 1.37.1 | `cimg/python:3.13` | Older upstream: existing and added features |
| 1.37.1 | `cimg/python:3.14` | This README's fixed-version example on the default executor |
| 1.38.0 | `cimg/python:3.13` | Version comparison with Python held constant |
| 1.38.0 | `cimg/python:3.14` | Newer upstream on the default executor |

The historical run used explicit `install.version`, real feature/combination
checks, and the inline command with all new parameters omitted. It missed
boolean runtime encoding: the published v2.1.0 consumer later failed
`hidden-warning` in pipeline 135. See the
[failure analysis](.circleci/BOOLEAN_RUNTIME_FIX.md).

For v2.1.1, every pair additionally executes ten observed inline Orb calls
with typed boolean parameters, retaining raw values and exact upstream
arguments/status/output. Local tests cover textual and numeric encodings,
old-code failure controls and observer faults. These are configured checks;
new CircleCI results for the final RC are still required. Existing eleven jobs
are retained and mapped to fixed-version coverage; they are not each run four
times. The [coverage and CI evidence](.circleci/INTEGRATION_TESTS.md) record
actual Python patch/dependency versions, cases and job links. This scope does
not guarantee all OS/Python versions or untested upstream/dependency releases.

Before publication, CI checks Orb refusals in **both normal and listing
modes** by executing the source script in child processes: status `2`, Orb
stderr and no body call must all match. The same revision's packed Orb and
expanded configuration separately establish script embedding and parameter
delivery. All required tests gate downstream pack and production publish.

After publication, #5504 must use the registry Orb directly in an independent
consumer configuration for the minimum workflow, `config_file`, effective
`config_data`, `no_warnings` with `strict`, listing, and accepted ordinary or
hyphen-leading paths. Direct execution of the two refusal paths in the
published Orb is outside that mandatory scope. Their evidence is traced via
pre-publication CI, embedding/delivery checks and equality of the published
Orb to the verified packed Orb; it is not a claim of direct consumer refusal
testing. The source CI result above does not establish publication or
post-publication acceptance.

### v2.2.0 output-file checks

For the v2.2.0 preparation, the source-Orb CI at
[commit 239092a](https://github.com/circleci-orbs-mamono210/yamllint/commit/239092af05f6879212162c3b19a9752b01bb540d)
ran the following for each of the four pairs above:

- Child-process suites that run the real execution script: saving, exit
  statuses, destination refusals, streaming and injected save/forwarding
  failures (20, 13 and 8 test methods), plus 23 fault-control methods for the
  step observer.
- Ten real `yamllint/execute` steps with typed parameters: two with saving
  disabled and eight with `output_file`. Every body exited `0`, and each
  saved file equals, byte for byte, a separate reference run of the same
  yamllint.

In those jobs the step's stdout was a terminal and, while saving, yamllint's
stdout was a non-terminal pipe. This is a record of those runs, not a
guarantee for other environments. The bytes delivered to the CircleCI log
were not captured; equality of the forwarded stdout and the saved file,
streaming, non-zero statuses and the failure paths are established by the
child-process suites. All of these jobs gate downstream pack and production
publish. Job links and the scope table are in
[INTEGRATION_TESTS.md](.circleci/INTEGRATION_TESTS.md#phase-1-and-2-output-file-checks-for-v220).

These are pre-publication source results. They are not results of the
published `orbss/yamllint@2.2.0`. After publication, #5514 is to use the
registry Orb directly in an independent consumer configuration: the success
cases, and one intentionally failing job (a lint error, exit status `1`) to
confirm that the file can be retrieved as an artifact after the failed step.
The new destination refusals and the save/forwarding failures are not
executed directly against the published Orb; they are traced through the
pre-publication checks, the embedding/delivery checks and equality of the
published Orb to the verified packed Orb.

## Release documentation

The [CHANGELOG](CHANGELOG.md) separates `2.2.0` from subsequent Unreleased
changes. Its comparisons are `v2.1.1...v2.2.0` for `2.2.0` and
`v2.2.0...HEAD` for `Unreleased`. The release candidate must include the
final date and documentation before validation. Publication and the
full-content comparison of the published Orb (#5513), and independent
consumer results (#5514), remain separate release evidence; a version heading
is not proof of publication. Follow the
[v2.2.0 release procedure](.circleci/RELEASE_V2_2_0.md). Earlier releases keep
their own records: v2.1.1 under #5504
([procedure](.circleci/RELEASE_V2_1_1.md)), and the v2.1.0 publication and
its failed consumer result under #5493.

orb-tools v12.5.0 **RC011 checks only the bundled examples' Orb major against
the release tag major**. It does not check this README or full `2.2.0`
equality. README, every example and CHANGELOG need a separate full-version
review; a branch-time RC011 skip is not a successful release-tag check.
