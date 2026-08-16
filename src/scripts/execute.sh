#!/bin/bash

set -euo pipefail

YAMLLINT_ARGS=()
TARGETS=()

if [[ -n "${PARAM_CONFIG_FILE}" ]]; then
    YAMLLINT_ARGS+=("--config-file" "${PARAM_CONFIG_FILE}")
fi

case "${PARAM_STRICT:-false}" in
    true | 1)
        YAMLLINT_ARGS+=("--strict")
        ;;
    false | 0 | "")
        ;;
    *)
        echo "Invalid strict value: ${PARAM_STRICT}" >&2
        exit 2
        ;;
esac

while IFS= read -r target; do
    if [[ -n "${target}" ]]; then
        TARGETS+=("${target}")
    fi
done <<< "${PARAM_TARGETS}"

if [[ "${#TARGETS[@]}" -eq 0 ]]; then
    TARGETS=(".")
fi

yamllint "${YAMLLINT_ARGS[@]}" "${TARGETS[@]}"
