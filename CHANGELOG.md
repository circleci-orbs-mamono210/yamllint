# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.5] - 2026-08-16

### Added

- Added `CHANGELOG.md` to document notable changes to the Orb.

### Fixed

- Updated the production publish context in `.circleci/test-deploy.yml`
  from `<publishing-context>` to `CIRCLECI_ORBS`.
- Fixed the `yamllint/defaut` executor typo in `src/examples/example.yml`
  to `yamllint/default`.
