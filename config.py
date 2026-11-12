"""Centralized configuration for Interactive Transformer Learning Machine."""

import os

# Window settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FULLSCREEN = os.getenv("TRANSFORMER_FULLSCREEN", "0") == "1"
# Reference workbench animation cadence.
FPS = 60
RESIZABLE = not FULLSCREEN
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 620

# Physical parameter limits and defaults
Vp_DEFAULT = 0.0
Vp_MIN = 0.0
Vp_MAX = 240.0
Vp_STEP = 1.0

Np_DEFAULT = 0
Np_MIN = 0
Np_MAX = 1000
Np_STEP = 10

Ns_DEFAULT = 0
Ns_MIN = 0
Ns_MAX = 1000
Ns_STEP = 10
TURNS_KNOB_STEP = 50

Simulated_Frequency_DEFAULT = 60
Simulated_Frequency_OPTIONS = [50, 60]

# Reference workbench design tokens. The index page continues to use the same
# shared palette while the workbench renders at its fixed reference size.
UI_HEADER_HEIGHT = 56
UI_WIDTH, UI_HEIGHT = 1240, 488 + UI_HEADER_HEIGHT
UI_INDEX_WIDTH, UI_INDEX_HEIGHT = 1240, 620
COLOR_BACKGROUND = (255, 255, 255)
COLOR_CARD = (255, 255, 255)
COLOR_TEXT = (12, 12, 12)
COLOR_TEXT_DARK = (38, 38, 38)
COLOR_TEXT_SUBTLE = (90, 90, 90)
COLOR_BORDER = (190, 190, 190)
COLOR_BUTTON_HOVER = (242, 242, 242)
COLOR_BUTTON_PRESSED = (225, 225, 225)
COLOR_PANEL = (234, 237, 241)
COLOR_ACCENT_PRIMARY = (31, 95, 200)
COLOR_ACCENT_SECONDARY = (46, 125, 50)
COLOR_CORE = (38, 38, 38)
COLOR_FLUX = (60, 60, 60)
COLOR_FILL_PRIMARY = (196, 214, 246)
COLOR_FILL_SECONDARY = (200, 228, 204)
COLOR_BASE = (170, 176, 184)
COLOR_WAVE_PRIMARY = (40, 75, 160)
COLOR_WAVE_SECONDARY = (60, 60, 60)
COLOR_DOT_PRIMARY = (50, 120, 220)
COLOR_DOT_SECONDARY = (60, 175, 70)
COLOR_DISABLED = (150, 150, 150)

UI_PAD, UI_GAP, UI_COLUMN_WIDTH = 16, 10, 320
UI_BAR_HEIGHT, UI_KNOB_HEIGHT, UI_BUTTON_HEIGHT = 76, 160, 38
UI_KNOB_RADIUS = 52
UI_REF_WIDTH, UI_REF_HEIGHT = 626, 242
UI_CX = UI_REF_WIDTH / 2
UI_TOP, UI_BOTTOM, UI_JOG, UI_STUB = 72, 158, 8, 6
UI_COIL_RADIUS, UI_COIL_RADIUS_Y = 14, 7
UI_COIL_GAP, UI_CORE_GAP = 12, 4
UI_TERMINAL_DX, UI_WAVE_WIDTH, UI_LABEL_DX = 146, 70, 213

UI_PAD, UI_GAP = 16, 10
UI_COLUMN_WIDTH = 320
UI_BAR_HEIGHT, UI_KNOB_HEIGHT, UI_BUTTON_HEIGHT = 76, 160, 38
UI_KNOB_RADIUS = 52
UI_REF_WIDTH, UI_REF_HEIGHT = 626, 242
UI_CX = UI_REF_WIDTH / 2
UI_TOP, UI_BOTTOM = 72, 158
UI_JOG, UI_STUB = 8, 6
UI_COIL_RADIUS, UI_COIL_RADIUS_Y = 14, 7
UI_COIL_GAP, UI_CORE_GAP = 12, 4
UI_TERMINAL_DX, UI_WAVE_WIDTH, UI_LABEL_DX = 146, 70, 213

# Font settings
FONT_FAMILY = "DejaVu Sans"
FONT_SIZE_SMALL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 20
FONT_SIZE_TITLE = 32

# Component styling
CORNER_RADIUS = 3
PADDING_SMALL = 8
PADDING_MEDIUM = 12
PADDING_LARGE = 16
GAP_SMALL = 6
GAP_MEDIUM = 12
GAP_LARGE = 20
BORDER_WIDTH = 1

# Animation settings
ANIMATION_ENABLED_DEFAULT = True
ANIMATION_SPEED_DEFAULT = 1.0

# Feature flags
FEATURE_SHOW_FLUX_ANIMATION = True
FEATURE_SHOW_TURNS_RATIO = True
FEATURE_KEYBOARD_CONTROLS = True

# Display precision
PRECISION_VOLTAGE = 2
PRECISION_RATIO = 3

# Default control method
CONTROL_METHOD = "Keyboard/Mouse"

# Optional Raspberry Pi hardware controls. Switches use BCM numbering and
# connect their GPIO input to GND; internal pull-ups are enabled by gpiozero.
# The ADS1115 analog inputs accept 0..ADS_REFERENCE_VOLTAGE only. Keep the
# potentiometer wipers within that range (typically 3.3 V on a Pi).
# Attempt physical controls on every launch; keyboard and mouse stay available.
# Set ITLW_HARDWARE=0 to explicitly disable GPIO/ADC initialization.
HARDWARE_ENABLED = os.getenv("ITLW_HARDWARE", "1") != "0"
HARDWARE_BUTTON_PINS = {
    # Vp tactile group
    "vp_plus_1": 4,
    "vp_minus_1": 17,
    "vp_plus_10": 27,
    "vp_minus_10": 22,
    # Np tactile group
    "np_plus_1": 10,
    "np_minus_1": 9,
    "np_plus_10": 11,
    "np_minus_10": 5,
    # Ns tactile group
    "ns_plus_1": 6,
    "ns_minus_1": 13,
    "ns_plus_10": 19,
    "ns_minus_10": 26,
    # Push buttons
    "btn_mode": 20,
    "btn_reset": 21,
}
TACTILE_ACTIONS = {
    "vp_plus_1": ("vp", 1),
    "vp_minus_1": ("vp", -1),
    "vp_plus_10": ("vp", 10),
    "vp_minus_10": ("vp", -10),
    "np_plus_1": ("np", 1),
    "np_minus_1": ("np", -1),
    "np_plus_10": ("np", 10),
    "np_minus_10": ("np", -10),
    "ns_plus_1": ("ns", 1),
    "ns_minus_1": ("ns", -1),
    "ns_plus_10": ("ns", 10),
    "ns_minus_10": ("ns", -10),
}
HARDWARE_DEBOUNCE_SECONDS = 0.06
HARDWARE_REPEAT_DELAY = 0.45
HARDWARE_REPEAT_INTERVAL = 0.12
HARDWARE_REPEAT_FAST_INTERVAL = 0.06
ADS_ENABLED = os.getenv("ITLW_ADS", "1") == "1"
ADS_ADDRESS = 0x48
ADS_GAIN = 1
ADS_REFERENCE_VOLTAGE = 3.3
ADS_SAMPLE_INTERVAL = 0.05
# ADS_KNOB_CHANNELS = {"pot_np": 0}
# ADS_KNOB_CHANNELS = {"pot_ns": 1}
ADS_KNOB_CHANNELS = {"pot_np": 0, "pot_ns": 1}
# Two B50k potentiometers map their full travel to the turns ranges.
HARDWARE_KNOB_RANGES = {
    "pot_np": (0, 1000, TURNS_KNOB_STEP),
    "pot_ns": (0, 1000, TURNS_KNOB_STEP),
}
ADS_DEADBAND = {"pot_np": 8, "pot_ns": 8}

# Suggested keyboard defaults (centralized)
KEYBINDING_SELECT_NEXT = "Tab"
KEYBINDING_ADJUST_INCREMENT = "ArrowUp, ArrowDown, Left, Right"
KEYBINDING_TOGGLE_MODE = "M"
KEYBINDING_RESET = "R"
KEYBINDING_HELP = "H"
KEYBINDING_TOGGLE_ANIMATION = "A"
