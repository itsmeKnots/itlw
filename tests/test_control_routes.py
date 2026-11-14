import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from types import SimpleNamespace
import unittest
import pygame

from ui.screens import MainScreen
from ui.screens import IndexScreen
from ui.theme import Theme, init_fonts


class ControlRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_fonts()
        cls.theme = Theme()

    def test_h_key_returns_to_dashboard_and_old_home_position_does_nothing(self):
        screen = object.__new__(MainScreen)
        screen.drag = screen.hold = screen.focus = None
        state = SimpleNamespace(active_screen="workbench")
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h), state)
        self.assertEqual(state.active_screen, "index")

        state.active_screen = "workbench"
        screen.pointer = None
        screen.vp_minus = pygame.Rect(0, 100, 10, 10)
        screen.vp_plus = pygame.Rect(20, 100, 10, 10)
        screen.vp_track = pygame.Rect(40, 100, 10, 10)
        screen.btn_up = pygame.Rect(60, 100, 10, 10)
        screen.btn_down = pygame.Rect(80, 100, 10, 10)
        screen.btn_reset = pygame.Rect(100, 100, 10, 10)
        screen.knob_rects = {}
        for old_button_position in ((1086, 28), (1172, 28)):
            screen.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=old_button_position), state)
            self.assertEqual(state.active_screen, "workbench")

    def test_dashboard_click_at_former_power_position_does_nothing(self):
        dashboard = IndexScreen(self.theme)
        state = SimpleNamespace(active_screen="index")
        dashboard._layout(pygame.Surface((1240, 620)), state)
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            dashboard.handle_event(pygame.event.Event(
                event_type, button=1, pos=(430, 71)), state)
        self.assertEqual(state.active_screen, "index")


if __name__ == "__main__":
    unittest.main()
