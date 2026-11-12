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

The installer configures a user service and labwc to start the app after the graphical desktop provides its display. Enable desktop autologin in Raspberry Pi OS if the workbench should appear without a manual login. The launcher starts the workbench full-screen. To run in a resizable window instead, use `TRANSFORMER_FULLSCREEN=0 .venv/bin/python main.py`.

## Updating from the app screen

The small version label shows the app's current commit. In **manual** mode,
the app checks GitHub when it opens and about once an hour after that. Select
**Check for updates** (or press `U`) to check sooner. If a new version is
available, select **Update available - Install now** and confirm. The app will
show an updating screen, restart itself, and show a short success or rollback
message when it returns. If it says the previous version was restored, leave
the app running; the broken commit is skipped until a newer version is pushed.
If the Pi is offline or GitHub is temporarily unavailable, the check quietly
remains available to retry later.

With the configured hardware buttons, go to the launch page and press MODE
when an update is shown to open the confirmation. Press MODE again to install,
or RESET to choose Later. Touch and mouse use the on-screen controls.

The default policy is `manual`. The other policies are `auto`, where the
five-minute systemd timer installs updates without asking and the app only
shows the result, and `off`, where the timer and in-app update controls are
disabled. No terminal is needed to check or install in manual mode.

## Auto-update on Raspberry Pi

The labwc hook imports the display environment before starting the app's
user-level systemd service. In **auto** mode, `itlw-update.timer` checks
`origin/main` every five minutes. The updater fast-forwards only, reinstalls
each requirements file only if it changed, restarts the app, waits five
seconds, and checks that the service is active. On failure it restores the
previous commit and dependencies and records the failed commit outside the
repository so it will not be retried. A newer commit remains eligible.

The updater and app run as the logged-in desktop user; no sudoers rule or
root service is needed. Keep desktop autologin enabled for updates after
reboot. Lingering is disabled because the graphical app needs a desktop
display; in auto mode a timer run before the desktop is ready is deferred.

The updater and graphical app run as the logged-in desktop user; no sudoers
rule or root service is needed. Keep desktop autologin enabled if updates
should continue after reboot. The installer does not enable lingering: without
a desktop session the Pygame app has no display to use, and a lingering timer
could attempt a restart while that display is unavailable.

Install on the Pi (assuming user `itlw` and checkout `/home/itlw/itlw`):

```bash
cd /home/itlw
git clone --branch main https://github.com/itsmeKnots/itlw.git itlw
cd /home/itlw/itlw
cp .env.example .env  # optional; defaults to manual update mode
chmod 600 .env
bash scripts/install_raspberry_pi.sh
```

The installer enables I2C, installs system and Python dependencies, writes
the user units, and enables or disables the timer based on `ITLW_UPDATE_MODE`.
Reboot after installation to activate I2C for the ADS1115.
If the project is already cloned, skip `git clone` and use its checkout path.

Change mode by editing `ITLW_UPDATE_MODE` in `/home/itlw/itlw/.env`, then apply
the corresponding timer setting and restart the app service. Enable the timer
for `auto`; disable it for `manual` or `off`:

```bash
# Run this after setting ITLW_UPDATE_MODE=auto:
systemctl --user enable --now itlw-update.timer
systemctl --user restart itlw.service
```

After setting `ITLW_UPDATE_MODE=manual` or `off`:

```bash
systemctl --user disable --now itlw-update.timer
systemctl --user restart itlw.service
```

In `manual`, the screen provides checks and install confirmation. In `auto`,
the timer installs updates and the screen only shows its result. In `off`, the
screen hides update controls and the updater exits without fetching.

Check status and logs:

```bash
systemctl --user status itlw.service itlw-update.timer
systemctl --user list-timers itlw-update.timer
journalctl --user -t itlw-auto-update -n 100 --no-pager
journalctl --user -u itlw-update.service -n 100 --no-pager
journalctl --user -u itlw.service -n 100 --no-pager
```

Pause automatic checks or request an immediate update from the terminal for
maintenance:

```bash
systemctl --user stop itlw-update.timer
bash /home/itlw/itlw/scripts/update_from_github.sh
systemctl --user start itlw-update.timer
```

If a commit failed, its hash is stored at
`~/.local/state/itlw/bad-commit`. The updater skips only that exact hash.
Inspect or clear the skip record with:

```bash
cat ~/.local/state/itlw/bad-commit
rm ~/.local/state/itlw/bad-commit
```

To roll back manually, first pause updates and stop the app, then reset to the
chosen commit and restore dependencies before starting the app again:

```bash
systemctl --user stop itlw-update.timer itlw.service
cd /home/itlw/itlw
git log --oneline -n 20
git reset --hard <commit>
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-hardware.txt --no-build-isolation
.venv/bin/python -m pip install adafruit-blinka 'adafruit-circuitpython-ads1x15<3'
systemctl --user start itlw.service itlw-update.timer
```

### Recovering the Pi after a history rewrite

If the GitHub history is ever rewritten, the Pi's local branch may no longer
fast-forward. After confirming the rewritten `origin/main` is the intended
history, recover the checkout with:

```bash
cd /home/itlw/itlw && git fetch origin && git reset --hard origin/main
```

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
