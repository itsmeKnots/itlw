"""Reference-style transformer schematic drawn with Pygame primitives."""
from __future__ import annotations

import math

import pygame

from core.transformer import calculate_output_voltage


class PygameTransformerRenderer:
    """Keep the existing renderer lifecycle and wave phase for the UI view."""

    def __init__(self):
        self.wave_phase = 0.0

    def destroy(self):
        """Compatibility lifecycle hook; rendering uses Pygame primitives."""


class TransformerView:
    """Bridge between simulator state and the schematic renderer."""
    def __init__(self):
        self.renderer = PygameTransformerRenderer()

    def draw(self, surface, x, y, width, height, state, theme=None, time_delta=.016):
        panel = pygame.Rect(x, y, width, height)
        if panel.width <= 0 or panel.height <= 0:
            return
        import config as cfg
        result = calculate_output_voltage(state.primary_voltage, state.primary_turns, state.secondary_turns)
        scale = min((panel.w - 24) / cfg.UI_REF_WIDTH, (panel.h - 16) / cfg.UI_REF_HEIGHT)
        ox = panel.x + (panel.w - cfg.UI_REF_WIDTH * scale) / 2
        oy = panel.y + (panel.h - cfg.UI_REF_HEIGHT * scale) / 2
        width_line = max(2, round(2 * scale))

        def point(px, py):
            return ox + px * scale, oy + py * scale

        def draw_text(value, center, size, color, bold=True):
            image = theme.render_text(value, max(1, int(size * scale)), color, bold)
            surface.blit(image, image.get_rect(center=point(*center)))

        def draw_symbol(base, sub, center, size, color):
            bfont = theme.get_font(max(1, int(size * scale)))
            sfont = theme.get_font(max(1, int(size * scale * .65)))
            base_img, sub_img = bfont.render(base, True, color), sfont.render(sub, True, color)
            px, py = point(*center)
            start_x = px - (base_img.get_width() + sub_img.get_width()) / 2
            start_y = py - base_img.get_height() / 2
            surface.blit(base_img, (start_x, start_y))
            surface.blit(sub_img, (start_x + base_img.get_width(), start_y + base_img.get_height() * .38))

        pygame.draw.rect(surface, cfg.COLOR_PANEL, panel, border_radius=6)
        pygame.draw.rect(surface, cfg.COLOR_BORDER, panel, 1, border_radius=6)
        cx = cfg.UI_CX
        lx, rx = cx - cfg.UI_LABEL_DX, cx + cfg.UI_LABEL_DX
        draw_text("PRIMARY (INPUT)", (lx, 20), 13, cfg.COLOR_ACCENT_PRIMARY)
        draw_text("SECONDARY (OUTPUT)", (rx, 20), 13, cfg.COLOR_ACCENT_SECONDARY)
        values = ((lx, cfg.COLOR_ACCENT_PRIMARY, state.primary_voltage, state.primary_turns, "p"),
                  (rx, cfg.COLOR_ACCENT_SECONDARY, result.secondary_voltage, state.secondary_turns, "s"))
        for tx, color, voltage, turns, sub in values:
            draw_symbol("V", sub, (tx, 50), 14, cfg.COLOR_TEXT_DARK)
            draw_text(f"{voltage:g} v", (tx, 78), 28, color)
            draw_text("AC 60 Hz", (tx, 108), 12, cfg.COLOR_TEXT_DARK)
            draw_symbol("N", sub, (tx, 163), 14, cfg.COLOR_TEXT_DARK)
            draw_text(str(turns), (tx, 190), 20, color)
            draw_text("Turns", (tx, 215), 12, cfg.COLOR_TEXT_DARK)
        ratio = state.secondary_turns / state.primary_turns if state.primary_turns > 0 else 0
        draw_text("Turns Ratio (Ns/Np)", (cx, 200), 12, cfg.COLOR_TEXT_DARK)
        draw_text(f"{ratio:.2f}", (cx, 224), 24, cfg.COLOR_TEXT)
        for core_x in (cx - cfg.UI_CORE_GAP, cx + cfg.UI_CORE_GAP):
            pygame.draw.line(surface, cfg.COLOR_TEXT_DARK, point(core_x, cfg.UI_TOP - 22),
                             point(core_x, cfg.UI_BOTTOM + 22), width_line)
        for side, turns, dot, wave, vmax, voltage in (
                (+1, state.primary_turns, cfg.COLOR_DOT_PRIMARY, cfg.COLOR_WAVE_PRIMARY, 240, state.primary_voltage),
                (-1, state.secondary_turns, cfg.COLOR_DOT_SECONDARY, cfg.COLOR_WAVE_SECONDARY, 480, result.secondary_voltage)):
            coil_x = cx - side * (cfg.UI_CORE_GAP + cfg.UI_COIL_GAP + cfg.UI_COIL_RADIUS)
            edge = coil_x - side * cfg.UI_COIL_RADIUS
            terminal = cx - side * cfg.UI_TERMINAL_DX
            y0, y1 = cfg.UI_TOP + cfg.UI_JOG, cfg.UI_BOTTOM - cfg.UI_JOG
            loops = max(4, min(14, round(turns / 100) + 4))
            steps = loops * 28
            helix = []
            for i in range(steps + 1):
                t = -math.pi / 2 + 2 * math.pi * loops * i / steps
                helix.append(point(coil_x + side * cfg.UI_COIL_RADIUS * math.sin(t),
                                   y0 + (y1-y0) * i / steps + cfg.UI_COIL_RADIUS_Y * math.cos(t)))
            pygame.draw.lines(surface, cfg.COLOR_TEXT_DARK, False, helix, width_line)
            for yy, ycoil in ((cfg.UI_TOP, y0), (cfg.UI_BOTTOM, y1)):
                path = [(terminal, yy), (edge-side*cfg.UI_STUB, yy), (edge-side*cfg.UI_STUB, ycoil), (edge, ycoil)]
                pygame.draw.lines(surface, cfg.COLOR_TEXT_DARK, False, [point(*p) for p in path], width_line)
            for yy in (cfg.UI_TOP, cfg.UI_BOTTOM):
                pygame.draw.circle(surface, dot, point(terminal, yy), int(5*scale))
                pygame.draw.circle(surface, cfg.COLOR_TEXT_DARK, point(terminal, yy), int(5*scale), 2)
            mid = (cfg.UI_TOP + cfg.UI_BOTTOM) / 2
            xa, xb = terminal + side * 14, terminal + side * (14 + cfg.UI_WAVE_WIDTH)
            amp = 6 + 24 * max(0, min(1, voltage / vmax)) if voltage > 0 else 0
            pygame.draw.line(surface, cfg.COLOR_BASE, point(xa, mid), point(xb, mid), 1)
            wave_pts = [point(xa + (xb-xa)*i/60,
                               mid - amp*math.sin(2*math.pi*1.1*i/60 + self.renderer.wave_phase))
                        for i in range(61)]
            pygame.draw.lines(surface, wave, False, wave_pts, 2)
        self.renderer.wave_phase -= max(0, time_delta) * 2 * math.pi * .6

    def close(self):
        self.renderer.destroy()
