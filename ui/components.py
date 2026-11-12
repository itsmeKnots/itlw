"""Small reusable Pygame controls used by the simulator dashboard."""
from __future__ import annotations

from typing import Callable, Optional

import pygame
import config as cfg


class Button:
    def __init__(self, rect, text: str, on_click: Optional[Callable[[], None]] = None,
                 tooltip: str = "", tag: str | None = None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.tooltip = tooltip
        self.tag = tag
        self.hovered = self.pressed = self.focused = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = self.rect.collidepoint(event.pos)
            self.focused = self.pressed
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            clicked = self.pressed and self.rect.collidepoint(event.pos)
            self.pressed = False
            if clicked and self.on_click:
                self.on_click()
                return True
        return False

    def draw(self, surface, theme) -> None:
        colors = theme.colors
        fill = colors["button_pressed"] if self.pressed else (
            colors["button_hover"] if self.hovered or self.focused else colors["button"]
        )
        pygame.draw.rect(surface, fill, self.rect, border_radius=cfg.CORNER_RADIUS)
        pygame.draw.rect(
            surface, colors["focus"] if self.focused else colors["border"],
            self.rect, 2 if self.focused else 1, border_radius=cfg.CORNER_RADIUS,
        )
        label = theme.render_text(self.text, 12, bold=True)
        surface.blit(label, label.get_rect(center=self.rect.center))


class SpinBox:
    def __init__(self, rect, value, min_val, max_val, step, on_change,
                 tag: str, tooltip: str = ""):
        self.rect = pygame.Rect(rect)
        self.value, self.min_val, self.max_val, self.step = value, min_val, max_val, step
        self.on_change, self.tag, self.tooltip = on_change, tag, tooltip
        self.focused = self.hovered = False
        button_width = max(26, self.rect.height - 6)
        self.dec_rect = pygame.Rect(self.rect.left + 3, self.rect.top + 3, button_width, self.rect.height - 6)
        self.inc_rect = pygame.Rect(self.rect.right - button_width - 3, self.rect.top + 3, button_width, self.rect.height - 6)

    def adjust(self, direction: int) -> None:
        new_value = max(self.min_val, min(self.max_val, self.value + direction * self.step))
        if new_value != self.value:
            self.value = new_value
            self.on_change(self.value)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.focused = True
            if self.dec_rect.collidepoint(event.pos):
                self.adjust(-1)
            elif self.inc_rect.collidepoint(event.pos):
                self.adjust(1)
            return True
        return False

    def draw(self, surface, theme) -> None:
        colors = theme.colors
        pygame.draw.rect(surface, colors["input"], self.rect, border_radius=cfg.CORNER_RADIUS)
        pygame.draw.rect(surface, colors["focus"] if self.focused else colors["border"],
                         self.rect, 2 if self.focused else 1, border_radius=cfg.CORNER_RADIUS)
        for rect, symbol in ((self.dec_rect, "−"), (self.inc_rect, "+")):
            fill = colors["button_hover"] if rect.collidepoint(pygame.mouse.get_pos()) else colors["button"]
            pygame.draw.rect(surface, fill, rect, border_radius=2)
            pygame.draw.rect(surface, colors["border"], rect, 1, border_radius=2)
            mark = theme.render_text(symbol, 17, bold=True)
            surface.blit(mark, mark.get_rect(center=rect.center))
        value = f"{self.value:.1f}" if isinstance(self.value, float) else str(self.value)
        label = theme.render_text(value, 16, bold=True)
        surface.blit(label, label.get_rect(center=self.rect.center))
