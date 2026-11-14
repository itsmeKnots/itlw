"""Responsive monochrome desktop composition and user-facing help."""
from __future__ import annotations

import calendar
import math
from datetime import datetime
from pathlib import Path

import pygame

import config as cfg
from ui.header_layout import layout_header
from core.transformer import calculate_output_voltage
from ui.components import Button


class AppState:
    def __init__(self):
        self.primary_voltage = cfg.Vp_DEFAULT
        self.primary_turns = cfg.Np_DEFAULT
        self.secondary_turns = cfg.Ns_DEFAULT
        self.operation = None
        self.turns_knob_value = cfg.Ns_DEFAULT
        self.frequency = cfg.Simulated_Frequency_DEFAULT
        self.mode = cfg.CONTROL_METHOD
        self.animation_enabled = cfg.ANIMATION_ENABLED_DEFAULT
        self.selected_control = 0
        self.help_visible = False
        self.active_screen = "index"


class IndexScreen:
    """Two-column launch dashboard with project widgets and system status."""

    def __init__(self, theme):
        self.theme = theme
        self.last_size = None
        self.open_workbench: Button | None = None

    def _layout(self, surface, state):
        width, height = surface.get_size()
        margin, gap, footer_height = 24, 16, 38
        widget_top = cfg.UI_HEADER_HEIGHT + 8
        usable_width = width - margin * 2
        left_width = int(usable_width * 0.43)
        right_width = usable_width - left_width - gap
        widget_height = max(150, height - widget_top - margin - footer_height)
        self.title_rect = pygame.Rect(margin, widget_top, left_width, 146)
        self.time_rect = pygame.Rect(margin, self.title_rect.bottom + gap, left_width, 112)
        self.calendar_rect = pygame.Rect(margin, self.time_rect.bottom + gap, left_width,
            widget_height - self.title_rect.height - self.time_rect.height - gap * 2)
        right_x = self.title_rect.right + gap
        self.document_rect = pygame.Rect(right_x, widget_top, right_width, (widget_height-gap)//2)
        self.tutorial_rect = pygame.Rect(right_x, self.document_rect.bottom+gap, right_width,
            widget_height-self.document_rect.height-gap)
        self.footer_rect = pygame.Rect(0, height-footer_height, width, footer_height)
        if self.last_size != (width, height):
            self.last_size = (width, height)
            self.open_workbench = Button(
                (self.title_rect.left+18, self.title_rect.bottom-48, 194, 32),
                "OPEN WORKBENCH", lambda: setattr(state, "active_screen", "workbench"),
                "Open the interactive transformer simulator.")

    def _panel(self, surface, rect):
        pygame.draw.rect(surface, self.theme.colors["card"], rect, border_radius=cfg.CORNER_RADIUS)
        pygame.draw.rect(surface, self.theme.colors["border"], rect, 1, border_radius=cfg.CORNER_RADIUS)

    def _text(self, surface, text, position, size=14, color=None, bold=False):
        surface.blit(self.theme.render_text(text, size, color, bold), position)

    def handle_event(self, event, state):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            state.active_screen = "workbench"
            return
        if self.open_workbench:
            self.open_workbench.handle_event(event)

    def draw(self, surface, state, dt=0.016):
        self._layout(surface, state)
        colors, now = self.theme.colors, datetime.now()
        surface.fill(colors["bg"])
        self._draw_title_widget(surface)
        self._draw_document_widget(surface)
        self._draw_tutorial_widget(surface)
        self._draw_time_widget(surface, now)
        self._draw_calendar_widget(surface, now)
        self._draw_footer(surface)

    def _draw_title_widget(self, surface):
        self._panel(surface, self.title_rect)
        colors = self.theme.colors
        self._text(surface, "INTERACTIVE TRANSFORMER", (self.title_rect.left+18,self.title_rect.top+18), 19,bold=True)
        self._text(surface, "LEARNING MACHINE", (self.title_rect.left+18,self.title_rect.top+43), 19,bold=True)
        self._text(surface, "Interactive transformer study environment", (self.title_rect.left+19,self.title_rect.top+72), 12,colors["text_subtle"])
        self.open_workbench.rect.topleft=(self.title_rect.left+18,self.title_rect.bottom-48)
        self.open_workbench.draw(surface,self.theme)
        self._text(surface,"ENTER  OPEN",(self.title_rect.left+222,self.title_rect.bottom-36),10,colors["text_subtle"],True)

    def _draw_document_widget(self,surface):
        self._panel(surface,self.document_rect); c=self.theme.colors
        self._text(surface,"01  PROJECT DOCUMENT",(self.document_rect.left+18,self.document_rect.top+17),12,bold=True)
        self._text(surface,"DOCUMENT WIDGET / PLACEHOLDER",(self.document_rect.left+18,self.document_rect.top+42),10,c["text_subtle"],True)
        self._text(surface,"Attach your thesis, learning guide, or laboratory worksheet here.",(self.document_rect.left+18,self.document_rect.top+68),13,c["text_subtle"])
        self._text(surface,"NO DOCUMENT CONNECTED",(self.document_rect.left+18,self.document_rect.bottom-32),11,c["text"],True)

    def _draw_tutorial_widget(self,surface):
        self._panel(surface,self.tutorial_rect); c=self.theme.colors
        self._text(surface,"02  DEMO TUTORIAL",(self.tutorial_rect.left+18,self.tutorial_rect.top+17),12,bold=True)
        self._text(surface,"TUTORIAL WIDGET / PLACEHOLDER",(self.tutorial_rect.left+18,self.tutorial_rect.top+42),10,c["text_subtle"],True)
        for i,line in enumerate(("1. Set Vp, Np, and Ns.","2. Observe the calculated Vs.","3. Compare step-up and step-down modes.","Press Esc for power menu.","Hold Vp +10 and Vp -10 to open power menu.")):
            self._text(surface,line,(self.tutorial_rect.left+18,self.tutorial_rect.top+70+i*22),12,c["text_subtle"])

    def _draw_time_widget(self,surface,now):
        self._panel(surface,self.time_rect); c=self.theme.colors
        self._text(surface,"03  LOCAL TIME",(self.time_rect.left+18,self.time_rect.top+16),11,bold=True)
        image=self.theme.render_text(now.strftime("%H:%M:%S"),29,c["text"],True)
        surface.blit(image,(self.time_rect.left+18,self.time_rect.top+40))
        self._text(surface,now.strftime("%A, %d %B %Y"),(self.time_rect.left+20,self.time_rect.bottom-21),11,c["text_subtle"])

    def _draw_calendar_widget(self,surface,now):
        self._panel(surface,self.calendar_rect); c=self.theme.colors
        self._text(surface,"04  CALENDAR",(self.calendar_rect.left+18,self.calendar_rect.top+16),11,bold=True)
        self._text(surface,now.strftime("%B %Y").upper(),(self.calendar_rect.left+18,self.calendar_rect.top+40),14,c["text"],True)
        data=calendar.Calendar(firstweekday=0).monthdayscalendar(now.year,now.month)
        left,top=self.calendar_rect.left+18,self.calendar_rect.top+70
        cell=(self.calendar_rect.width-36)/7
        row_pitch=min(25,max(16,(self.calendar_rect.height-90)//max(1,len(data))))
        for i,day in enumerate(("MO","TU","WE","TH","FR","SA","SU")):
            image=self.theme.render_text(day,9,c["text_subtle"],True)
            surface.blit(image,image.get_rect(center=(left+cell*(i+.5),top)))
        for row,week in enumerate(data):
            for col,day in enumerate(week):
                if not day: continue
                center=(int(left+cell*(col+.5)),top+22+row*row_pitch)
                color=c["text"]
                if day==now.day:
                    marker=pygame.Rect(0,0,24,20); marker.center=center
                    pygame.draw.rect(surface,color,marker,border_radius=2); color=c["bg"]
                image=self.theme.render_text(str(day),11,color,day==now.day)
                surface.blit(image,image.get_rect(center=center))

    @staticmethod
    def _battery_status() -> str:
        for capacity_file in Path("/sys/class/power_supply").glob("BAT*/capacity"):
            try: return f"BATTERY {int(capacity_file.read_text().strip())}%"
            except (OSError,ValueError): pass
        return "POWER EXTERNAL"

    @staticmethod
    def _cpu_temperature() -> str:
        try: return f"CPU {int(Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip())/1000:.1f}°C"
        except (OSError,ValueError): return "CPU --°C"

    def _draw_footer(self,surface):
        c=self.theme.colors
        pygame.draw.rect(surface,(245,245,245),self.footer_rect)
        pygame.draw.line(surface,c["border"],self.footer_rect.topleft,self.footer_rect.topright)
        self._text(surface,"INTERACTIVE TRANSFORMER LEARNING MACHINE  /  READY",(18,self.footer_rect.top+13),10,c["text_subtle"],True)
        battery,cpu=self._battery_status(),self._cpu_temperature()
        bx=self.footer_rect.right-178; cx=bx-145
        icon=pygame.Rect(bx,self.footer_rect.top+11,18,12)
        pygame.draw.rect(surface,c["text"],icon,1); pygame.draw.rect(surface,c["text"],(icon.right,icon.top+4,2,4))
        if battery.startswith("BATTERY"): pygame.draw.rect(surface,c["text"],icon.inflate(-5,-5))
        self._text(surface,battery,(bx+27,self.footer_rect.top+13),10,c["text_subtle"],True)
        pygame.draw.line(surface,c["text"],(cx+7,self.footer_rect.top+10),(cx+7,self.footer_rect.top+21),2)
        pygame.draw.circle(surface,c["text"],(cx+7,self.footer_rect.top+23),4)
        self._text(surface,cpu,(cx+18,self.footer_rect.top+13),10,c["text_subtle"],True)


class MainScreen:
    """Fixed reference composition backed by the existing workbench state."""

    def __init__(self, theme, transformer_view):
        self.theme, self.transformer_view = theme, transformer_view
        self.controls = []
        self.hardware_inputs = {}
        self.selected_mode = None
        self.drag = None
        self.focus = None
        self.hold = None
        self.phase = 0.0
        self._layout()

    def _layout(self):
        self.pad, self.gap = cfg.UI_PAD, cfg.UI_GAP
        self.col_w = cfg.UI_COLUMN_WIDTH
        self.col_x = cfg.UI_WIDTH - self.pad - self.col_w
        self.bar_h, self.knob_h, self.btn_h = cfg.UI_BAR_HEIGHT, cfg.UI_KNOB_HEIGHT, cfg.UI_BUTTON_HEIGHT
        self.col_h = self.bar_h * 2 + self.knob_h + self.btn_h + self.gap * 3
        self.top = cfg.UI_HEADER_HEIGHT + self.pad
        self.model_rect = pygame.Rect(self.pad, self.top, self.col_x - 12 - self.pad, self.col_h)
        y = self.top
        self.vp_rect = pygame.Rect(self.col_x, y, self.col_w, self.bar_h)
        y += self.bar_h + self.gap
        bw = (self.col_w - 2 * self.gap) // 3
        self.btn_up = pygame.Rect(self.col_x, y, bw, self.btn_h)
        self.btn_down = pygame.Rect(self.col_x + bw + self.gap, y, bw, self.btn_h)
        self.btn_reset = pygame.Rect(self.col_x + 2 * (bw + self.gap), y, bw, self.btn_h)
        y += self.btn_h + self.gap
        kw = (self.col_w - self.gap) // 2
        self.knob_rects = {
            "np": pygame.Rect(self.col_x, y, kw, self.knob_h),
            "ns": pygame.Rect(self.col_x + kw + self.gap, y, kw, self.knob_h),
        }
        y += self.knob_h + self.gap
        self.vs_rect = pygame.Rect(self.col_x, y, self.col_w, self.bar_h)
        self._bar_geometry()
        self.focus = None

    def _bar_geometry(self):
        y = self.vp_rect.y + 34
        self.vp_minus = pygame.Rect(self.vp_rect.x + 12, y, 40, 30)
        self.vp_plus = pygame.Rect(self.vp_rect.right - 52, y, 40, 30)
        self.vp_track = pygame.Rect(self.vp_minus.right + 8, y, self.vp_plus.x - self.vp_minus.right - 16, 30)
        self.vs_track = pygame.Rect(self.vs_rect.x + 12, self.vs_rect.y + 34, self.vs_rect.w - 24, 30)

    def _text(self, surface, value, pos, size=14, color=None, bold=False, anchor="topleft"):
        image = self.theme.render_text(str(value), size, color, bold)
        rect = image.get_rect()
        setattr(rect, anchor, pos)
        surface.blit(image, rect)
        return rect

    @staticmethod
    def _box(surface, rect, fill=None, border=None, radius=3):
        if fill is not None:
            pygame.draw.rect(surface, fill, rect, border_radius=radius)
        if border:
            pygame.draw.rect(surface, border, rect, 1, border_radius=radius)

    def _button(self, surface, rect, label, pressed=False, active=False):
        c = cfg
        hovered = rect.collidepoint(getattr(self, "pointer", pygame.mouse.get_pos()))
        self._box(surface, rect, c.COLOR_BUTTON_PRESSED if (pressed or active) else
                  c.COLOR_BUTTON_HOVER if hovered else c.COLOR_CARD, c.COLOR_BORDER)
        self._text(surface, label, rect.center, 15, c.COLOR_TEXT, True, "center")

    def _values(self, state):
        result = calculate_output_voltage(state.primary_voltage, state.primary_turns, state.secondary_turns)
        return float(result.secondary_voltage), float(state.primary_voltage), int(state.primary_turns), int(state.secondary_turns)

    def _draw_bar(self, surface, rect, track, label, sym, value, maximum, primary=True, readonly=False):
        c = cfg
        accent = c.COLOR_ACCENT_PRIMARY if primary else c.COLOR_ACCENT_SECONDARY
        fill = c.COLOR_FILL_PRIMARY if primary else c.COLOR_FILL_SECONDARY
        self._box(surface, rect, c.COLOR_CARD, c.COLOR_BORDER)
        self._text(surface, label, (rect.x + 12, rect.y + 9), 14, accent, True)
        self._text(surface, sym + ("  ·  calculated" if readonly else ""), (rect.right - 12, rect.y + 9), 14, c.COLOR_TEXT_SUBTLE, False, "topright")
        self._box(surface, track, c.COLOR_BUTTON_HOVER, c.COLOR_BORDER)
        frac = max(0.0, min(1.0, value / maximum if maximum else 0.0))
        if frac > 0:
            pygame.draw.rect(surface, fill, pygame.Rect(track.x + 1, track.y + 1, max(2, (track.w - 2) * frac), track.h - 2), border_radius=3)
        self._box(surface, track, None, c.COLOR_BORDER)
        self._text(surface, f"{value:g} V", track.center, 17, c.COLOR_TEXT, True, "center")
        if not readonly:
            active_minus = any(self.hardware_inputs.get(k) for k in ("vp_minus_1", "vp_minus_10"))
            active_plus = any(self.hardware_inputs.get(k) for k in ("vp_plus_1", "vp_plus_10"))
            self._button(surface, self.vp_minus, "−", active_minus or bool(self.hold and self.hold[1] < 0))
            self._button(surface, self.vp_plus, "+", active_plus or bool(self.hold and self.hold[1] > 0))

    def _draw_knob(self, surface, key, state):
        c = cfg
        rect = self.knob_rects[key]
        value = state.primary_turns if key == "np" else state.secondary_turns
        label, sym = ("Primary turns", "Np") if key == "np" else ("Secondary turns", "Ns")
        accent = ((175, 175, 175) if self.selected_mode is None else
                  c.COLOR_ACCENT_PRIMARY if key == "np" else c.COLOR_ACCENT_SECONDARY)
        self._box(surface, rect, c.COLOR_CARD, c.COLOR_BORDER)
        self._text(surface, label, (rect.x + 10, rect.y + 9), 13, accent, True)
        self._text(surface, sym, (rect.right - 10, rect.y + 9), 13, c.COLOR_TEXT_SUBTLE, False, "topright")
        cx, cy = rect.centerx, rect.y + 34 + c.UI_KNOB_RADIUS
        scale = c.UI_KNOB_RADIUS / 60
        angle = -135 + 270 * max(0, min(1000, value)) / 1000
        pts = self._arc(cx, cy, 54 * scale, -135, 135)
        pygame.draw.lines(surface, c.COLOR_BORDER, False, pts, 4)
        if angle > -135:
            pygame.draw.lines(surface, accent, False, self._arc(cx, cy, 54 * scale, -135, angle), 4)
        for i in range(21):
            a = -135 + 270 * i / 20
            major = i % 5 == 0
            pygame.draw.line(surface, (125, 125, 125), self._polar(cx, cy, 50 * scale, a),
                             self._polar(cx, cy, (44 if major else 46) * scale, a), 2 if major else 1)
        pygame.draw.circle(surface, c.COLOR_TEXT, (cx, cy), int(34 * scale))
        pygame.draw.circle(surface, c.COLOR_TEXT_SUBTLE, (cx, cy), int(30 * scale), 1)
        tip = self._polar(cx, cy, 26 * scale, angle)
        pygame.draw.line(surface, c.COLOR_BACKGROUND, (cx, cy), tip, 4)
        pygame.draw.circle(surface, c.COLOR_BACKGROUND, tip, 2)
        if self.focus == key:
            pygame.draw.circle(surface, c.COLOR_TEXT, (cx, cy), c.UI_KNOB_RADIUS + 3, 2)
        if self.selected_mode is None:
            pygame.draw.circle(surface, (110, 110, 110), (cx, cy), int(34 * scale))
            pygame.draw.circle(surface, c.COLOR_TEXT_SUBTLE, (cx, cy), int(30 * scale), 1)
            tip = self._polar(cx, cy, 26 * scale, angle)
            pygame.draw.line(surface, c.COLOR_BACKGROUND, (cx, cy), tip, 4)
            pygame.draw.circle(surface, c.COLOR_BACKGROUND, tip, 2)
            self._text(surface, "Select a mode first", (cx, rect.bottom - 20), 11,
                       c.COLOR_TEXT_SUBTLE, False, "midtop")
        else:
            self._text(surface, "0", (cx - c.UI_KNOB_RADIUS + 4, rect.bottom - 20), 11, c.COLOR_TEXT_SUBTLE)
            self._text(surface, "1000", (cx + c.UI_KNOB_RADIUS - 4, rect.bottom - 20), 11,
                       c.COLOR_TEXT_SUBTLE, False, "topright")

    @staticmethod
    def _polar(cx, cy, radius, degrees):
        a = math.radians(degrees - 90)
        return cx + radius * math.cos(a), cy + radius * math.sin(a)

    @classmethod
    def _arc(cls, cx, cy, radius, a, b, step=3):
        n = max(2, int(abs(b - a) / step) + 1)
        return [cls._polar(cx, cy, radius, a + (b - a) * i / (n - 1)) for i in range(n)]

    def _set_turns(self, key, value, state):
        from core.transformer import jround
        value = jround(value / cfg.TURNS_KNOB_STEP) * cfg.TURNS_KNOB_STEP
        if key == "np":
            self._set_primary_turns(state, value)
        else:
            self._set_turns_knob(state, value)
        self.selected_mode = state.operation

    def _preset_step_up(self, state):
        from core.transformer import set_mode
        set_mode(state, "up")
        self.selected_mode = state.operation

    def _preset_step_down(self, state):
        from core.transformer import set_mode
        set_mode(state, "down")
        self.selected_mode = state.operation

    def _toggle_mode(self, state):
        from core.transformer import toggle_mode
        toggle_mode(state)
        self.selected_mode = state.operation

    def _reset(self, state):
        from core.transformer import reset
        reset(state)
        self.selected_mode = state.operation

    def _go_home(self, state):
        self.drag = self.hold = None
        self.focus = None
        state.active_screen = "index"

    def nudge(self, state, key, delta):
        from core.transformer import nudge
        nudge(state, key, delta)
        self.selected_mode = state.operation

    def _adjust_vp_control(self, state, delta):
        from core.transformer import set_vp
        set_vp(state, state.primary_voltage + delta)
        self.selected_mode = state.operation

    def _set_turns_knob(self, state, value):
        from core.transformer import set_turns
        set_turns(state, "ns", value)
        self.selected_mode = state.operation

    def _set_primary_turns(self, state, value):
        from core.transformer import set_turns
        set_turns(state, "np", value)
        self.selected_mode = state.operation

    def _knob_value(self, key, pos):
        rect = self.knob_rects[key]
        cx, cy = rect.centerx, rect.y + 34 + cfg.UI_KNOB_RADIUS
        angle = math.degrees(math.atan2(pos[0] - cx, -(pos[1] - cy)))
        angle = max(-135, min(135, angle))
        return (angle + 135) / 270 * 1000

    def handle_event(self, event, state):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                keys = ["vp", "np", "ns"]
                index = keys.index(self.focus) if self.focus in keys else -1
                self.focus = keys[(index + 1) % 3]
            elif event.key == pygame.K_r:
                self._reset(state)
            elif event.key == pygame.K_h:
                self._go_home(state)
            elif self.focus and event.key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT):
                direction = 1 if event.key in (pygame.K_UP, pygame.K_RIGHT) else -1
                if self.focus == "vp":
                    self.nudge(state, "vp", direction)
                else:
                    step = cfg.TURNS_KNOB_STEP if event.mod & pygame.KMOD_SHIFT else cfg.Np_STEP
                    self.nudge(state, self.focus, direction * step)
            elif self.focus in ("np", "ns") and event.key in (pygame.K_HOME, pygame.K_END):
                self._set_turns(self.focus, 0 if event.key == pygame.K_HOME else 1000, state)
            return
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = event.pos
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.vp_minus.collidepoint(pos):
                now = pygame.time.get_ticks(); self._adjust_vp_control(state, -1); self.hold = ("vp", -1, now, now); return
            if self.vp_plus.collidepoint(pos):
                now = pygame.time.get_ticks(); self._adjust_vp_control(state, 1); self.hold = ("vp", 1, now, now); return
            if self.vp_track.collidepoint(pos):
                self._adjust_vp_control(state, (pos[0]-self.vp_track.x)/self.vp_track.w*cfg.Vp_MAX - state.primary_voltage); self.drag = "vp"; return
            if self.btn_up.collidepoint(pos):
                self._preset_step_up(state); return
            if self.btn_down.collidepoint(pos):
                self._preset_step_down(state); return
            if self.btn_reset.collidepoint(pos):
                self._reset(state); self.focus = None; return
            for key, rect in self.knob_rects.items():
                knob_center = (rect.centerx, rect.y + 34 + cfg.UI_KNOB_RADIUS)
                if math.hypot(pos[0]-knob_center[0], pos[1]-knob_center[1]) <= cfg.UI_KNOB_RADIUS and self.selected_mode:
                    self.focus, self.drag = key, key
                    self._set_turns(key, self._knob_value(key, pos), state)
                    return
        elif event.type == pygame.MOUSEMOTION and self.drag:
            if self.drag == "vp" and self.vp_track.w:
                self._adjust_vp_control(state, (event.pos[0]-self.vp_track.x)/self.vp_track.w*cfg.Vp_MAX - state.primary_voltage)
            else:
                self._set_turns(self.drag, self._knob_value(self.drag, event.pos), state)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag = self.hold = None
        elif event.type == pygame.MOUSEWHEEL:
            pos = getattr(self, "pointer", pygame.mouse.get_pos())
            if self.vp_rect.collidepoint(pos):
                self._adjust_vp_control(state, 1 if event.y > 0 else -1)
            for key, rect in self.knob_rects.items():
                if rect.collidepoint(pos):
                    self._set_turns(key, (state.primary_turns if key == "np" else state.secondary_turns) + (cfg.TURNS_KNOB_STEP if event.y > 0 else -cfg.TURNS_KNOB_STEP), state)

    def tick_hold(self):
        if not self.hold:
            return
        key, direction, started, last = self.hold
        now = pygame.time.get_ticks()
        held = now - started
        if held > 450 and now - last >= 60:
            self.hold = (key, direction, started, now)
            self.nudge_from_hold(key, direction * (5 if held >= 1500 else 1))

    def nudge_from_hold(self, key, delta):
        if hasattr(self, "_active_state"):
            self.nudge(self._active_state, key, delta)

    def apply_hardware_knobs(self, state, inputs):
        self.hardware_inputs = inputs or {}
        if not hasattr(self, "_last_applied_knob_values"):
            self._last_applied_knob_values = {"pot_np": None, "pot_ns": None}
        from core.transformer import set_turns
        for name, target in (("pot_np", "np"), ("pot_ns", "ns")):
            value = self.hardware_inputs.get(name)
            if value is None:
                continue
            minimum, maximum, step = cfg.HARDWARE_KNOB_RANGES[name]
            snapped = max(minimum, min(maximum, round((value - minimum) / step) * step + minimum))
            if snapped != self._last_applied_knob_values[name]:
                set_turns(state, target, snapped)
                self.selected_mode = state.operation
                self._last_applied_knob_values[name] = snapped

    def _draw_header(self, surface, state):
        h = cfg.UI_HEADER_HEIGHT
        pygame.draw.line(surface, cfg.COLOR_BORDER, (0, h - 1), (cfg.UI_WIDTH, h - 1))
        layout = layout_header(self.theme, surface.get_size(), "workbench",
                               "Press Esc for power menu", "CHECK FOR UPDATES [U]", "v-------")
        self._text(surface, layout.title.text, layout.title.rect.topleft,
                   layout.title.font_size, cfg.COLOR_TEXT, True)

    def _draw_model(self, surface, state, phase):
        self.transformer_view.draw(surface, self.model_rect.x, self.model_rect.y,
                                   self.model_rect.w, self.model_rect.h, state, self.theme, 1/60)

    def draw(self, surface, state, dt=1/60):
        self._active_state = state
        self.phase -= dt * 2 * math.pi * 0.6
        surface.fill(cfg.COLOR_BACKGROUND)
        self._draw_header(surface, state)
        self._draw_model(surface, state, self.phase)
        vs = calculate_output_voltage(state.primary_voltage, state.primary_turns, state.secondary_turns).secondary_voltage
        self._draw_bar(surface, self.vp_rect, self.vp_track, "Primary voltage", "Vp", state.primary_voltage, cfg.Vp_MAX)
        active = self.selected_mode
        self._button(surface, self.btn_up, "Step-up", active=active == "up" or bool(self.hardware_inputs.get("btn_mode") and state.secondary_turns > state.primary_turns))
        self._button(surface, self.btn_down, "Step-down", active=active == "down" or bool(self.hardware_inputs.get("btn_mode") and state.secondary_turns <= state.primary_turns))
        self._button(surface, self.btn_reset, "Reset", pressed=bool(self.hardware_inputs.get("btn_reset")))
        for key in self.knob_rects:
            self._draw_knob(surface, key, state)
        self._draw_bar(surface, self.vs_rect, self.vs_track, "Secondary voltage", "Vs", vs, 480, False, True)
        mode = "Not selected" if self.selected_mode is None else ("Step-up" if self.selected_mode == "up" else "Step-down")
        cards = [("Mode", mode), ("Input voltage", f"{state.primary_voltage:g} V"),
                 ("Output voltage", f"{vs:g} V"), ("Primary turns", str(state.primary_turns)),
                 ("Secondary turns", str(state.secondary_turns))]
        top = self.top + self.col_h + 12
        cw = (cfg.UI_WIDTH - 2 * cfg.UI_PAD - 4 * cfg.UI_GAP) / 5
        for index, (label, value) in enumerate(cards):
            rect = pygame.Rect(cfg.UI_PAD + index * (cw + cfg.UI_GAP), top, cw, 64)
            self._box(surface, rect, cfg.COLOR_CARD, cfg.COLOR_BORDER)
            self._text(surface, label, (rect.centerx, rect.y + 9), 13, cfg.COLOR_TEXT_SUBTLE, False, "midtop")
            self._text(surface, value, (rect.centerx, rect.y + 30), 22, cfg.COLOR_TEXT, True, "midtop")
