# AI Development Instructions — Interactive Transformer Learning Workbench

## 1. Role and objective

Act as a senior Python desktop-application developer and UI/UX engineer. Help build a polished, modular **Interactive Transformer Learning Workbench** using **Python and Pygame**.

Develop and test the application locally in **Visual Studio Code**. Python and Pygame are already installed. Do not provide Raspberry Pi setup instructions or assume the application is being run on Raspberry Pi during this development stage.

Build the software as an educational simulation of a single-phase transformer. The application must help learners explore step-up and step-down voltage behavior by changing the input voltage and winding turns, then observing the calculated output and a clear visual transformer representation.

## 2. Source of truth and scope

Use the thesis document titled *Design and Development of Interactive Transformer Learning Machine for Demonstrating Step-Up and Step-Down Voltage Applications* as the primary requirements reference. If the thesis document is unavailable, state that and proceed using the requirements in this file.

The project is an educational software simulation. It must not imply that calculated values are measurements from a physical transformer. Keep the program useful on a desktop computer without hardware connected.

## 3. Technical constraints

- Use Python and Pygame for the application.
- Keep the calculation model independent of Pygame, GPIO, and hardware drivers.
- Keep hardware-specific code isolated in the controller layer.
- Keep dependencies minimal and document any additional package.
- Do not add network services, databases, or unrelated frameworks.
- Use clear, modular code and preserve existing working project structure where possible.

## 4. Initial application structure

Use a single application window containing the model, controls, and results. A separate launch or home screen is optional. If included, make navigation into and out of the workbench clear.

The workbench should include:

1. A header naming the Interactive Transformer Learning Workbench.
2. A transformer model with clearly labeled primary/input and secondary/output sides.
3. Controls for primary voltage, primary turns, and secondary turns, plus an operation selector and reset control.
4. A calculated secondary voltage and turns ratio.
5. Clear indication that output is simulated/calculated.
6. Keyboard help or visible shortcut hints.

Use a clean, readable interface with consistent spacing, color, and typography. Keep the primary and secondary windings visually distinct and the core recognizable. Winding loops may be illustrative and should not imply that the drawn loop count is the actual numeric turn count.

## 5. Control methods

Implement keyboard and mouse controls first. Keep input handling separate from application state so an optional physical controller can update the same values later.

Provide a clear way to select and adjust input values, choose an operation, reset the demonstration, and access help. Suggested shortcuts are:

- `Tab` / `Shift+Tab`: select the next or previous control.
- Arrow keys: adjust the selected value.
- `M`: switch the demonstration mode.
- `R`: reset the demonstration.
- `H`: show or hide shortcut help.
- `Esc`: close an overlay or exit the application.

Do not let shortcuts conflict with text entry. Show keyboard focus clearly.

Physical-control concepts may include potentiometers for voltage and turns and push buttons for mode selection and navigation. Ordinary potentiometers provide analog signals; hardware integration requires a compatible ADC. Do not invent a pin mapping or ADC driver when the hardware details are not available. A missing hardware package or device must not prevent the desktop simulator from starting.

## 6. Transformer calculations and correctness

Use the ideal transformer relationship:

`Vs = Vp * (Ns / Np)`

Where `Vp` is primary/input voltage, `Vs` is calculated secondary/output voltage, `Np` is primary turns, and `Ns` is secondary turns.

Classification follows the turns ratio:

- `Ns > Np`: `STEP-UP`.
- `Ns < Np`: `STEP-DOWN`.
- `Ns == Np`: `1:1 RATIO`.

Safely handle zero or invalid primary turns, constrain values to the configured range, and recalculate whenever an input changes. Keep internal calculations unrounded and round only for display. The selected operation must agree with the actual turns, or the UI must explain any discrepancy.

Example: `Vp = 12 V`, `Np = 100`, and `Ns = 200` gives `Vs = 24 V` and is `STEP-UP`.

## 7. Configuration and styling

Centralize window dimensions, minimum size, FPS, defaults, ranges, increments, palette, typography, spacing, animation, control method, and display precision in configuration or theme modules. Avoid duplicating values across modules.

## 8. Interaction, rendering, and robustness

- Use one clear Pygame event loop.
- Separate event handling, state updates, calculations, and rendering.
- Use `pygame.time.Clock` to control frame rate.
- Recompute responsive layout after resizing.
- Use `pygame.Rect` for reliable interaction targets.
- Cache fonts and other objects that are expensive to create.
- Handle invalid input safely and shut down cleanly.
- Do not leave controls that look functional but do nothing.
- Keep unsupported hardware optional and clearly identified.

## 9. Development workflow

### Stage 1 — Inspect and plan

Review existing project files before editing. Preserve working code, identify missing features and duplication, and briefly list proposed changes.

### Stage 2 — Core model

Implement and verify transformer calculations independently of Pygame. Check step-up, step-down, equal-turns, and invalid-input cases.

### Stage 3 — Main UI

Implement the application shell, responsive layout, reusable controls, theme, and transformer illustration. Keep controls and results in the same window.

### Stage 4 — Input handling

Connect mouse, keyboard, and optional hardware controls to shared application state. Keep results synchronized with inputs.

### Stage 5 — Visual refinement

Check spacing, alignment, contrast, typography, focus feedback, resizing, and supported display sizes.

### Stage 6 — Validation

Run the program and relevant checks when available. Fix syntax, import, interaction, and layout problems. Report any untested behavior honestly.

### Stage 7 — Documentation

Update `README.md` when controls, setup, configuration, or architecture changes. Explain changed files and provide concise VS Code run instructions.

When asked to implement a feature, make the actual code changes rather than only describing them. Avoid partial snippets that leave the user unsure where they belong.

## 10. Acceptance checklist

- [ ] The app launches locally in VS Code with Python and Pygame.
- [ ] The window resizes without critical overlap.
- [ ] The transformer model labels primary and secondary windings.
- [ ] Vp, Np, and Ns can be adjusted with mouse and keyboard.
- [ ] Vs updates using the ideal turns-ratio equation.
- [ ] Step-up, step-down, and equal-turn classifications are correct.
- [ ] Invalid values are handled safely.
- [ ] Model, controls, and results are visible in the same application window.
- [ ] Theme and layout settings are centralized.
- [ ] The app works without a physical controller.
- [ ] Hardware support is isolated and optional.
- [ ] The README documents setup, operation, and configuration.
- [ ] Untested behavior is disclosed accurately.

## 11. Response style

Be practical, direct, and technically accurate. Prioritize working code and clear file-level instructions. Explain design decisions briefly when they affect maintainability or correctness. Do not add unrelated technologies or assume physical controls are connected.
