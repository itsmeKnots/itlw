"""Power-menu state and overlay rendering, independent of OS commands."""
from __future__ import annotations

import math

import pygame

import config as cfg


class PowerMenu:
    """Track menu navigation, confirmation, and cancellable countdown state."""

    ENTRIES = (
        ("return_to_app", "Return to app"),
        ("restart_app", "Restart app"),
        ("exit_to_desktop", "Exit to desktop"),
        ("reboot", "Reboot"),
        ("poweroff", "Shut down"),
    )

    CLOSED = "closed"
    MENU = "menu"
    CONFIRM = "confirm"
    COUNTDOWN = "countdown"
    NOTICE = "notice"

    def __init__(self, countdown_seconds: float = 10.0):
        self.countdown_seconds = countdown_seconds
        self.state = self.CLOSED
        self.selection = 0
        self.remaining = 0.0
        self.pending_action: str | None = None
        self.disabled_reasons: dict[str, str] = {}
        self.message = ""

    @property
    def is_open(self) -> bool:
        return self.state != self.CLOSED

    @property
    def selected_action(self) -> str:
        return self.ENTRIES[self.selection][0]

    @property
    def selected_label(self) -> str:
        return self.ENTRIES[self.selection][1]

    def open(self) -> None:
        if self.state == self.CLOSED:
            self.state = self.MENU
            self.selection = 0
            self.remaining = 0.0
            self.pending_action = None
            self.message = ""

    def dismiss(self) -> None:
        self.state = self.CLOSED
        self.remaining = 0.0
        self.pending_action = None
        self.message = ""

    def set_availability(self, action: str, enabled: bool, reason: str = "") -> None:
        if enabled:
            self.disabled_reasons.pop(action, None)
        else:
            self.disabled_reasons[action] = reason

    def move_selection(self, direction: int) -> None:
        if self.state == self.MENU and direction:
            self.selection = (self.selection + direction) % len(self.ENTRIES)
            self.message = ""

    def activate(self) -> str | None:
        """Activate the selection, returning a non-destructive action intent."""
        if self.state == self.CONFIRM:
            if self.pending_action in {"restart_app", "exit_to_desktop"}:
                action = self.pending_action
                self.state = self.CLOSED
                self.pending_action = None
                return action
            self.state = self.COUNTDOWN
            self.remaining = self.countdown_seconds
            return None
        if self.state != self.MENU:
            return None

        action = self.selected_action
        if action in self.disabled_reasons:
            self.message = self.disabled_reasons[action]
            return None
        if action in {"restart_app", "exit_to_desktop", "reboot", "poweroff"}:
            self.pending_action = action
            self.state = self.CONFIRM
            return None
        self.state = self.CLOSED
        self.pending_action = None
        return action

    def tick(self, elapsed: float) -> str | None:
        """Advance the countdown and return the action intent when it expires."""
        if self.state not in {self.COUNTDOWN, self.NOTICE}:
            return None
        self.remaining = max(0.0, self.remaining - max(0.0, elapsed))
        if self.remaining > 0:
            return None
        if self.state == self.COUNTDOWN:
            self.state = self.NOTICE
            self.remaining = 2.0
            return None
        action = self.pending_action
        self.state = self.CLOSED
        self.pending_action = None
        return action

    def cancel(self) -> bool:
        """Back out one level; canceling from the menu returns to the app."""
        if self.state == self.CLOSED:
            return False
        if self.state in {self.CONFIRM, self.COUNTDOWN, self.NOTICE}:
            self.state = self.MENU
            self.remaining = 0.0
            self.pending_action = None
            self.message = ""
        else:
            self.state = self.CLOSED
            self.remaining = 0.0
            self.pending_action = None
        return True


def power_menu_layout(size, menu: PowerMenu):
    """Return actual-surface hit targets for the current menu state."""
    width, height = size
    if menu.state == PowerMenu.MENU:
        panel_height = min(360, height - 24)
    else:
        panel_height = min(280, height - 24)
    panel = pygame.Rect(0, 0, min(560, width - 24), panel_height)
    panel.center = (width // 2, height // 2)
    if menu.state == PowerMenu.MENU:
        rows = []
        for index in range(len(PowerMenu.ENTRIES)):
            rect = pygame.Rect(panel.left + 24, panel.top + 62 + index * 48,
                               panel.width - 48, 48)
            rows.append(rect)
        return panel, rows
    if menu.state == PowerMenu.CONFIRM:
        left = pygame.Rect(panel.centerx - 190, panel.bottom - 82, 180, 56)
        right = pygame.Rect(panel.centerx + 10, panel.bottom - 82, 180, 56)
        return panel, {"confirm": left, "cancel": right}
    if menu.state in {PowerMenu.COUNTDOWN, PowerMenu.NOTICE}:
        cancel = pygame.Rect(panel.centerx - 100, panel.bottom - 80, 200, 56)
        return panel, {"cancel": cancel}
    return panel, {}


def handle_power_menu_pointer(menu: PowerMenu, position, size) -> tuple[bool, str | None]:
    """Handle a pointer release on the menu; callers supply display coordinates."""
    panel, controls = power_menu_layout(size, menu)
    if menu.state == PowerMenu.MENU:
        for index, rect in enumerate(controls):
            if rect.collidepoint(position):
                menu.selection = index
                menu.message = ""
                return True, menu.activate()
    elif menu.state == PowerMenu.CONFIRM:
        if controls["confirm"].collidepoint(position):
            return True, menu.activate()
        if controls["cancel"].collidepoint(position):
            menu.cancel()
            return True, None
    elif menu.state in {PowerMenu.COUNTDOWN, PowerMenu.NOTICE}:
        if controls["cancel"].collidepoint(position):
            menu.cancel()
            return True, None
    if not panel.collidepoint(position):
        menu.cancel()
        return True, None
    return True, None


def countdown_message(action: str, remaining: float) -> str:
    seconds = max(1, math.ceil(remaining))
    action_label = "Shutdown" if action == "poweroff" else "Reboot"
    unit = "second" if seconds == 1 else "seconds"
    return f"{action_label} starts in {seconds} {unit}"


def power_button_rect(size, active_screen="workbench"):
    """Position a tappable Power control while preserving a 48-pixel target."""
    width, height = size
    if active_screen == "index":
        sx, sy = width / cfg.UI_INDEX_WIDTH, height / cfg.UI_INDEX_HEIGHT
        card = pygame.Rect(round(24 * sx), round(24 * sy), round(512 * sx), round(146 * sy))
        button_width, button_height = max(72, round(96 * sx)), max(52, round(52 * sy))
        return pygame.Rect(card.right - button_width - 10,
                           card.top + (card.height - button_height) // 2,
                           button_width, button_height)
    sx, sy = width / cfg.UI_WIDTH, height / cfg.UI_HEIGHT
    button_width, button_height = max(72, round(96 * sx)), max(52, round(52 * sy))
    return pygame.Rect(round(660 * sx), round(2 * sy), button_width, button_height)


def draw_power_button(surface, theme, active_screen="workbench") -> None:
    rect = power_button_rect(surface.get_size(), active_screen)
    pygame.draw.rect(surface, theme.colors["button"], rect, border_radius=cfg.CORNER_RADIUS)
    pygame.draw.rect(surface, theme.colors["border"], rect, 1,
                     border_radius=cfg.CORNER_RADIUS)
    image = theme.render_text("POWER", 13, theme.colors["text"], True)
    surface.blit(image, image.get_rect(center=rect.center))


def draw_power_menu(surface, theme, menu: PowerMenu) -> None:
    """Draw the power menu in the existing dimmed-overlay/card style."""
    if not menu.is_open:
        return
    width, height = surface.get_size()
    colors = theme.colors
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))

    panel, controls = power_menu_layout((width, height), menu)
    pygame.draw.rect(surface, colors["card"], panel, border_radius=10)
    pygame.draw.rect(surface, colors["border"], panel, 2, border_radius=10)

    def draw_text(text, y, size=18, bold=False):
        image = theme.render_text(text, size, colors["text"], bold)
        surface.blit(image, image.get_rect(center=(panel.centerx, y)))

    if menu.state == PowerMenu.MENU:
        draw_text("POWER MENU", panel.top + 35, 23, True)
        for index, (action, label) in enumerate(PowerMenu.ENTRIES):
            row = controls[index]
            y = row.centery
            disabled = action in menu.disabled_reasons
            if index == menu.selection:
                pygame.draw.rect(surface, colors["border"], row, border_radius=5)
            prefix = "▶  " if index == menu.selection else "    "
            color = colors["text_subtle"] if disabled else colors["text"]
            image = theme.render_text(prefix + label, 16, color, index == menu.selection)
            surface.blit(image, image.get_rect(center=(panel.centerx, y)))
        if menu.message:
            draw_text(menu.message, panel.bottom - 39, 11)
        draw_text("UP / DOWN SELECT     ENTER CHOOSE     ESC RETURN", panel.bottom - 18, 10)
    elif menu.state == PowerMenu.CONFIRM:
        draw_text(f"CONFIRM {menu.selected_label.upper()}?", panel.top + 58, 21, True)
        draw_text("Press Enter again, or choose below.", panel.top + 112, 15)
        for key, label in (("confirm", "CONFIRM"), ("cancel", "CANCEL")):
            rect = controls[key]
            pygame.draw.rect(surface, colors["button"], rect, border_radius=cfg.CORNER_RADIUS)
            pygame.draw.rect(surface, colors["border"], rect, 1,
                             border_radius=cfg.CORNER_RADIUS)
            image = theme.render_text(label, 14, colors["text"], True)
            surface.blit(image, image.get_rect(center=rect.center))
        draw_text("Esc: go back", panel.bottom - 14, 10)
    elif menu.state == PowerMenu.COUNTDOWN:
        message = countdown_message(menu.pending_action, menu.remaining)
        draw_text(message, panel.top + 68, 20, True)
        draw_text("Press Esc to cancel.", panel.top + 125, 15)
        rect = controls["cancel"]
        pygame.draw.rect(surface, colors["button"], rect, border_radius=cfg.CORNER_RADIUS)
        pygame.draw.rect(surface, colors["border"], rect, 1,
                         border_radius=cfg.CORNER_RADIUS)
        image = theme.render_text("CANCEL", 14, colors["text"], True)
        surface.blit(image, image.get_rect(center=rect.center))
    elif menu.state == PowerMenu.NOTICE:
        message = ("Wait until the screen turns off before unplugging"
                   if menu.pending_action == "poweroff" else "Restarting now")
        draw_text(message, panel.top + 74, 17, True)
        rect = controls["cancel"]
        pygame.draw.rect(surface, colors["button"], rect, border_radius=cfg.CORNER_RADIUS)
        pygame.draw.rect(surface, colors["border"], rect, 1,
                         border_radius=cfg.CORNER_RADIUS)
        image = theme.render_text("CANCEL", 14, colors["text"], True)
        surface.blit(image, image.get_rect(center=rect.center))
