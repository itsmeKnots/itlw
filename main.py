import logging
import signal
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

import pygame

import config as cfg
from ui.theme import Theme, init_fonts
from ui.transformer_view import TransformerView
from ui.screens import AppState, IndexScreen, MainScreen
from ui.update_ui import UpdateUI
from ui.power_menu import (
    PowerMenu, draw_power_menu, handle_power_menu_event,
    handle_power_menu_hardware, opens_power_menu_from_key, power_gesture_held,
)
from controllers.hardware import get_hardware_controller
from update_check import UpdateManager
from power_actions import PowerActions


def configure_logging():
    """Write application errors to a rotating log file beside the project."""
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "application.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    return logging.getLogger(__name__)


def blit_stretched(screen, surface):
    """Stretch a fixed-size UI surface over the whole screen."""
    size = screen.get_size()
    if size == surface.get_size():
        screen.blit(surface, (0, 0))
    else:
        screen.blit(pygame.transform.smoothscale(surface, size), (0, 0))


def scale_pointer_event(event, active_screen, screen_size, main_screen):
    """Translate pointer coordinates from the window into a reference surface."""
    if active_screen == "workbench":
        ref_w, ref_h = cfg.UI_WIDTH, cfg.UI_HEIGHT
    else:
        ref_w, ref_h = cfg.UI_INDEX_WIDTH, cfg.UI_INDEX_HEIGHT
    sx, sy = ref_w / screen_size[0], ref_h / screen_size[1]
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
        px, py = event.pos
        local = (px * sx, py * sy)
        if active_screen == "workbench":
            main_screen.pointer = local
        event = pygame.event.Event(event.type, {**event.dict, "pos": local})
    elif event.type == pygame.MOUSEWHEEL and active_screen == "workbench":
        px, py = pygame.mouse.get_pos()
        main_screen.pointer = (px * sx, py * sy)
    return event, (ref_w, ref_h)


def main():
    logger = logging.getLogger(__name__)
    pygame.init()
    init_fonts()
    flags = pygame.FULLSCREEN if cfg.FULLSCREEN else (pygame.RESIZABLE if cfg.RESIZABLE else 0)
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), flags)
    pygame.display.set_caption("Transformer Learning Workbench")
    clock = pygame.time.Clock()
    theme = Theme()
    transformer_view = TransformerView()
    state = AppState()
    index_screen = IndexScreen(theme)
    main_screen = MainScreen(theme, transformer_view)
    update_manager = UpdateManager(cfg.UPDATE_MODE, Path(__file__).resolve().parent)
    update_ui = UpdateUI(
        theme, cfg.UPDATE_MODE, update_manager.request_check, update_manager.request_update
    )
    update_manager.start()
    startup_notice = update_manager.take_notice()
    if startup_notice:
        update_ui.show_notice(startup_notice)
    workbench_surface = pygame.Surface((cfg.UI_WIDTH, cfg.UI_HEIGHT))
    index_surface = pygame.Surface((cfg.UI_INDEX_WIDTH, cfg.UI_INDEX_HEIGHT))
    hardware = get_hardware_controller()
    main_screen.hardware_status = hardware.get_status()
    # CHANGED (1/2): read the pins once at startup so a pin that is already
    # low is not treated as a fresh button press on the first frame.
    previous_hardware_inputs = hardware.read_inputs()

    power_menu = PowerMenu()
    power_actions = PowerActions(logger=logger)
    requested_action = None
    combo_started_at = None
    combo_latched = False
    power_menu_wait_for_release = False
    menu_button_baseline = {"btn_mode": False, "btn_reset": False}
    power_menu_opened_this_frame = False
    tactile_started = {}
    tactile_last_repeat = {}
    running = True
    termination_requested = {"value": False}
    previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM,
                  lambda _signum, _frame: termination_requested.__setitem__("value", True))
    last_time = pygame.time.get_ticks() / 1000.0

    def open_power_menu(snapshot):
        nonlocal power_menu_opened_this_frame
        if snapshot.state == "updating" or update_ui.confirming:
            return False
        for action in ("restart_app", "reboot", "poweroff"):
            allowed, reason = power_actions.availability(action)
            power_menu.set_availability(action, allowed, reason)
        was_open = power_menu.is_open
        power_menu.open()
        if not was_open and power_menu.is_open:
            power_menu_opened_this_frame = True
        return power_menu.is_open

    def handle_power_key(key):
        nonlocal requested_action
        action = handle_power_menu_event(
            power_menu, pygame.event.Event(pygame.KEYDOWN, key=key)
        )
        if action and action != "return_to_app":
            requested_action = action

    while running:
        if termination_requested["value"]:
            running = False
            break
        current_time = pygame.time.get_ticks() / 1000.0
        dt = current_time - last_time
        last_time = current_time
        update_manager.poll_result()
        update_notice = update_manager.take_notice()
        if update_notice:
            update_ui.show_notice(update_notice)

        for event in pygame.event.get():
            update_snapshot = update_manager.snapshot
            if update_snapshot.state == "updating" or update_ui.confirming:
                event, surface_size = scale_pointer_event(
                    event, state.active_screen, screen.get_size(), main_screen
                )
                update_ui.handle_event(event, update_snapshot, surface_size, state.active_screen)
                continue

            if power_menu.is_open:
                if event.type == pygame.KEYDOWN:
                    handle_power_key(event.key)
                continue

            if event.type == pygame.QUIT:
                # The menu is intentionally keyboard and hardware controlled.
                continue
            elif event.type == pygame.VIDEORESIZE:
                if getattr(cfg, "RESIZABLE", True):
                    size = (max(cfg.MIN_WINDOW_WIDTH, event.w), max(cfg.MIN_WINDOW_HEIGHT, event.h))
                    screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state.help_visible:
                        state.help_visible = False
                        continue
                    if opens_power_menu_from_key(event.key):
                        open_power_menu(update_snapshot)
                        continue
                elif opens_power_menu_from_key(event.key):
                    open_power_menu(update_snapshot)
                    continue
                elif state.active_screen == "workbench" and event.key == pygame.K_r:
                    main_screen._reset(state)
                elif state.active_screen == "workbench" and event.key == pygame.K_m:
                    main_screen._toggle_mode(state)
                elif state.active_screen == "workbench" and event.key == pygame.K_a:
                    state.animation_enabled = not state.animation_enabled

            try:
                on_workbench = state.active_screen == "workbench"
                active_screen = main_screen if on_workbench else index_screen
                event, surface_size = scale_pointer_event(
                    event, state.active_screen, screen.get_size(), main_screen
                )
                if update_ui.handle_event(event, update_manager.snapshot, surface_size,
                                         state.active_screen):
                    continue
                active_screen.handle_event(event, state)
            except Exception:
                logger.exception("Unhandled error while processing event: %r", event)

        physical = hardware.read_inputs()
        hardware_status = hardware.get_status()
        if main_screen.hardware_status != hardware_status:
            main_screen.hardware_status = hardware_status
        pressed = lambda name: physical.get(name, False) and not previous_hardware_inputs.get(name, False)
        update_snapshot = update_manager.snapshot
        update_blocked = update_snapshot.state == "updating" or update_ui.confirming
        if update_blocked:
            power_menu.dismiss()
            combo_started_at = None
            requested_action = None
        elif power_menu.state in {PowerMenu.COUNTDOWN, PowerMenu.NOTICE}:
            action = power_menu.tick(dt)
            if action:
                requested_action = action

        vp_combo_down = (physical.get("vp_plus_10", False)
                         and physical.get("vp_minus_10", False))
        if not update_blocked and not power_menu.is_open:
            if vp_combo_down:
                if combo_started_at is None and not combo_latched:
                    combo_started_at = pygame.time.get_ticks()
                if (combo_started_at is not None and not combo_latched
                        and power_gesture_held(physical, pygame.time.get_ticks() - combo_started_at)):
                    if open_power_menu(update_snapshot):
                        combo_latched = True
                        power_menu_wait_for_release = True
                        menu_button_baseline = {
                            "btn_mode": physical.get("btn_mode", False),
                            "btn_reset": physical.get("btn_reset", False),
                        }
            else:
                combo_started_at = None
                combo_latched = False

        if power_menu.is_open and not update_blocked:
            if power_menu_opened_this_frame:
                menu_button_baseline = {
                    "btn_mode": physical.get("btn_mode", False),
                    "btn_reset": physical.get("btn_reset", False),
                }
                power_menu_opened_this_frame = False
            elif power_menu_wait_for_release:
                menu_button_baseline = {
                    "btn_mode": physical.get("btn_mode", False),
                    "btn_reset": physical.get("btn_reset", False),
                }
                if not physical.get("vp_plus_10", False) and not physical.get("vp_minus_10", False):
                    power_menu_wait_for_release = False
            else:
                if pressed("vp_plus_1"):
                    handle_power_menu_hardware(power_menu, "vp_plus_1")
                elif pressed("vp_minus_1"):
                    handle_power_menu_hardware(power_menu, "vp_minus_1")
                reset_changed = (physical.get("btn_reset", False)
                                 != menu_button_baseline["btn_reset"])
                mode_changed = (physical.get("btn_mode", False)
                                != menu_button_baseline["btn_mode"])
                if reset_changed:
                    handle_power_menu_hardware(power_menu, "btn_reset")
                elif mode_changed:
                    action = handle_power_menu_hardware(power_menu, "btn_mode")
                    if action and action != "return_to_app":
                        requested_action = action
                menu_button_baseline = {
                    "btn_mode": physical.get("btn_mode", False),
                    "btn_reset": physical.get("btn_reset", False),
                }

        elif not update_blocked and not power_menu.is_open:
            if state.active_screen == "index":
                if pressed("btn_mode"):
                    state.active_screen = "workbench"
            elif state.active_screen == "workbench":
                if pressed("btn_mode"):
                    main_screen._toggle_mode(state)
                if pressed("btn_reset"):
                    main_screen._reset(state)
                if pressed("btn_inc") or pressed("btn_up"):
                    main_screen._adjust_selected(state, 1)
                if pressed("btn_dec") or pressed("btn_down"):
                    main_screen._adjust_selected(state, -1)

                now_ms = pygame.time.get_ticks()
                for name, (key, delta) in cfg.TACTILE_ACTIONS.items():
                    if name in {"vp_plus_10", "vp_minus_10"} and vp_combo_down:
                        tactile_started.pop(name, None)
                        tactile_last_repeat.pop(name, None)
                        continue
                    down = physical.get(name, False)
                    if pressed(name):
                        main_screen.nudge(state, key, delta)
                        tactile_started[name] = now_ms
                        tactile_last_repeat[name] = now_ms
                    elif down and name in tactile_started:
                        held_ms = now_ms - tactile_started[name]
                        interval = (cfg.HARDWARE_REPEAT_FAST_INTERVAL if held_ms >= 1500
                                    else cfg.HARDWARE_REPEAT_INTERVAL)
                        if held_ms >= cfg.HARDWARE_REPEAT_DELAY * 1000 and now_ms - tactile_last_repeat[name] >= interval * 1000:
                            main_screen.nudge(state, key, delta)
                            tactile_last_repeat[name] = now_ms
                    elif not down:
                        tactile_started.pop(name, None)
                        tactile_last_repeat.pop(name, None)
                main_screen.apply_hardware_knobs(state, physical)

        previous_hardware_inputs = physical
        power_menu_opened_this_frame = False
        active_screen = main_screen if state.active_screen == "workbench" else index_screen
        update_manager.poll_result()
        update_notice = update_manager.take_notice()
        if update_notice:
            update_ui.show_notice(update_notice)
        update_snapshot = update_manager.snapshot
        update_blocked = update_snapshot.state == "updating" or update_ui.confirming
        if update_blocked:
            power_menu.dismiss()
            requested_action = None
        if active_screen is main_screen:
            active_screen.tick_hold()
            active_screen.draw(workbench_surface, state, dt)
            update_ui.draw(workbench_surface, update_snapshot, "workbench")
            blit_stretched(screen, workbench_surface)
        else:
            active_screen.draw(index_surface, state, dt)
            update_ui.draw(index_surface, update_snapshot, "index")
            blit_stretched(screen, index_surface)
        if not update_blocked:
            if power_menu.is_open:
                draw_power_menu(screen, theme, power_menu)
        pygame.display.flip()
        if requested_action or termination_requested["value"]:
            running = False
        clock.tick(cfg.FPS)

    update_manager.stop()
    hardware.stop(timeout=2.0)
    hardware.close()
    transformer_view.close()
    pygame.quit()
    signal.signal(signal.SIGTERM, previous_sigterm_handler)

    if requested_action in {"restart_app", "reboot", "poweroff"}:
        if not power_actions.execute(requested_action):
            logger.error("Could not complete requested power action: %s", requested_action)
    return 0


if __name__ == "__main__":
    configure_logging()
    try:
        raise SystemExit(main())
    except Exception:
        logging.getLogger(__name__).exception("Application stopped because of an unhandled error")
        pygame.quit()
        raise
