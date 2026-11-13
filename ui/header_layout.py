"""Shared, measured layout for the dashboard and workbench headers."""
from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class HeaderItem:
    text: str
    rect: pygame.Rect
    font_size: int
    bold: bool = False


@dataclass(frozen=True)
class HeaderLayout:
    title: HeaderItem
    status: HeaderItem
    version: HeaderItem | None
    update: HeaderItem | None


def _fit_text(theme, text, max_width, size, bold):
    """Return measured text, its image, and a font size that fits."""
    candidate = text
    for font_size in (size, size - 1):
        image = theme.render_text(candidate, font_size, bold=bold)
        if image.get_width() <= max_width:
            return candidate, image, font_size
        while candidate and image.get_width() > max_width:
            candidate = candidate[:-2].rstrip() + "…"
            image = theme.render_text(candidate, font_size, bold=bold)
    return candidate, image, max(1, size - 1)


def layout_header(theme, size, screen_name, status_text, update_text=None, version_text=None):
    """Lay out header content in a 12px gap row with 16px edge padding."""
    width, height = size
    scale = width / 1240
    # Reference surfaces are scaled down to the 900 px minimum window.
    # These source-space values leave at least 16/12 display px there.
    edge = max(22, round(22 * scale))
    gap = max(17, round(17 * scale))
    header_height = max(48, round(56 * scale))
    right = width - edge
    update = None
    status_width = theme.render_text(status_text, 10, bold=True).get_width()
    if update_text:
        # Reserve a practical control width before fitting; the text itself
        # shrinks inside the measured clickable rectangle.
        update_width = min(max(170, round(270 * scale)), max(1, right - edge - status_width - gap))
        text, image, font = _fit_text(theme, update_text, update_width - 16, 11, True)
        update_rect = pygame.Rect(right - update_width, 0, update_width, 36)
        update_rect.centery = header_height // 2
        update = HeaderItem(text, update_rect, font, True)
        right = update_rect.left - gap
    version = None
    if version_text:
        text, image, font = _fit_text(theme, version_text, max(1, right - edge), 10, True)
        version_rect = image.get_rect(top=(header_height - image.get_height()) // 2, right=right)
        version = HeaderItem(text, version_rect, font, True)
        right = version_rect.left - gap
    status, image, font = _fit_text(theme, status_text, max(1, right - edge), 10, True)
    status_rect = image.get_rect(top=(header_height - image.get_height()) // 2, right=right)
    right = status_rect.left - gap
    title_text = "INTERACTIVE TRANSFORMER LEARNING MACHINE"
    title, title_image, title_font = _fit_text(theme, title_text, max(1, right - edge), 20, True)
    title_rect = title_image.get_rect(left=edge,
                                      top=(header_height - title_image.get_height()) // 2)
    return HeaderLayout(HeaderItem(title, title_rect, title_font, True),
                        HeaderItem(status, status_rect, font, True), version, update)


def header_rectangles(layout):
    """Return the visible interactive header rectangles for geometry checks."""
    items = [layout.title.rect, layout.status.rect]
    if layout.version is not None:
        items.append(layout.version.rect)
    if layout.update is not None:
        items.append(layout.update.rect)
    return items

