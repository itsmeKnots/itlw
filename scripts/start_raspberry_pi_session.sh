#!/usr/bin/env bash
# Run from labwc after the graphical session has exported its display.
set -euo pipefail

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "No graphical display is available; cannot start the workbench." >&2
    exit 1
fi

session_vars=(XDG_RUNTIME_DIR)
for variable in DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE XDG_CURRENT_DESKTOP; do
    if [[ -n "${!variable:-}" ]]; then
        session_vars+=("$variable")
    fi
done

systemctl --user import-environment "${session_vars[@]}"
systemctl --user restart itlw.service
