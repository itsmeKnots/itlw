# Interactive Transformer Learning Workbench: Project Execution Phases

This document details the complete, step-by-step implementation plan for building the **Interactive Transformer Learning Workbench**. It spans from initial setup and core mathematical modeling to visual UI development, interactive controls, refinement, and future hardware compatibility.

---

## Phase 1: Environment Setup & Project Architecture
**Objective:** Establish project workspace structure, initial configuration parameters, and clean dependency management.

* **Task 1.1: Project Structure Creation**
  * Create folder structure according to modular design requirements:
    ```text
    transformer_workbench/
    ├── main.py
    ├── config.py
    ├── requirements.txt
    ├── README.md
    ├── core/
    │   ├── __init__.py
    │   └── transformer.py
    ├── ui/
    │   ├── __init__.py
    │   ├── theme.py
    │   ├── components.py
    │   ├── screens.py
    │   └── transformer_view.py
    ├── controllers/
    │   ├── __init__.py
    │   ├── keyboard.py
    │   └── hardware.py
    └── assets/
        └── fonts/
    ```

* **Task 1.2: Centralized Configuration (`config.py`)**
  * Set default window parameters (`WINDOW_WIDTH = 1280`, `WINDOW_HEIGHT = 720`, `FPS = 60`, `RESIZABLE = True`).
  * Define physical parameter limits and defaults:
    * Primary Voltage $V_p$: default `12.0V`, range `[1.0V, 240.0V]`, step `1.0V` or `5.0V`.
    * Primary Turns $N_p$: default `100`, range `[10, 1000]`, step `10`.
    * Secondary Turns $N_s$: default `200`, range `[10, 1000]`, step `10`.
    * Simulated Frequency $f$: default `60Hz`, options `[50Hz, 60Hz]`.
  * Set default theme palette, font sizes, corner radii, padding, and feature flags.

* **Task 1.3: Dependency Definition (`requirements.txt`)**
  * Define minimalist dependencies: `pygame>=2.5.0`.

---

## Phase 2: Pure Core Logic & Calculation Engine
**Objective:** Implement and validate pure Python logic for ideal transformer equations with zero Pygame or GUI dependencies.

* **Task 2.1: Implement Ideal Transformer Logic (`core/transformer.py`)**
  * Implement formula for secondary voltage calculation:
    $$V_s = V_p \times \left(\frac{N_s}{N_p}\right)$$
  * Implement turns ratio calculation:
    $$\text{Ratio} = \frac{N_s}{N_p}$$
  * Implement classification functions:
    * `STEP-UP` if $N_s > N_p$ ($V_s > V_p$)
    * `STEP-DOWN` if $N_s < N_p$ ($V_s < V_p$)
    * `1:1 RATIO` if $N_s == N_p$ ($V_s == V_p$)
  * Add error handling and range clamping (prevent $N_p \le 0$ division-by-zero errors).
  * Structure input/output using dataclasses or typed dictionaries (`TransformerState`, `TransformerResult`).

* **Task 2.2: Standalone Verification & Unit Tests**
  * Verify calculation output for key benchmark cases:
    * $V_p = 12\text{V}, N_p = 100, N_s = 200 \implies V_s = 24\text{V}$ (Step-Up)
    * $V_p = 120\text{V}, N_p = 500, N_s = 50 \implies V_s = 12\text{V}$ (Step-Down)
    * $V_p = 220\text{V}, N_p = 100, N_s = 100 \implies V_s = 220\text{V}$ (1:1 Ratio)

---

## Phase 3: Theme Design & UI Component Toolkit
**Objective:** Create shared styles and reusable UI components in Pygame for intuitive interaction.

* **Task 3.1: Theme Helper (`ui/theme.py`)**
  * Define color constants (Dark technical theme: primary background, card fill, accent colors for primary/secondary windings, core color, flux animation color, high-contrast text).
  * Helper functions for rounded rectangles, anti-aliased lines, text rendering caching, and borders.

* **Task 3.2: Reusable UI Component Toolkit (`ui/components.py`)**
  * **Buttons:** Standard click handling, hover/active visual feedback states, keyboard focus highlights.
  * **Value Adjuster / Spinbox:** Numeric input control with `+` and `-` buttons.
  * **Sliders / Knobs:** Interactive mouse-draggable controls for adjusting continuous/discrete numerical values.
  * **Info Cards & Badges:** Styled container containers for displaying numerical readings ($V_p, V_s, N_p, N_s$, Turns Ratio) and operation status badges (`STEP-UP`, `STEP-DOWN`, `1:1`).

---

## Phase 4: Transformer Visualization Engine
**Objective:** Develop the core interactive visual graphic representing the digital transformer, coils, magnetic flux, and terminal connections.

* **Task 4.1: Schematic Core & Coil Rendering (`ui/transformer_view.py`)**
  * Render central laminated iron core using Pygame primitive drawing shapes.
  * Render Primary Winding coil on the left side ($N_p$).
  * Render Secondary Winding coil on the right side ($N_s$).
  * Dynamically adjust coil visual density or loop indication based on relative $N_p$ and $N_s$ values.
  * Add labels for Primary Input Terminals and Secondary Output Terminals.

* **Task 4.2: Dynamic Magnetic Flux Visualization**
  * Implement an animated particle or dashed loop path inside the core representing magnetic flux ($\Phi$).
  * Animate flux motion along the core driven by the simulated AC frequency ($f$).
  * Ensure animation can be toggled on/off or adjusted via config settings.

---

## Phase 5: Screen Layout & Application Main Loop
**Objective:** Assemble the main dashboard screen composition and wire up the event loop in `main.py`.

* **Task 5.1: Main Dashboard Layout (`ui/screens.py`)**
  * **Header Area:** Application title, short educational description, status badge (`SIMULATION MODE`).
  * **Center Left Panel:** Interactive transformer graphic (`transformer_view`).
  * **Center Right Panel:** Input controls ($V_p$ slider/spinbox, $N_p$ knob/spinbox, $N_s$ knob/spinbox, preset mode switches).
  * **Bottom Results Banner:** Output display ($V_s$, Turns Ratio, Operating Mode, simulated $f$, explanatory text note).
  * Ensure layout dynamically recalculates bounds when window resizing occurs.

* **Task 5.2: Application Lifecycle & Event Loop (`main.py`)**
  * Initialize Pygame modules and establish display window.
  * Run main loop: Event capture $\rightarrow$ Controller State Update $\rightarrow$ Core Physics Recalculation $\rightarrow$ UI Rendering $\rightarrow$ Frame rate lock (`clock.tick(60)`).
  * Ensure clean shutdown on window close (`QUIT`) or key triggers (`ESC`).

---

## Phase 6: Interactive Controllers & Input Binding
**Objective:** Implement keyboard shortcuts, mouse interaction drivers, and isolate the physical hardware controller interface.

* **Task 6.1: Keyboard & Mouse Control (`controllers/keyboard.py`)**
  * Implement mouse click targeting, drag gestures, and hover detection using `pygame.Rect`.
  * Keyboard navigation bindings:
    * `Tab` / `Shift+Tab`: Cycle active focus across parameter controls.
    * `Up Arrow` / `Right Arrow`: Increment focused parameter value.
    * `Down Arrow` / `Left Arrow`: Decrement focused parameter value.
    * `M`: Toggle demonstration presets (e.g. forced Step-Up vs Step-Down preset turns).
    * `R`: Reset to default parameters ($12\text{V}, N_p=100, N_s=200$).
    * `H`: Open/Close Help Overlay.

* **Task 6.2: Isolated Hardware Interface Placeholder (`controllers/hardware.py`)**
  * Design an abstract `HardwareController` class.
  * Provide stub methods for analog knob inputs (potentiometers) and digital push buttons.
  * Explicitly isolate GPIO/ADC libraries behind feature flag checks to prevent failure on generic desktop systems without attached hardware.
  * Clearly display "Hardware Disconnected" status in the interface options.

---

## Phase 7: Visual Refinement, Testing & Documentation
**Objective:** Perform system evaluation, fix layout bugs, verify safety/correctness, and write complete execution documentation.

* **Task 7.1: Visual Refinement & Usability Polish**
  * Ensure high contrast for screen readability in laboratory settings.
  * Add instructional tooltips and keyboard shortcut legends (`Press H for Help`).
  * Implement an explicit visual distinction clarifying that output readings are **Simulated / Calculated Ideal Values** and not live physical meter measurements.

* **Task 7.2: Verification Checklist**
  * [x] Verify program launches smoothly in desktop VS Code environment.
  * [x] Test responsive resizing without layout overlap or UI breakdown.
  * [x] Confirm $V_s$ calculations match ideal turns ratio formula across various scenarios.
  * [x] Ensure correct operational mode classification (`STEP-UP`, `STEP-DOWN`, `1:1`).
  * [x] Verify zero or negative turn inputs are safely handled/clamped.

* **Task 7.3: Project Documentation (`README.md`)**
  * Write clear execution guide (Setup, execution in VS Code via standard Python).
  * Document key bindings, interface architecture, configuration flags, and current project scope limitations.
