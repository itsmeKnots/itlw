#!/usr/bin/env bash
# Run from labwc after the graphical session has exported its display. Import
# the display variables into the user manager before starting either unit.
set -euo pipefail

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "No graphical display is available; cannot start the workbench." >&2
    exit 1
fi

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}"
export DISPLAY="${DISPLAY:-}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is not set in the desktop session}"

systemctl --user import-environment WAYLAND_DISPLAY DISPLAY XDG_RUNTIME_DIR
systemctl --user start itlw.service
