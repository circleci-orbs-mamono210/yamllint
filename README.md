[![CircleCI Build Status](https://circleci.com/gh/circleci-orbs-mamono210/yamllint.svg?style=shield "CircleCI Build Status")](https://circleci.com/gh/circleci-orbs-mamono210/yamllint) [![CircleCI Orb Version](https://badges.circleci.com/orbs/orbss/yamllint.svg)](https://circleci.com/orbs/registry/orb/orbss/yamllint) [![GitHub License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://raw.githubusercontent.com/circleci-orbs-mamono210/yamllint/main/LICENSE)

# yamllint Orb

CircleCI Orb for running yamllint.

This documentation targets **orbss/yamllint@2.1.0**. Development verification
uses the packed source Orb injected inline. Registry availability and
independent consumer verification are tracked separately in #5493; a source
test result alone does not establish either outcome.

## Usage

The following minimal configuration uses `orbss/yamllint@2.1.0`.
The referenced release must be available in the Orb Registry.

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.1.0

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

For v2.1.0, update the Orb reference to `orbss/yamllint@2.1.0`, and rename the
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

### After: v2.1.0

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.1.0

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

The existing parameter names, types and defaults are retained in v2.1.0.
Target interpretation has the specific migration changes described below.
The complete `execute` API is:

| Parameter | Type | Default | Behavior in v2.1.0 |
| --- | --- | --- | --- |
| `targets` | string | `.` | Literal file/directory paths, one per line; applies to lint and listing |
| `config_file` (v1: `config-file`) | string | `""` | Configuration path; mutually exclusive with non-empty `config_data` |
| `config_data` | string | `""` | YAML configuration or upstream configuration name; empty means unspecified |
| `strict` | boolean | `false` | Enable strict mode so warnings produce a non-zero exit status |
| `no_warnings` | boolean | `false` | Hide warning output without changing the exit status |
| `list_files` | boolean | `false` | Print upstream-selected paths without linting |
| `format` | string | `""` | Pass an output format to yamllint; an empty value keeps its default format |

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
The Orb version (`2.1.0`) and installed yamllint version (`1.37.1`) are
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
No artifact or structured report is created by the Orb.

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

Status `2` is also used by upstream for strict warnings and argument errors
such as an invalid `format`. **An exit code alone does not uniquely identify
the cause.** Inspect the diagnostic, inputs and execution context. The Orb
propagates upstream's exit status without an independent remapping.

## Verified compatibility

The Phase 5 source-Orb CI at
[commit 9bdc52b](https://github.com/circleci-orbs-mamono210/yamllint/commit/9bdc52b627986e18a6da4ba02c8a621387f554e1)
verified these four pairs:

| yamllint | Configured image | Coverage role |
| --- | --- | --- |
| 1.37.1 | `cimg/python:3.13` | Older upstream: existing and added features |
| 1.37.1 | `cimg/python:3.14` | This README's fixed-version example on the default executor |
| 1.38.0 | `cimg/python:3.13` | Version comparison with Python held constant |
| 1.38.0 | `cimg/python:3.14` | Newer upstream on the default executor |

Each pair uses explicit `install.version`, real feature/combination checks,
and the inline command with all new parameters omitted. Existing eleven jobs
are retained and mapped to fixed-version coverage; they are not each run four
times. The [coverage and CI evidence](.circleci/INTEGRATION_TESTS.md) record
actual Python patch/dependency versions, cases and job links. This scope does
not guarantee all OS/Python versions or untested upstream/dependency releases.

Before publication, CI checks Orb refusals in **both normal and listing
modes** by executing the source script in child processes: status `2`, Orb
stderr and no body call must all match. The same revision's packed Orb and
expanded configuration separately establish script embedding and parameter
delivery. All required tests gate downstream pack and production publish.

After publication, #5493 must use the registry Orb directly in an independent
consumer configuration for the minimum workflow, `config_file`, effective
`config_data`, `no_warnings` with `strict`, listing, and accepted ordinary or
hyphen-leading paths. Direct execution of the two refusal paths in the
published Orb is outside that mandatory scope. Their evidence is traced via
pre-publication CI, embedding/delivery checks and equality of the published
Orb to the verified packed Orb; it is not a claim of direct consumer refusal
testing. The source CI result above does not establish publication or
post-publication acceptance.

## Release documentation

The [CHANGELOG](CHANGELOG.md) separates `2.1.0` from subsequent Unreleased
changes. Its comparisons are `v2.0.0...v2.1.0` for `2.1.0` and
`v2.1.0...HEAD` for `Unreleased`. The release candidate must include the
final date and documentation before validation. Publication, artifact
equality and independent consumer results remain separate release evidence
in #5493; a version heading is not proof of publication.

orb-tools v12.5.0 **RC011 checks only the bundled examples' Orb major against
the release tag major**. It does not check this README or full `2.1.0`
equality. README, every example and CHANGELOG need a separate full-version
review; a branch-time RC011 skip is not a successful release-tag check.
