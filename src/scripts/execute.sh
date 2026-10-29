#!/bin/bash

set -euo pipefail

YAMLLINT_ARGS=()
TARGETS=()

# Keep configuration validation before argument construction and any body call.
# Both normal lint and file-listing modes share this input contract.
if [[ -n "${PARAM_CONFIG_FILE}" && -n "${PARAM_CONFIG_DATA:-}" ]]; then
    printf '%s\n' "yamllint Orb: config_file and config_data cannot both be non-empty." >&2
    exit 2
fi

if [[ -n "${PARAM_CONFIG_FILE}" ]]; then
    YAMLLINT_ARGS+=("--config-file" "${PARAM_CONFIG_FILE}")
elif [[ -n "${PARAM_CONFIG_DATA:-}" ]]; then
    YAMLLINT_ARGS+=("--config-data" "${PARAM_CONFIG_DATA}")
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

if [[ "${PARAM_NO_WARNINGS:-false}" == "true" || "${PARAM_NO_WARNINGS:-false}" == "1" ]]; then
    YAMLLINT_ARGS+=("--no-warnings")
fi

if [[ -n "${PARAM_FORMAT:-}" ]]; then
    YAMLLINT_ARGS+=("--format" "${PARAM_FORMAT}")
fi

if [[ "${PARAM_LIST_FILES:-false}" == "true" || "${PARAM_LIST_FILES:-false}" == "1" ]]; then
    YAMLLINT_ARGS+=("--list-files")
fi

# Validate every target before invoking yamllint. This is shared input validation,
# independent of any options selecting how yamllint processes those targets.
while IFS= read -r target; do
    if [[ "${target}" == "-" ]]; then
        printf '%s\n' "yamllint Orb: standalone '-' is not supported in targets; use './-' for a file named '-'." >&2
        exit 2
    fi

    if [[ -n "${target}" ]]; then
        TARGETS+=("${target}")
    fi
done <<< "${PARAM_TARGETS}"

if [[ "${#TARGETS[@]}" -eq 0 ]]; then
    TARGETS=(".")
fi

yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[@]}"
