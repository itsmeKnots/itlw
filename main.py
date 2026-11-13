import logging
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

import pygame

import config as cfg
from ui.theme import Theme, init_fonts
from ui.transformer_view import TransformerView
from ui.screens import AppState, IndexScreen, MainScreen
from ui.update_ui import UpdateUI
from controllers.hardware import get_hardware_controller
from update_check import UpdateManager


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


def draw_power_menu(surface, theme, selection, confirming):
    """Draw the Power Menu overlay."""
    width, height = surface.get_size()
    colors = theme.colors
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))
    panel = pygame.Rect(0, 0, 380, 220 if confirming else 280)
    panel.center = (width // 2, height // 2)
    pygame.draw.rect(surface, colors["card"], panel, border_radius=10)
    pygame.draw.rect(surface, colors["border"], panel, 2, border_radius=10)

    def draw_text(text, y, size=18, bold=False):
        image = theme.render_text(text, size, colors["text"], bold)
        surface.blit(image, image.get_rect(center=(panel.centerx, y)))

    if confirming:
        action = "SHUT DOWN" if selection == 0 else "REBOOT"
        draw_text("CONFIRM " + action, panel.top + 45, 21, True)
        draw_text("Press MODE again to confirm.", panel.top + 105, 14)
        draw_text("Press RESET to cancel.", panel.top + 140, 14)
        return
    draw_text("POWER MENU", panel.top + 38, 23, True)
    options = ["SHUT DOWN", "REBOOT", "CANCEL"]
    for index, option in enumerate(options):
        y = panel.top + 95 + index * 48
        if index == selection:
            item = pygame.Rect(panel.left + 35, y - 16, panel.width - 70, 36)
            pygame.draw.rect(surface, colors["border"], item, border_radius=5)
        image = theme.render_text(("▶  " if index == selection else "    ") + option,
                                 16, colors["text"], index == selection)
        surface.blit(image, image.get_rect(center=(panel.centerx, y)))
    draw_text("UP / DOWN SELECT     MODE CONFIRM", panel.bottom - 25, 10)


def execute_power_action(action, logger):
    """Request an operating-system shutdown or reboot."""
    try:
        subprocess.run(["/usr/bin/loginctl", action], check=True, timeout=10)
        return True
    except (OSError, subprocess.SubprocessError):
        logger.exception("Power operation failed: %s", action)
        return False


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

    power_menu_open = False
    power_menu_selection = 0
    power_menu_confirming = False
    combo_started_at = None
    combo_triggered = False
    power_menu_wait_for_release = False
    power_menu_release_started_at = None
    RELEASE_STABLE_MS = 200
    tactile_started = {}
    tactile_last_repeat = {}
    running = True
    last_time = pygame.time.get_ticks() / 1000.0

    while running:
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

            if power_menu_open:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if power_menu_confirming:
                            power_menu_confirming = False
                        else:
                            power_menu_open = False
                    elif event.key in (pygame.K_UP, pygame.K_DOWN):
                        if not power_menu_confirming:
                            direction = -1 if event.key == pygame.K_UP else 1
                            power_menu_selection = (power_menu_selection + direction) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if power_menu_confirming:
                            action = "poweroff" if power_menu_selection == 0 else "reboot"
                            if execute_power_action(action, logger):
                                running = False
                            else:
                                power_menu_confirming = False
                        elif power_menu_selection == 2:
                            power_menu_open = False
                        else:
                            power_menu_confirming = True
                continue

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                if getattr(cfg, "RESIZABLE", True):
                    size = (max(cfg.MIN_WINDOW_WIDTH, event.w), max(cfg.MIN_WINDOW_HEIGHT, event.h))
                    screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state.help_visible:
                        state.help_visible = False
                        continue
                    running = False
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
        mode_down = physical.get("btn_mode", False)
        reset_down = physical.get("btn_reset", False)
        update_snapshot = update_manager.snapshot
        # MODE and RESET now have dedicated push-button actions; do not use
        # their old long-press chord to open the power menu.
        combo_active = False
        if combo_active:
            if combo_started_at is None:
                combo_started_at = pygame.time.get_ticks()
            elif pygame.time.get_ticks() - combo_started_at >= 2000 and not combo_triggered:
                if not power_menu_open:
                    power_menu_open = True
                    power_menu_selection = 0
                    power_menu_confirming = False
                    power_menu_wait_for_release = True
                    power_menu_release_started_at = None
                combo_triggered = True
        else:
            combo_started_at = None

        if power_menu_open and update_snapshot.state != "updating":
            if power_menu_wait_for_release:
                if not mode_down and not reset_down:
                    if power_menu_release_started_at is None:
                        power_menu_release_started_at = pygame.time.get_ticks()
                    elif pygame.time.get_ticks() - power_menu_release_started_at >= RELEASE_STABLE_MS:
                        power_menu_wait_for_release = False
                        power_menu_release_started_at = None
                else:
                    power_menu_release_started_at = None
            else:
                if not power_menu_confirming:
                    if pressed("btn_up") or pressed("btn_inc"):
                        power_menu_selection = (power_menu_selection - 1) % 3
                    elif pressed("btn_down") or pressed("btn_dec"):
                        power_menu_selection = (power_menu_selection + 1) % 3
                elif pressed("btn_mode"):
                    action = "poweroff" if power_menu_selection == 0 else "reboot"
                    if execute_power_action(action, logger):
                        running = False
                    else:
                        power_menu_confirming = False
                if not power_menu_confirming and pressed("btn_mode"):
                    if power_menu_selection == 2:
                        power_menu_open = False
                    else:
                        power_menu_confirming = True
                if pressed("btn_reset"):
                    if power_menu_confirming:
                        power_menu_confirming = False
                    else:
                        power_menu_open = False

        elif not combo_active and update_snapshot.state != "updating":
            mode_handled = pressed("btn_mode") and update_ui.handle_hardware_button(
                "btn_mode", update_snapshot, state.active_screen
            )
            reset_handled = pressed("btn_reset") and update_ui.handle_hardware_button(
                "btn_reset", update_snapshot, state.active_screen
            )
            if mode_handled or reset_handled:
                pass
            elif state.active_screen == "index":
                # CHANGED (2/2): only the MODE button leaves the index,
                # not any of the 14 GPIO pins.
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

        if not mode_down and not reset_down:
            combo_triggered = False
        previous_hardware_inputs = physical
        active_screen = main_screen if state.active_screen == "workbench" else index_screen
        update_manager.poll_result()
        update_notice = update_manager.take_notice()
        if update_notice:
            update_ui.show_notice(update_notice)
        update_snapshot = update_manager.snapshot
        if active_screen is main_screen:
            active_screen.tick_hold()
            active_screen.draw(workbench_surface, state, dt)
            update_ui.draw(workbench_surface, update_snapshot, "workbench")
            blit_stretched(screen, workbench_surface)
        else:
            active_screen.draw(index_surface, state, dt)
            update_ui.draw(index_surface, update_snapshot, "index")
            blit_stretched(screen, index_surface)
        if (power_menu_open and update_snapshot.state != "updating"
                and not update_ui.confirming):
            draw_power_menu(screen, theme, power_menu_selection, power_menu_confirming)
        pygame.display.flip()
        clock.tick(cfg.FPS)

    transformer_view.close()
    hardware.close()
    update_manager.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    configure_logging()
    try:
        main()
    except Exception:
        logging.getLogger(__name__).exception("Application stopped because of an unhandled error")
        pygame.quit()
        raise
