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

# The only yamllint body invocation; both output modes call it unchanged.
run_yamllint() {
    yamllint "${YAMLLINT_ARGS[@]}" -- "${TARGETS[@]}"
}

OUTPUT_FILE="${PARAM_OUTPUT_FILE:-}"

# Saving disabled (the default): no destination checks, files or relay.
# yamllint keeps this step's stdout; its output and exit status are unchanged.
if [[ -z "${OUTPUT_FILE}" ]]; then
    run_yamllint
    exit 0
fi

# Saving enabled. All existing input refusals above have already run, so
# output_file is checked last and only before yamllint starts.
# The helper is part of this script and runs as "python3 -I" (isolated mode,
# no imports from the working directory):
#   prepare  - refuse unsafe destinations, then create an empty temporary file
#              in the destination's real parent directory; print its token.
#   forward  - copy yamllint's stdout to this step's stdout as it arrives and
#              to the temporary file; keep reading to the end even if either
#              write fails, so a save failure never cuts yamllint short.
#   finalize - link the complete temporary file to the destination without
#              replacing any entry, then remove the temporary name.
ORB_OUTPUT_HELPER='
import os
import select
import stat
import sys

PREFIX = "yamllint Orb: output_file: "
TEMPORARY_PREFIX = ".yamllint-orb-output-"
TEMPORARY_SUFFIX = ".tmp"
LOG_FAILED = 10
SAVE_FAILED = 11
BOTH_FAILED = 12
PROBLEM = 3


def report(message):
    try:
        sys.stderr.write(PREFIX + message + "\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def reason(error):
    return error.strerror or str(error)


def refuse(message):
    report("rejected: " + message + "; yamllint was not run")
    return 2


def unprepared(message):
    report("could not prepare the output: " + message + "; yamllint was not run")
    return 2


def split(raw):
    head, tail = os.path.split(raw)
    return head or ".", tail


def destination_path(raw):
    parent, tail = split(raw)
    return os.path.join(os.path.realpath(parent), tail)


def temporary_path(raw, token):
    parent, tail = split(raw)
    name = TEMPORARY_PREFIX + token + TEMPORARY_SUFFIX
    return os.path.join(os.path.realpath(parent), name)


def entry_kind(path):
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        if os.path.exists(path):
            return "a symbolic link"
        return "a broken symbolic link"
    if stat.S_ISDIR(mode):
        return "a directory"
    if stat.S_ISREG(mode):
        return "a regular file"
    return "a special file"


def inside(path, directory):
    return os.path.commonpath([path, directory]) == directory


def prepare(raw, config_file, targets):
    if "\n" in raw or "\r" in raw:
        return refuse("the path must not contain a newline or carriage return")
    parent, tail = split(raw)
    if tail in ("", ".", ".."):
        return refuse(repr(raw) + " does not name a file")
    try:
        parent_mode = os.stat(parent).st_mode
    except FileNotFoundError:
        return refuse("the parent directory " + repr(parent)
                      + " does not exist and is not created")
    except NotADirectoryError:
        return refuse("the parent " + repr(parent) + " is not a directory")
    except OSError as error:
        return unprepared("cannot access the parent directory " + repr(parent)
                          + ": " + reason(error))
    if not stat.S_ISDIR(parent_mode):
        return refuse("the parent " + repr(parent) + " is not a directory")
    try:
        existing = entry_kind(raw)
    except FileNotFoundError:
        existing = None
    except OSError as error:
        return unprepared("cannot inspect " + repr(raw) + ": " + reason(error))
    if existing is not None:
        return refuse(repr(raw) + " already exists as " + existing
                      + "; existing entries are never replaced")
    destination = destination_path(raw)
    for target in targets:
        real_target = os.path.realpath(target)
        if destination == real_target:
            return refuse(repr(raw) + " is the same path as the target " + repr(target))
        if os.path.isdir(target) and inside(destination, real_target):
            return refuse(repr(raw) + " is inside the target directory " + repr(target)
                          + "; save it outside every target directory")
    if config_file and destination == os.path.realpath(config_file):
        return refuse(repr(raw) + " is the same path as config_file " + repr(config_file))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    for _ in range(100):
        token = os.urandom(8).hex()
        path = temporary_path(raw, token)
        try:
            descriptor = os.open(path, flags, 0o666)
        except FileExistsError:
            continue
        except OSError as error:
            return unprepared("cannot create a temporary file in "
                              + repr(os.path.dirname(path)) + ": " + reason(error))
        os.close(descriptor)
        sys.stdout.write(token)
        return 0
    return unprepared("cannot create a unique temporary file")


def write_all(descriptor, data):
    view = memoryview(data)
    while view:
        try:
            written = os.write(descriptor, view)
        except BlockingIOError:
            select.select([], [descriptor], [])
            continue
        view = view[written:]


def forward(raw, token):
    path = temporary_path(raw, token)
    log_ok = True
    save_ok = True
    saved = None
    try:
        saved = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        save_ok = False
        report("could not open the temporary file " + repr(path) + ": " + reason(error))
    while True:
        try:
            chunk = os.read(0, 65536)
        except OSError as error:
            report("could not read the yamllint stdout: " + reason(error))
            return BOTH_FAILED
        if not chunk:
            break
        if log_ok:
            try:
                write_all(1, chunk)
            except OSError as error:
                log_ok = False
                report("could not forward the yamllint stdout to the step log: "
                       + reason(error))
        if save_ok:
            try:
                write_all(saved, chunk)
            except OSError as error:
                save_ok = False
                report("could not write the yamllint stdout to " + repr(path)
                       + ": " + reason(error))
    if saved is not None:
        try:
            os.close(saved)
        except OSError as error:
            if save_ok:
                save_ok = False
                report("could not complete " + repr(path) + ": " + reason(error))
    if log_ok and save_ok:
        return 0
    if save_ok:
        return LOG_FAILED
    if log_ok:
        return SAVE_FAILED
    return BOTH_FAILED


def finalize(raw, token, body_status, relay_status):
    path = temporary_path(raw, token)
    destination = destination_path(raw)
    started = body_status not in (126, 127)
    saved = relay_status in (0, LOG_FAILED)
    problem = relay_status != 0
    if relay_status not in (0, LOG_FAILED, SAVE_FAILED, BOTH_FAILED):
        report("the output relay ended unexpectedly with status " + str(relay_status))
    if not started:
        report("yamllint could not be started (exit status " + str(body_status)
               + "); no result file was created")
    elif saved:
        try:
            os.link(path, destination)
        except FileExistsError:
            saved = False
            problem = True
            report(repr(raw) + " appeared while yamllint was running; it was left unchanged")
        except OSError as error:
            saved = False
            problem = True
            report("could not create " + repr(raw) + ": " + reason(error))
    if started and not saved:
        report("the result file " + repr(raw) + " was not created")
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError as error:
        problem = True
        report("could not remove the temporary file " + repr(path) + ": " + reason(error))
    if problem:
        return PROBLEM
    return 0


def main(argv):
    action = argv[1]
    raw = argv[2]
    if action == "prepare":
        return prepare(raw, argv[3], argv[4:])
    if action == "forward":
        return forward(raw, argv[3])
    if action == "finalize":
        return finalize(raw, argv[3], int(argv[4]), int(argv[5]))
    report("unknown helper action " + repr(action))
    return 70


sys.exit(main(sys.argv))
'

if ! command -v python3 > /dev/null 2>&1; then
    printf '%s\n' "yamllint Orb: output_file: could not prepare the output: python3 was not found on PATH; yamllint was not run" >&2
    exit 2
fi

PREPARE_STATUS=0
OUTPUT_TOKEN="$(python3 -I -c "${ORB_OUTPUT_HELPER}" prepare "${OUTPUT_FILE}" "${PARAM_CONFIG_FILE:-}" "${TARGETS[@]}")" || PREPARE_STATUS=$?
if [[ "${PREPARE_STATUS}" -ne 0 || ! "${OUTPUT_TOKEN}" =~ ^[0-9a-f]{16}$ ]]; then
    if [[ "${PREPARE_STATUS}" -ne 2 ]]; then
        printf '%s\n' "yamllint Orb: output_file: could not prepare the output (helper status ${PREPARE_STATUS}); yamllint was not run" >&2
    fi
    exit 2
fi

# yamllint writes to a pipe (never a terminal); stdin and stderr are inherited.
set +e
run_yamllint | python3 -I -c "${ORB_OUTPUT_HELPER}" forward "${OUTPUT_FILE}" "${OUTPUT_TOKEN}"
RELAY_STATUS=("${PIPESTATUS[@]}")
set -e

FINALIZE_STATUS=0
python3 -I -c "${ORB_OUTPUT_HELPER}" finalize "${OUTPUT_FILE}" "${OUTPUT_TOKEN}" \
    "${RELAY_STATUS[0]}" "${RELAY_STATUS[1]}" || FINALIZE_STATUS=$?
if [[ "${FINALIZE_STATUS}" -ne 0 && "${FINALIZE_STATUS}" -ne 3 ]]; then
    printf '%s\n' "yamllint Orb: output_file: the result could not be finalized (helper status ${FINALIZE_STATUS})" >&2
fi

# A non-zero yamllint status always wins. Otherwise a save or relay problem
# fails the step with status 2.
if [[ "${RELAY_STATUS[0]}" -ne 0 ]]; then
    exit "${RELAY_STATUS[0]}"
fi
if [[ "${FINALIZE_STATUS}" -ne 0 ]]; then
    exit 2
fi
exit 0
