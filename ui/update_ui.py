"""Compact update controls shared by the launch page and workbench."""
from __future__ import annotations

import time

import pygame

import config as cfg
from ui.header_layout import layout_header


class UpdateUI:
    def __init__(self, theme, mode: str, request_check, request_update):
        self.theme = theme
        self.mode = mode
        self.request_check = request_check
        self.request_update = request_update
        self.confirming = False
        self.selected_action = 0  # Install is the default keyboard/button action.
        self.notice = ""
        self.notice_until = 0.0

    def action_rects(self, size, active_screen="workbench", snapshot=None):
        width, height = size
        snapshot = snapshot or type("Snapshot", (), {"local_hash": "-------", "state": "idle"})()
        layout = layout_header(self.theme, size, active_screen,
                               f"v{snapshot.local_hash or '-------'}", self._label(snapshot))
        trigger = layout.update.rect
        return {
            "trigger": trigger,
            "install": pygame.Rect(width // 2 - 180, height // 2 + 35, 160, 46),
            "later": pygame.Rect(width // 2 + 20, height // 2 + 35, 160, 46),
        }

    @staticmethod
    def _label(snapshot):
        return {
            "update_available": "UPDATE AVAILABLE - INSTALL NOW",
            "checking": "CHECKING FOR UPDATES...",
            "updating": "UPDATING...",
        }.get(snapshot.state, "CHECK FOR UPDATES [U]")

    def show_notice(self, message: str, duration: float = 5.0) -> None:
        self.notice = message
        self.notice_until = time.monotonic() + duration

    def handle_event(self, event, snapshot, surface_size, active_screen="workbench") -> bool:
        """Handle an input event and return whether it belongs to update UI."""
        if self.mode != "manual":
            return False
        if snapshot.state == "updating":
            return True
        if self.confirming:
            return self._handle_confirmation(event, surface_size)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_u:
            if snapshot.state == "update_available":
                self.confirming = True
            else:
                self.request_check()
            return True
        layout = layout_header(self.theme, surface_size, active_screen,
                               "", self._label(snapshot), f"v{snapshot.local_hash or '-------'}")
        rects = self.action_rects(surface_size, active_screen, snapshot)
        rects["trigger"] = layout.update.rect
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return rects["trigger"].collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if rects["trigger"].collidepoint(event.pos):
                if snapshot.state == "update_available":
                    self.confirming = True
                else:
                    self.request_check()
                return True
        return False

    def _handle_confirmation(self, event, surface_size) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._choose(1)
            elif event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                self.selected_action = 1 - self.selected_action
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._choose(self.selected_action)
            return True
        # Keep the modal exclusive while it is open; only its keyboard
        # controls can choose Install or Later.
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                          pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            return True
        return False

    def _choose(self, action: int) -> None:
        self.confirming = False
        if action == 0:
            self.request_update()

    def handle_hardware_button(self, button: str, snapshot, active_screen: str) -> bool:
        if self.mode != "manual":
            return False
        if snapshot.state == "updating" or self.confirming:
            return True
        return False

    def draw(self, surface, snapshot, active_screen="workbench") -> None:
        if self.mode == "off":
            return
        width, height = surface.get_size()
        colors = self.theme.colors
        local = snapshot.local_hash or "-------"
        status_text = f"v{local}"
        layout = layout_header(self.theme, (width, height), active_screen,
                               "Press Esc for power menu",
                               self._label(snapshot) if self.mode == "manual" else None,
                               status_text)
        self._text(surface, layout.status.text, layout.status.rect.topleft,
                   layout.status.font_size, colors["text_subtle"], True)
        if layout.version:
            self._text(surface, layout.version.text, layout.version.rect.topleft,
                       layout.version.font_size, colors["text_subtle"], True)

        if self.mode == "manual":
            label = self._label(snapshot)
            rect = layout.update.rect
            active = snapshot.state == "update_available"
            fill = cfg.COLOR_ACCENT_PRIMARY if active else colors["button"]
            fg = (255, 255, 255) if active else colors["text"]
            pygame.draw.rect(surface, fill, rect, border_radius=cfg.CORNER_RADIUS)
            pygame.draw.rect(surface, colors["border"], rect, 1, border_radius=cfg.CORNER_RADIUS)
            image = self.theme.render_text(layout.update.text, layout.update.font_size, fg, True)
            surface.blit(image, image.get_rect(center=rect.center))

        if snapshot.state == "updating":
            self._draw_updating(surface)
        elif self.confirming:
            self._draw_confirmation(surface, snapshot)
        elif self.notice and time.monotonic() < self.notice_until:
            self._draw_notice(surface, self.notice)
        elif time.monotonic() >= self.notice_until:
            self.notice = ""

    def _text(self, surface, text, position, size, color, bold=False, anchor="topleft"):
        image = self.theme.render_text(text, size, color, bold)
        rect = image.get_rect()
        setattr(rect, anchor, position)
        surface.blit(image, rect)

    def _draw_confirmation(self, surface, snapshot) -> None:
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, min(560, width - 32), 250)
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(surface, self.theme.colors["card"], panel, border_radius=8)
        pygame.draw.rect(surface, self.theme.colors["border"], panel, 2, border_radius=8)
        self._text(surface, "Install update? The app will restart.",
                   (panel.centerx, panel.top + 58), 20, self.theme.colors["text"], True, "midtop")
        self._text(surface, "The simulator will close briefly and reopen automatically.",
                   (panel.centerx, panel.top + 101), 13,
                   self.theme.colors["text_subtle"], False, "midtop")
        if snapshot.remote_message:
            message = snapshot.remote_message.replace("\n", " ")[:72]
            self._text(surface, message, (panel.centerx, panel.top + 123), 12,
                       self.theme.colors["text_subtle"], False, "midtop")
        rects = self.action_rects((width, height), active_screen, snapshot)
        for index, (name, label) in enumerate((("install", "INSTALL"), ("later", "LATER"))):
            rect = rects[name]
            selected = index == self.selected_action
            fill = cfg.COLOR_ACCENT_PRIMARY if selected else self.theme.colors["button"]
            color = (255, 255, 255) if selected else self.theme.colors["text"]
            pygame.draw.rect(surface, fill, rect, border_radius=cfg.CORNER_RADIUS)
            pygame.draw.rect(surface, self.theme.colors["border"], rect, 1, border_radius=cfg.CORNER_RADIUS)
            image = self.theme.render_text(label, 14, color, True)
            surface.blit(image, image.get_rect(center=rect.center))
        self._text(surface, "Enter: choose   Tab: switch   Esc: later",
                   (panel.centerx, panel.bottom - 18), 11,
                   self.theme.colors["text_subtle"], False, "midbottom")

    def _draw_updating(self, surface) -> None:
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))
        self._text(surface, "Updating, please wait...", (width // 2, height // 2),
                   30, (255, 255, 255), True, "center")

    def _draw_notice(self, surface, message: str) -> None:
        width, height = surface.get_size()
        image = self.theme.render_text(message, 15, (255, 255, 255), True)
        panel = image.get_rect(center=(width // 2, height - 28)).inflate(34, 18)
        pygame.draw.rect(surface, (40, 40, 40), panel, border_radius=4)
        surface.blit(image, image.get_rect(center=panel.center))
