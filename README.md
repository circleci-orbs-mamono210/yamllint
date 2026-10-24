[![CircleCI Build Status](https://circleci.com/gh/circleci-orbs-mamono210/yamllint.svg?style=shield "CircleCI Build Status")](https://circleci.com/gh/circleci-orbs-mamono210/yamllint) [![CircleCI Orb Version](https://badges.circleci.com/orbs/orbss/yamllint.svg)](https://circleci.com/orbs/registry/orb/orbss/yamllint) [![GitHub License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://raw.githubusercontent.com/circleci-orbs-mamono210/yamllint/main/LICENSE)

# yamllint Orb

CircleCI Orb for running yamllint.

## Usage

This example targets the planned `2.0.0` release. The version reference is
prepared for that release; it does not indicate that `2.0.0` has been published.
Use this reference after the release is available.

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.0.0

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

Update the Orb reference to `orbss/yamllint@2.0.0` when that release is
available, and rename the `yamllint/execute` parameter `config-file` to
`config_file` in every invocation. There is no compatibility alias for
`config-file` in v2; a configuration that still passes the old name must be
updated before it can use v2.

The following examples assume `.yamllint-ci` already exists in your repository.
The v2 example is a migration target for the planned release.

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

### After: v2

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@2.0.0

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

The behavior of the other `execute` parameters is unchanged:

| Parameter | Type | Default | Behavior in v2 |
| --- | --- | --- | --- |
| `targets` | string | `.` | Lint a file or directory, or multiple targets with one target per line |
| `config_file` (v1: `config-file`) | string | `""` | Supply a configuration path; an empty value keeps normal yamllint configuration discovery |
| `strict` | boolean | `false` | Enable strict mode so warnings produce a non-zero exit status |
| `format` | string | `""` | Pass an output format to yamllint; an empty value keeps its default format |

`format` remains a string parameter, not an Orb enum. Format values are
interpreted by the installed yamllint version. The underlying yamllint CLI
option remains `--config-file`; only the Orb parameter name changes.

The minimum `checkout` → `yamllint/install` → `yamllint/execute` configuration
shown in Usage is unchanged. If you do not pass `config-file`, no step changes
are needed when updating the Orb version. The `install.version` parameter,
executor image and resource-class options, and custom image requirements are
also unchanged; their details are documented below.

## Executor

The default executor uses:

```text
cimg/python:3.14
```

A custom Docker image can be specified with the `image` parameter.

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

```yaml
steps:
  - yamllint/install:
      version: "1.37.1"
```

This is equivalent to:

```bash
python -m pip install "yamllint==1.37.1"
```

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
yamllint .
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

If `config_file` is not specified, yamllint uses its normal configuration
discovery behavior.

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

