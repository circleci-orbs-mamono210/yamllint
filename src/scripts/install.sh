#!/bin/bash

set -euo pipefail

if [[ -n "${PARAM_VERSION}" ]]; then
    python -m pip install "yamllint==${PARAM_VERSION}"
else
    python -m pip install yamllint
fi
