#!/usr/bin/env bash
# Fast-forward to origin/main and restart the graphical user service. Since
# this script is stored in the checkout, all executable logic is in main().

log_tag="itlw-auto-update"

log() {
    logger -t "$log_tag" -- "$*" || printf '%s\n' "$*" >&2
}

main() {
    set -Eeuo pipefail

    local project_dir service_name update_branch lock_dir lock_file state_dir state_file result_file
    local previous target status changed_app changed_hardware rollback_armed
    local failure_status failure_command tmp_bad_commit

    project_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
    service_name="itlw.service"
    lock_dir="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}"
    lock_file="$lock_dir/itlw-update-${UID:-$(id -u)}.lock"
    state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/itlw"
    state_file="$state_dir/bad-commit"
    result_file="$state_dir/last-update.json"
    changed_app=0
    changed_hardware=0
    rollback_armed=0

    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/${UID:-$(id -u)}}"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

    write_result() {
        local result="$1" from_commit="$2" to_commit="$3" reason="$4"
        mkdir -p "$state_dir" || return 1
        python3 - "$result_file" "$result" "$from_commit" "$to_commit" "$reason" <<'PY'
import datetime
import json
import os
import pathlib
import sys
import tempfile

path = pathlib.Path(sys.argv[1])
result, from_commit, to_commit, reason = sys.argv[2:6]
try:
    previous_result = json.loads(path.read_text())
except (OSError, ValueError):
    previous_result = {}
if (previous_result.get("shown") is False
        and previous_result.get("result") in {"updated", "rolled_back"}
        and result in {"no_change", "skipped"}):
    raise SystemExit(0)
document = {
    "result": result,
    "from_commit": from_commit or None,
    "to_commit": to_commit or None,
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "reason": reason or None,
    "shown": False,
}
path.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                 prefix=path.name + ".", delete=False) as handle:
    json.dump(document, handle)
    handle.write("\n")
    temporary = handle.name
os.replace(temporary, path)
PY
    }

    exec 9>"$lock_file"
    if ! flock -n 9; then
        log "SKIPPED: another update run holds the lock"
        return 0
    fi

    cd "$project_dir"
    if [[ "${ITLW_UPDATE_MODE:-manual}" == "off" ]]; then
        previous="$(git rev-parse HEAD 2>/dev/null || true)"
        log "SKIPPED: updates are disabled by ITLW_UPDATE_MODE=off"
        write_result skipped "$previous" "" "updates are disabled"
        return 0
    fi
    if [[ ! -d .git ]]; then
        log "ERROR: no Git checkout at $project_dir"
        return 1
    fi

    update_branch="$(git branch --show-current)"

    if [[ -z "$update_branch" ]]; then
        previous="$(git rev-parse HEAD 2>/dev/null || true)"
        log "ERROR: cannot update from detached HEAD"
        write_result skipped "$previous" "" "cannot update from detached HEAD"
        return 1
    fi

    status="$(git status --porcelain --untracked-files=normal)" || {
        log "ERROR: could not inspect Git working tree"
        return 1
    }
    if [[ -n "$status" ]]; then
        previous="$(git rev-parse HEAD 2>/dev/null || true)"
        log "ERROR: refusing update because the working tree is not clean; files:"
        while IFS= read -r line; do
            [[ -n "$line" ]] && log "  $line"
        done <<< "$status"
        write_result skipped "$previous" "" "working tree is not clean"
        return 1
    fi

    # In auto mode the timer may fire before labwc exports a display. Defer
    # the check so it cannot start the graphical app outside its desktop.
    if [[ "${ITLW_UPDATE_MODE:-manual}" == "auto" && -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        previous="$(git rev-parse HEAD 2>/dev/null || true)"
        log "SKIPPED: graphical display is not available yet"
        write_result skipped "$previous" "" "graphical desktop is not available"
        return 0
    fi

    if ! git fetch --quiet origin "$update_branch"; then
        log "ERROR: git fetch origin $update_branch failed"
        previous="$(git rev-parse HEAD 2>/dev/null || true)"
        write_result skipped "$previous" "" "GitHub fetch failed"
        return 1
    fi

    previous="$(git rev-parse HEAD)" || {
        log "ERROR: could not determine current commit"
        return 1
    }
    target="$(git rev-parse "refs/remotes/origin/$update_branch")" || {
        log "ERROR: could not determine origin/$update_branch commit"
        return 1
    }
    if [[ "$previous" == "$target" ]]; then
        log "NO CHANGE: already at $target"
        write_result no_change "$previous" "$target" "already up to date"
        return 0
    fi

    if [[ -f "$state_file" ]] && [[ "$(<"$state_file")" == "$target" ]]; then
        log "SKIPPED: origin/$update_branch $target previously failed; waiting for a newer commit"
        write_result skipped "$previous" "$target" "this commit previously failed and was rolled back"
        return 0
    fi
    if ! git merge-base --is-ancestor "$previous" "$target"; then
        log "ERROR: origin/$update_branch $target is not a fast-forward from $previous"
        write_result skipped "$previous" "$target" "update is not a fast-forward"
        return 1
    fi

    if ! git diff --quiet "$previous" "$target" -- requirements.txt; then
        changed_app=1
    fi
    if ! git diff --quiet "$previous" "$target" -- requirements-hardware.txt; then
        changed_hardware=1
    fi

    on_error() {
        failure_status=$?
        local rollback_ok
        failure_command="$1"
        trap - ERR
        set +e
        rollback_ok=1
        log "ERROR: update of $target failed (status $failure_status): $failure_command"
        if (( rollback_armed )); then
            log "ROLLING BACK: $target to $previous"
            git reset --hard "$previous" || rollback_ok=0
            if (( changed_app )) && [[ -f requirements.txt ]]; then
                .venv/bin/python -m pip install -r requirements.txt || rollback_ok=0
            fi
            if (( changed_hardware )) && [[ -f requirements-hardware.txt ]]; then
                .venv/bin/python -m pip install -r requirements-hardware.txt --no-build-isolation || rollback_ok=0
                .venv/bin/python -m pip install adafruit-blinka 'adafruit-circuitpython-ads1x15<3' || rollback_ok=0
            fi
            systemctl --user restart "$service_name" || rollback_ok=0
            sleep 5
            if systemctl --user is-active --quiet "$service_name"; then
                :
            else
                rollback_ok=0
            fi
            if (( rollback_ok )); then
                log "ROLLED BACK: running $previous; failed commit $target recorded"
            else
                log "ERROR: rollback to $previous was incomplete; failed commit $target recorded"
            fi
            mkdir -p "$state_dir"
            tmp_bad_commit="$state_file.tmp.$$"
            if printf '%s\n' "$target" > "$tmp_bad_commit" && mv -f "$tmp_bad_commit" "$state_file"; then
                log "SKIPPED: recorded bad commit $target at $state_file"
            else
                rm -f "$tmp_bad_commit"
                log "ERROR: could not record failed commit $target"
            fi
            write_result rolled_back "$previous" "$target" "$failure_command" || \
                log "ERROR: could not write update result to $result_file"
        else
            log "ERROR: update failed before checkout; no rollback was needed"
            write_result skipped "$previous" "$target" "$failure_command" || \
                log "ERROR: could not write update result to $result_file"
        fi
        exit "$failure_status"
    }

    if ! write_result updating "$previous" "$target" ""; then
        log "ERROR: could not write updating state to $result_file"
    fi
    trap 'on_error "$BASH_COMMAND"' ERR
    rollback_armed=1

    git merge --ff-only "$target"
    if (( changed_app )); then
        .venv/bin/python -m pip install -r requirements.txt
    fi
    if (( changed_hardware )); then
        .venv/bin/python -m pip install -r requirements-hardware.txt --no-build-isolation
        # hardware.py uses the ADS1x15 2.x channel names.
        .venv/bin/python -m pip install adafruit-blinka 'adafruit-circuitpython-ads1x15<3'
    fi

    systemctl --user restart "$service_name"
    sleep 5
    systemctl --user is-active --quiet "$service_name"
    rollback_armed=0
    rm -f "$state_file"
    write_result updated "$previous" "$target" "" || \
        log "ERROR: could not write update result to $result_file"
    log "UPDATED: $previous -> $target; app service is active"
}

main "$@"
exit $?
