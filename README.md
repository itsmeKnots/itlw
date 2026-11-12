# Interactive Transformer Learning Machine

A desktop Pygame learning tool for demonstrating the ideal single-phase transformer turns-ratio principle. It presents a transformer model alongside editable primary voltage (`Vp`), secondary voltage (`Vs`), primary turns (`Np`), and secondary turns (`Ns`).

> **Important:** this is a simulation. Every output reading is a calculated ideal value, not a live electrical-meter measurement. It does not connect to, measure, or control physical equipment.

## Raspberry Pi 4 deployment

This project is configured for a Raspberry Pi 4 Model B with 2 GB RAM and a 64-bit Raspberry Pi OS installation. The default frame rate is 30 FPS and the transformer schematic is drawn with Pygame primitives for responsive display.

Use a reliable 5 V / 3 A USB-C power supply and active cooling for sustained use. Use 720p display output for the smoothest presentation. Copy the entire project folder, excluding `.venv` and `__pycache__`; those files are generated locally and are not part of the transfer package.

On Raspberry Pi OS Bookworm or later, use a 64-bit installation and run:

```bash
cd transformer_workbench
bash scripts/install_raspberry_pi.sh
```

The installer enables a user service and configures labwc to start it after the graphical desktop session provides its display. Enable desktop autologin in Raspberry Pi OS if the workbench should appear without a manual login. The launcher starts the workbench full-screen. To run in a resizable window instead, use `TRANSFORMER_FULLSCREEN=0 .venv/bin/python main.py`.

GPIO and ADS controls are attempted on every launch; keyboard and mouse remain available.

## Run in VS Code

1. Open the `transformer_workbench` folder in VS Code.
2. Select a Python 3 interpreter from the status bar.
3. In the VS Code terminal, install the required dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Run the application:

   ```powershell
   python main.py
   ```

The app is designed for a 1280 × 720 desktop window and supports resizing down to 900 × 620. Close the window, or press `Esc` when help is not open, to exit.

The launch page includes live local-time and calendar widgets, plus placeholders for a project document and demo tutorial. Select **Open Workbench** or press `Enter` to launch the simulator. Press `Home` in the simulator to return to the launch page.

## How to use it

Set the primary input voltage `Vp` in the Voltage card, choose an operation in the Mode card, and adjust `Np`/`Ns` in the Turns card. These three cards share the right-side controls area evenly. Secondary voltage `Vs` is calculated output only; it is not an input. The results panel displays the calculated values and classification:

`Vs = Vp × (Ns / Np)`

`Ns > Np` is **STEP-UP**, `Ns < Np` is **STEP-DOWN**, and equal turns are **1:1 RATIO**. Inputs are constrained to safe configured ranges, so desktop UI interaction cannot create zero or negative turn counts.

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `Tab` / `Shift+Tab` | Focus next / previous control |
| Arrow keys | Increase or decrease the focused numeric input |
| `M` | Toggle Step-Up and Step-Down presets |
| `R` | Reset to 12 V, Np = 100, Ns = 200 |
| `A` | Toggle flux animation |
| `H` | Show or hide the shortcut help panel |
| `Esc` | Close help; otherwise exit the app |

Hover over a control for a short description. The header also keeps the `Press H for Help` legend visible.

## Architecture

```text
transformer_workbench/
├── main.py                  # Pygame startup, event loop, resize and shutdown
├── config.py                # Defaults, ranges, sizing, palette and feature flags
├── core/transformer.py      # Pure ideal-transformer calculation and classification
├── ui/theme.py              # Shared fonts and semantic color theme
├── ui/components.py         # Reusable buttons and numeric spin boxes
├── ui/screens.py            # Responsive dashboard, help overlay and results view
├── ui/transformer_view.py  # Pygame transformer schematic and live labels
└── controllers/
    ├── keyboard.py          # Reusable keyboard/mouse controller abstraction
    └── hardware.py          # Optional Pi GPIO buttons and ADS1115 knobs
```

## Configuration

Edit `config.py` to adjust the window dimensions, minimum resize size, FPS, numeric defaults/ranges/increments, display precision, color palette, font sizes, and feature flags. Important settings include:

- `FEATURE_SHOW_FLUX_ANIMATION`, `ANIMATION_ENABLED_DEFAULT`, and `ANIMATION_SPEED_DEFAULT` for flux visualization.
- `FPS` for presentation performance; it is set to 30 for the target Pi 4.
- `Vp_*`, `Np_*`, and `Ns_*` for safe input ranges, defaults, and step sizes.
- `COLOR_*`, font-size constants, `MIN_WINDOW_WIDTH`, and `MIN_WINDOW_HEIGHT` for visual customization.

## Scope and limitations

- The model uses the ideal equation only; it does not model losses, current, power, efficiency, magnetic saturation, temperature, waveform distortion, or physical-transformer safety behavior.
- Winding loops in the graphic are illustrative density cues, not literal turn counts.
- Physical controls change simulator inputs only; they do not measure or control transformer equipment.
- The simulation runs offline. Pygame provides the application shell and draws the transformer schematic.

## Physical controls (Raspberry Pi)

Hardware input is attempted by default. Keyboard and mouse remain active at the same time. GPIO inputs use internal pull-ups; connect each button between its GPIO and Pi GND. The 12 tactile buttons map to Vp, Np, and Ns adjustments (`+1`, `-1`, `+10`, `-10` per value). BCM GPIO 23 is the mode push button and BCM GPIO 24 is reset. The tactile buttons repeat while held. Pin assignments are in `HARDWARE_BUTTON_PINS` and `TACTILE_ACTIONS` in `config.py`.

| Button | BCM GPIO | Physical pin |
|---|---:|---:|
| Vp +1 / −1 / +10 / −10 | 4 / 17 / 27 / 22 | 7 / 11 / 13 / 15 |
| Np +1 / −1 / +10 / −10 | 10 / 9 / 11 / 5 | 19 / 21 / 23 / 29 |
| Ns +1 / −1 / +10 / −10 | 6 / 13 / 19 / 26 | 31 / 33 / 35 / 37 |
| Mode push button | 23 | 16 |
| Reset push button | 24 | 18 |

Two B50k potentiometers control turns through an ADS1115 at I2C address `0x48`: A0 controls `Np` and A1 controls `Ns`. Connect ADS VDD to Pi 3.3 V, GND to Pi GND, SDA/SCL to physical pins 3 and 5, and each potentiometer's wiper to its assigned ADS input. Connect each potentiometer's outer legs to 3.3 V and GND. Keep the wiper voltage within 0–3.3 V. The Raspberry Pi installer enables I2C; reboot after installation to activate the bus.

Install the hardware packages in the project's virtual environment, then launch normally:

```bash
.venv/bin/pip install -r requirements-hardware.txt
.venv/bin/python main.py
```

ADS1115 support and physical buttons are enabled by default. Set `ITLW_ADS=0` to disable the ADC, or `ITLW_HARDWARE=0` to disable physical controls. The controls panel shows hardware status; missing packages or devices leave the application running with keyboard and mouse input available.

To test the configured GPIO buttons by themselves, close the workbench and run:

```bash
.venv/bin/python scripts/test_buttons.py
```

The tester prints each configured BCM pin as `1` when released and `0` while pressed. Stop it with `Ctrl+C`. To inspect button presses alongside live ADS1115 voltage readings, run:

```bash
bash scripts/watch_hardware.sh
```

Press `Ctrl+C` to stop the monitor. It uses the same GPIO pin and ADS channel settings as the application.
