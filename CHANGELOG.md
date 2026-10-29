# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add the `execute.config_data` string parameter (default: empty) to pass
  YAML configuration or an upstream configuration name as one literal
  argument. Empty values retain the existing configuration discovery or
  `config_file` behavior; non-empty values are interpreted by yamllint.
- Reject non-empty `config_file` and `config_data` used together with exit
  status `2` and an Orb diagnostic on stderr before the lint invocation.
  The separate version-display step may still run before this validation.

### Changed

- Treat each non-empty line of `targets` as a literal file or directory path,
  separated from yamllint options by `--`. Values beginning with `-`, including
  option-like names such as `--version`, are now paths rather than CLI options.
  Use the dedicated Orb parameters to set options. Empty lines are still
  ignored, and an empty target list still defaults to `.`.
- Reject a target line equal to `-` with exit status `2` and an Orb diagnostic
  on stderr before the lint invocation. This changes the previous behavior
  that could reach yamllint's stdin mode. Use `./-` to lint a file named `-`;
  a stdin interface is not provided. The separate version-display step may
  still run before this validation.

## [2.0.0] - 2026-10-24

### Added

- Added a v1-to-v2 migration guide with before/after configurations and the
  `config-file` to `config_file` parameter mapping.
- Added a combined integration test for `targets`, `config_file`, `strict`,
  and `format`, checking selected arguments, warning-only strict exit status,
  parsable output, and command execution.
- Added single-file target coverage and argument/count checks to the existing
  directory and multiple-target integration tests.
- Added an integration-test coverage matrix and release-dependency checks in
  `.circleci/INTEGRATION_TESTS.md`.

### Changed

- **Breaking:** renamed the `execute` parameter `config-file` to `config_file`
  without a compatibility alias. The other execute parameters, install
  behavior, and executor options remain unchanged.
- Updated the development pipeline from `circleci/orb-tools@11.1` to
  `circleci/orb-tools@12.5.0` and from `circleci/shellcheck@3.1` to
  `circleci/shellcheck@3.4.0`, including the v12 parameter names and review
  Orb name.
- Switched integration testing to the packed source Orb injected inline by
  `orb-tools/continue`, after setup lint, pack, review, and ShellCheck succeed.
- Pinned both pack jobs to `circleci/circleci-cli:1.11.0` using the `orb-pack`
  executor for the updated CLI validation path.
- Tightened the invalid-YAML and default-configuration rejection tests to
  require exit status `1` instead of accepting any non-zero status.
- Made downstream pack require all eleven integration tests to succeed, and
  production publish require that pack to succeed. Preserved the release-tag
  pattern `^v[0-9]+\.[0-9]+\.[0-9]+$`, branch exclusion, and tag reachability of
  prerequisite jobs. The `CIRCLECI_ORBS` Context is assigned only to production
  publish.
- Updated README Usage and the bundled example to use
  `orbss/yamllint@2.0.0`, while preserving the minimal install/execute
  workflow.

### Removed

- Removed the setup development-publish job and downstream
  `orbss/yamllint@dev:<<pipeline.git.revision>>` reference; inline source testing
  no longer depends on publishing a development Orb.

### Development

- Recorded the development probe `.circleci/orb-lint-phase-1-4-fail.yml`, added
  after v1.1.5 in commit `9a9c3af`. The file is retained unchanged. It is a
  development artifact, not an Orb feature; its presence does not establish
  execution or successful verification by the current pipeline.

## [1.1.5] - 2026-08-16

### Changed

- Added GitHub comparison links for CHANGELOG versions.
- Added an `[Unreleased]` comparison link from the latest release to `HEAD`.
- Updated the README usage example to reference `orbss/yamllint@1.1.5`.

## [1.1.4] - 2026-08-16

### Changed

- Added `display.home_url` metadata pointing to the yamllint Orb Registry page.
- Updated the README usage example to reference `orbss/yamllint@1.1.4`.

## [1.1.3] - 2026-08-16

### Changed

- Documented the `resource_class` parameter for the default executor.
- Added examples for configuring the resource class and combining it with a
  custom executor image.
- Updated the README usage example to reference `orbss/yamllint@1.1.3`.

## [1.1.2] - 2026-08-16

### Changed

- Documented the runtime requirements for custom executor images, including
  Bash, the `python` command, pip, and a Python environment that allows package
  installation.
- Clarified that CircleCI `cimg/python` convenience images are the recommended
  custom executor images.
- Updated the README usage example to reference `orbss/yamllint@1.1.2`.

## [1.1.1] - 2026-08-16

### Fixed

- Fixed exit status handling in the `format-test` integration test so that
  yamllint failures can be inspected correctly when `set -e` is enabled.

## [1.1.0] - 2026-08-16

### Added

- Added the `targets` parameter to the `execute` command.
- Added support for specifying multiple lint targets using one target per line.
- Added integration tests for the `targets` parameter.
- Added the `config-file` parameter to the `execute` command.
- Added an integration test to verify that a custom yamllint configuration
  file changes lint behavior as expected.
- Added the `strict` parameter to the `execute` command.
- Added an integration test to verify that warnings cause a non-zero
  exit status when strict mode is enabled.
- Added the `format` parameter to the `execute` command.
- Added an integration test to verify that the requested yamllint output
  format is applied.

## [1.0.0] - 2026-08-16

### Added

- Added the `install` command with support for installing a specific yamllint
  version.
- Added integration tests for the install command, version parameter,
  executor parameters, and lint failure behavior.

### Changed

- Changed the default executor image to `cimg/python:3.14`.
- Simplified the yamllint version display logic.
- Updated the README usage example to reference `orbss/yamllint@1.0.0`.

### Fixed

- Fixed the production Orb publishing configuration.
- Fixed the example executor name.
- Fixed the README LICENSE link.
- Fixed the LICENSE copyright information.

## [0.0.11] - 2026-08-16

### Fixed

- Replaced the `<organization>` placeholder in `LICENSE` with
  `mamono210`.
- Updated the copyright year range to `2022-2026`.

## [0.0.10] - 2026-08-16

### Fixed

- Fixed the LICENSE link in `README.md` to reference the `main` branch
  instead of the non-existent `master` branch.

## [0.0.9] - 2026-08-16

### Changed

- Simplified `show-version.sh` to execute `yamllint --version` directly.
- Removed the ShellCheck `SC2196` exclusion because `egrep` is no longer used.

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

[Unreleased]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.5...v2.0.0
[1.1.5]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.11...v1.0.0
[0.0.11]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.10...v0.0.11
[0.0.10]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.9...v0.0.10
[0.0.9]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.8...v0.0.9
[0.0.8]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/circleci-orbs-mamono210/yamllint/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/circleci-orbs-mamono210/yamllint/releases/tag/v0.0.5

