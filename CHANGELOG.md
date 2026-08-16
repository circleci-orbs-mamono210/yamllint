# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.8] - 2026-08-16

### Added

- Added a negative integration test to verify that yamllint returns a
  non-zero exit status when invalid YAML is detected.
- Added the negative integration test as a prerequisite for production
  publishing.

## [0.0.7] - 2026-08-16

### Changed

- Changed the default executor image from
  `ghcr.io/docker-images-mamono210/circleci-executors/yamllint:latest`
  to `cimg/python:3.14`.
- Updated command and resource class integration tests to install yamllint
  explicitly with the `install` command before running `execute`.

### Added

- Added an integration test to verify that a custom executor image can still
  be specified with the `image` parameter.

## [0.0.6] - 2026-08-16

### Added

- Added the `install` command to install yamllint with `python -m pip`.
- Added the `install.version` parameter to install a specific yamllint version.
- Added integration tests for the `install` command and the
  `install.version` parameter using `cimg/python:3.14`.

## [0.0.5] - 2026-08-16

### Added

- Added `CHANGELOG.md` to document notable changes to the Orb.

### Fixed

- Updated the production publish context in `.circleci/test-deploy.yml`
  from `<publishing-context>` to `CIRCLECI_ORBS`.
- Fixed the `yamllint/defaut` executor typo in `src/examples/example.yml`
  to `yamllint/default`.
