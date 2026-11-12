"""Keyboard and mouse input handling."""
import pygame
import config as cfg


class KeyboardMouseController:
    def __init__(self, screen=None):
        self.focus_index = 0
        self.controls = []
        self.screen = screen
        self.help_active = False

    def set_controls(self, controls):
        self.controls = list(controls) if controls else []

    def cycle_focus(self, direction=1):
        if not self.controls:
            return
        for control in self.controls:
            if hasattr(control, "focused"):
                control.focused = False
        self.focus_index = (self.focus_index + direction) % len(self.controls)
        if hasattr(self.controls[self.focus_index], "focused"):
            self.controls[self.focus_index].focused = True

    def handle_events(self, events, state, main_screen=None):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.cycle_focus(-1 if event.mod & pygame.KMOD_SHIFT else 1)
                elif event.key in (pygame.K_UP, pygame.K_RIGHT):
                    self._adjust_focused(1, state)
                elif event.key in (pygame.K_DOWN, pygame.K_LEFT):
                    self._adjust_focused(-1, state)
                elif event.key == pygame.K_m:
                    if main_screen:
                        if state.secondary_turns <= state.primary_turns:
                            main_screen._preset_step_up(state)
                        else:
                            main_screen._preset_step_down(state)
                elif event.key == pygame.K_r:
                    if main_screen:
                        main_screen._reset(state)
                elif event.key == pygame.K_h:
                    self.help_active = not self.help_active
                    return "help_toggle"
            for control in self.controls:
                try:
                    control.handle_event(event)
                except Exception:
                    pass

    def _adjust_focused(self, delta, state):
        if not self.controls:
            return
        control = self.controls[self.focus_index]
        tag = getattr(control, "tag", None)
        if tag == "vp":
            state.primary_voltage = max(cfg.Vp_MIN, min(cfg.Vp_MAX, state.primary_voltage + delta * cfg.Vp_STEP))
            if hasattr(control, "value"):
                control.value = state.primary_voltage
        elif tag == "np":
            state.primary_turns = max(cfg.Np_MIN, min(cfg.Np_MAX, state.primary_turns + delta * cfg.Np_STEP))
            if hasattr(control, "value"):
                control.value = state.primary_turns
        elif tag == "ns":
            state.secondary_turns = max(cfg.Ns_MIN, min(cfg.Ns_MAX, state.secondary_turns + delta * cfg.Ns_STEP))
            if hasattr(control, "value"):
                control.value = state.secondary_turns

    def update(self, state):
        pass
