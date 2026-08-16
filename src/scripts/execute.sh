#!/bin/bash

set -euo pipefail

TARGETS=()

while IFS= read -r target; do
    if [[ -n "${target}" ]]; then
        TARGETS+=("${target}")
    fi
done <<< "${PARAM_TARGETS}"

if [[ "${#TARGETS[@]}" -eq 0 ]]; then
    TARGETS=(".")
fi

yamllint "${TARGETS[@]}"
