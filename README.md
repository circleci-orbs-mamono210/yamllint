[![CircleCI Build Status](https://circleci.com/gh/circleci-orbs-mamono210/yamllint.svg?style=shield "CircleCI Build Status")](https://circleci.com/gh/circleci-orbs-mamono210/yamllint) [![CircleCI Orb Version](https://badges.circleci.com/orbs/orbss/yamllint.svg)](https://circleci.com/orbs/registry/orb/orbss/yamllint) [![GitHub License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://raw.githubusercontent.com/circleci-orbs-mamono210/yamllint/main/LICENSE)

# yamllint Orb

CircleCI Orb for running yamllint.

## Usage

```yaml
version: 2.1

orbs:
  yamllint: orbss/yamllint@1.0.0

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

The selected image must provide Python and pip so that the `install` command can install yamllint.

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
