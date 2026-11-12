"""Pure transformer calculation logic with no Pygame dependencies."""

try:
    from config import PRECISION_RATIO
except Exception:
    PRECISION_RATIO = 3

from dataclasses import dataclass
from typing import Tuple
import math

import config as cfg


@dataclass
class TransformerState:
    """Input state for transformer calculations."""
    primary_voltage: float
    primary_turns: int
    secondary_turns: int
    frequency: float = 60.0


@dataclass
class TransformerResult:
    """Result from transformer calculations."""
    secondary_voltage: float
    turns_ratio: float
    classification: str
    classification_detail: str
    primary_voltage: float = 0.0
    primary_turns: int = 0
    secondary_turns: int = 0


def clamp(value, minimum, maximum):
    return min(maximum, max(minimum, value))


def jround(value):
    return math.floor(value + 0.5)


def set_vp(state, value):
    state.primary_voltage = int(clamp(jround(value), cfg.Vp_MIN, cfg.Vp_MAX))


def constrain(state, key, value):
    minimum = cfg.Np_MIN if key == "np" else cfg.Ns_MIN
    maximum = cfg.Np_MAX if key == "np" else cfg.Ns_MAX
    step = cfg.TURNS_KNOB_STEP
    value = clamp(value, minimum, maximum)
    other = state.secondary_turns if key == "np" else state.primary_turns
    larger = "ns" if state.operation == "up" else "np"
    if key == larger:
        if value > 0:
            value = max(value, other + step if other > 0 else step)
    else:
        value = min(value, other - step if other > 0 else maximum)
    return value


def set_turns(state, key, value):
    if state.operation is None:
        return
    value = constrain(state, key, jround(value))
    if key == "np":
        state.primary_turns = value
    else:
        state.secondary_turns = value


def nudge(state, key, delta):
    if key == "vp":
        set_vp(state, state.primary_voltage + delta)
    elif key == "np":
        set_turns(state, key, state.primary_turns + delta)
    else:
        set_turns(state, key, state.secondary_turns + delta)


def set_mode(state, mode):
    if state.operation == mode:
        return
    if state.operation is not None:
        state.primary_turns, state.secondary_turns = state.secondary_turns, state.primary_turns
    state.operation = mode


def toggle_mode(state):
    set_mode(state, "down" if state.operation == "up" else "up")


def reset(state):
    state.primary_voltage = 0
    state.primary_turns = 0
    state.secondary_turns = 0
    state.operation = None


def _clamp_primary_turns(np: int) -> int:
    """Prevent division by zero and handle invalid primary turns."""
    if np is None or np <= 0:
        return 1
    return np


def calculate_turns_ratio(np: int, ns: int) -> float:
    """Calculate turns ratio (Ns/Np)."""
    if np is None or np <= 0 or ns is None or ns < 0:
        return 0.0
    return ns / np


def calculate_output_voltage(vp: float = None, np: int = None, ns: int = None,
                             state: TransformerState = None) -> TransformerResult:
    """Calculate secondary voltage using Vs = Vp * (Ns / Np)."""
    if state is not None:
        np_count, ns_count, vp_val = state.primary_turns, state.secondary_turns, state.primary_voltage
    else:
        np_count, ns_count, vp_val = np, ns, vp

    vp_val = 0.0 if vp_val is None else max(0.0, float(vp_val))
    ns_count = 0 if ns_count is None else max(0, int(ns_count))
    valid_primary = np_count is not None and np_count > 0
    ratio = ns_count / np_count if valid_primary else 0.0
    vs = vp_val * ratio if valid_primary else 0.0

    if not valid_primary:
        classification = "INVALID"
        detail = "Enter primary turns above 0 to calculate Vs"
    elif ns_count > np_count:
        classification = "STEP-UP"
        detail = f"Ns ({ns_count}) > Np ({np_count}) — Vs ({vs:.4g}) > Vp ({vp_val:.4g})"
    elif ns_count < np_count:
        classification = "STEP-DOWN"
        detail = f"Ns ({ns_count}) < Np ({np_count}) — Vs ({vs:.4g}) < Vp ({vp_val:.4g})"
    else:
        classification = "1:1 RATIO"
        detail = f"Ns ({ns_count}) == Np ({np_count}) — Vs == Vp ({vp_val:.4g})"

    return TransformerResult(
        secondary_voltage=round(vs, 4),
        turns_ratio=round(ratio, PRECISION_RATIO),
        classification=classification,
        classification_detail=detail,
        primary_voltage=vp_val,
        primary_turns=np_count if valid_primary else 0,
        secondary_turns=ns_count,
    )


def classify_turns(ns: int, np: int) -> Tuple[str, str]:
    """Return operation classification and an explanatory detail."""
    if np is None or np <= 0:
        return "INVALID", "Primary turns must be > 0"
    ratio = ns / np
    if ns > np:
        return "STEP-UP", f"Ns ({ns}) > Np ({np}) (ratio={ratio:.3g})"
    if ns < np:
        return "STEP-DOWN", f"Ns ({ns}) < Np ({np}) (ratio={ratio:.3g})"
    return "1:1 RATIO", f"Ns ({ns}) == Np ({np}) (ratio={ratio:.3g})"
