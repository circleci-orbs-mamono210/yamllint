[![CircleCI Build Status](https://circleci.com/gh/circleci-orbs-mamono210/yamllint.svg?style=shield "CircleCI Build Status")](https://circleci.com/gh/circleci-orbs-mamono210/yamllint) [![CircleCI Orb Version](https://badges.circleci.com/orbs/orbss/yamllint.svg)](https://circleci.com/orbs/registry/orb/orbss/yamllint) [![GitHub License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://raw.githubusercontent.com/circleci-orbs-mamono210/yamllint/main/LICENSE)

# yamllint Orb

CircleCI Orb for running yamllint.

## Usage

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@1.1.2

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

The `config-file` parameter can be used to explicitly specify a yamllint
configuration file.

```yaml
steps:
  - yamllint/execute:
      config-file: .yamllint-ci
```

The `config-file` parameter can be combined with `targets`.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
      config-file: .yamllint-ci
```

If `config-file` is not specified, yamllint uses its normal configuration
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

The `strict` parameter can be combined with `targets` and `config-file`.

```yaml
steps:
  - yamllint/execute:
      targets: .circleci/
      config-file: .yamllint-ci
      strict: true
```

### Specify an output format

The `format` parameter can be used to specify the yamllint output format.

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
      config-file: .yamllint-ci
      strict: true
      format: parsable
```

