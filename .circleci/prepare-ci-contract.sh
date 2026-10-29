#!/bin/bash
# The only continuation input is the inline config checked by this script.
set -euo pipefail

evidence_dir="${PHASE5_EVIDENCE_DIR:-/tmp/yamllint-phase5}"
mkdir -p "${evidence_dir}"

if [[ "${CIRCLECI:-false}" == true ]]; then
    # orb-tools/continue checks all three even with inject_orb disabled.
    command -v curl jq yq > "${evidence_dir}/continuation-tools.txt"
    jq --version >> "${evidence_dir}/continuation-tools.txt"
    yq --version >> "${evidence_dir}/continuation-tools.txt"
fi

if [[ -z "${PHASE5_CIRCLECI_CLI:-}" ]]; then
    [[ "$(uname -m)" == x86_64 ]]
    cli_dir="$(mktemp -d)"
    curl --fail --silent --show-error --location \
        https://github.com/CircleCI-Public/circleci-cli/releases/download/v1.11.0/circleci-cli_1.11.0_linux_amd64.tar.gz \
        --output "${cli_dir}/cli.tar.gz"
    printf '%s  %s\n' \
        '70c3a935e0c2d71d42ba65f0005696eb17fd65fb625c678f45311b826d56de47' \
        "${cli_dir}/cli.tar.gz" | sha256sum --check
    tar --no-same-owner -xzf "${cli_dir}/cli.tar.gz" -C "${cli_dir}" circleci
    PHASE5_CIRCLECI_CLI="${cli_dir}/circleci"
fi

"${PHASE5_CIRCLECI_CLI}" version > "${evidence_dir}/circleci-version.txt"
grep -Eq '^circleci 1\.11\.0([ +]|$)' "${evidence_dir}/circleci-version.txt"
tar --no-same-owner -xzf "$1" -C "${evidence_dir}" ./orb.yml
python .circleci/check-ci-contract.py prepare --evidence-dir "${evidence_dir}"

"${PHASE5_CIRCLECI_CLI}" config process "${evidence_dir}/injected.yml" \
    > "${evidence_dir}/expanded.yml"
"${PHASE5_CIRCLECI_CLI}" config process "${evidence_dir}/parameter-probes.yml" \
    > "${evidence_dir}/parameter-probes-expanded.yml"
"${PHASE5_CIRCLECI_CLI}" config process .circleci/config.yml \
    > "${evidence_dir}/setup-expanded.yml"

python .circleci/check-ci-contract.py verify --evidence-dir "${evidence_dir}"
PHASE5_EVIDENCE_DIR="${evidence_dir}" python .circleci/test-ci-contract.py -v \
    > "${evidence_dir}/contract-negative-controls.log" 2>&1
cat "${evidence_dir}/contract-negative-controls.log"
