import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import unittest

import pygame

from ui.theme import Theme, init_fonts
from ui.update_ui import UpdateUI
from update_check import UpdateSnapshot


class UpdateUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_fonts()
        cls.theme = Theme()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.checks = []
        self.installs = []
        self.ui = UpdateUI(
            self.theme, "manual", lambda: self.checks.append(True),
            lambda: self.installs.append(True),
        )
        self.surface = pygame.Surface((1240, 620))

    def test_manual_check_hotkey_and_confirmation(self):
        self.assertTrue(self.ui.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u),
            UpdateSnapshot("up_to_date", "abc1234"), self.surface.get_size(),
        ))
        self.assertEqual(self.checks, [True])

        self.ui.draw(self.surface, UpdateSnapshot("update_available", "abc1234", "def5678"))
        self.assertTrue(self.ui.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u),
            UpdateSnapshot("update_available", "abc1234", "def5678"), self.surface.get_size(),
        ))
        self.assertTrue(self.ui.confirming)
        self.ui.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
            UpdateSnapshot("update_available"), self.surface.get_size(),
        )
        self.assertEqual(self.installs, [True])

    def test_later_and_hardware_confirmation(self):
        update = UpdateSnapshot("update_available")
        self.ui.confirming = True
        self.assertTrue(self.ui.handle_hardware_button("btn_reset", update, "index"))
        self.assertFalse(self.ui.confirming)
        self.assertEqual(self.installs, [])
        self.assertTrue(self.ui.handle_hardware_button("btn_mode", update, "index"))
        self.assertTrue(self.ui.confirming)
        self.ui.handle_hardware_button("btn_mode", update, "index")
        self.assertEqual(self.installs, [True])

    def test_banner_confirmation_and_fullscreen_updating_render(self):
        available = UpdateSnapshot("update_available", "abc1234", "def5678")
        trigger = self.ui.action_rects(self.surface.get_size())["trigger"]
        self.assertTrue(self.ui.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=trigger.center),
            available, self.surface.get_size(),
        ))
        self.assertTrue(self.ui.confirming)
        self.ui.confirming = False
        self.surface.fill((255, 255, 255))
        self.ui.draw(self.surface, UpdateSnapshot("updating", "abc1234"))
        self.assertLess(self.surface.get_at((5, 5)).r, 100)


if __name__ == "__main__":
    unittest.main()
