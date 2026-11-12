"""Shared colors, fonts, and drawing helpers for the Pygame interface."""
from __future__ import annotations

import pygame
import config as cfg

_FONT_CACHE = {}


def init_fonts():
    pygame.font.init()
    _FONT_CACHE.clear()


class Theme:
    def __init__(self):
        self.colors = {
            "bg": cfg.COLOR_BACKGROUND,
            "card": cfg.COLOR_CARD,
            "surface": cfg.COLOR_CARD,
            "accent_primary": cfg.COLOR_ACCENT_PRIMARY,
            "accent_secondary": cfg.COLOR_ACCENT_SECONDARY,
            "core": cfg.COLOR_CORE,
            "flux": cfg.COLOR_FLUX,
            "text": cfg.COLOR_TEXT,
            "text_subtle": cfg.COLOR_TEXT_SUBTLE,
            "border": cfg.COLOR_BORDER,
            "button": cfg.COLOR_CARD,
            "button_hover": cfg.COLOR_BUTTON_HOVER,
            "button_pressed": cfg.COLOR_BUTTON_PRESSED,
            "input": cfg.COLOR_CARD,
            "result": (250, 250, 250),
            "simulation": (18, 18, 18),
            "focus": (18, 18, 18),
            "success": (18, 18, 18),
            "warning": (18, 18, 18),
            "danger": (18, 18, 18),
        }

    def get_font(self, size, bold=False, italic=False):
        key = (int(size), bool(bold), bool(italic))
        if key not in _FONT_CACHE:
            _FONT_CACHE[key] = pygame.font.SysFont(cfg.FONT_FAMILY, key[0], bold=key[1], italic=key[2])
        return _FONT_CACHE[key]

    def render_text(self, text, size, color=None, bold=False, italic=False, antialias=True):
        return self.get_font(size, bold, italic).render(
            str(text), antialias, color or self.colors["text"]
        )


def draw_rounded_rect(surface, color, rect, radius=None, border_width=0, border_color=None):
    radius = cfg.CORNER_RADIUS if radius is None else radius
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_width and border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


def draw_aa_line(surface, color, start_pos, end_pos, width=1):
    pygame.draw.aaline(surface, color, start_pos, end_pos)
    if width > 1:
        pygame.draw.line(surface, color, start_pos, end_pos, width)
