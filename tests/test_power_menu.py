"""Unit tests for power-menu transitions without running OS commands."""
import unittest

from ui.power_menu import (
    PowerMenu, countdown_message, handle_power_menu_key, handle_power_menu_event,
    handle_power_menu_hardware, opens_power_menu_from_key, power_gesture_held,
)


class PowerMenuTests(unittest.TestCase):
    def test_open_selection_wrap_and_return_to_app(self):
        menu = PowerMenu()
        menu.open()

        self.assertEqual(menu.state, PowerMenu.MENU)
        self.assertEqual(menu.selected_action, "return_to_app")
        menu.move_selection(-1)
        self.assertEqual(menu.selected_action, "poweroff")
        menu.move_selection(1)
        self.assertEqual(menu.selected_action, "return_to_app")
        self.assertEqual(menu.activate(), "return_to_app")
        self.assertEqual(menu.state, PowerMenu.CLOSED)

    def test_restart_and_exit_require_confirmation_without_countdown(self):
        menu = PowerMenu()
        menu.open()
        menu.move_selection(1)
        self.assertIsNone(menu.activate())
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        self.assertEqual(menu.pending_action, "restart_app")
        self.assertEqual(menu.activate(), "restart_app")
        self.assertEqual(menu.state, PowerMenu.CLOSED)

        menu.open()
        menu.move_selection(2)
        self.assertIsNone(menu.activate())
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        self.assertEqual(menu.pending_action, "exit_to_desktop")
        self.assertEqual(menu.activate(), "exit_to_desktop")
        self.assertEqual(menu.state, PowerMenu.CLOSED)

    def test_return_to_app_needs_no_confirmation_or_countdown(self):
        menu = PowerMenu()
        menu.open()
        self.assertEqual(menu.activate(), "return_to_app")
        self.assertEqual(menu.state, PowerMenu.CLOSED)
        self.assertIsNone(menu.tick(20))

    def test_reboot_requires_confirmation_and_countdown(self):
        menu = PowerMenu(countdown_seconds=10)
        menu.open()
        menu.move_selection(3)

        self.assertIsNone(menu.activate())
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        self.assertEqual(menu.pending_action, "reboot")
        self.assertIsNone(menu.activate())
        self.assertEqual(menu.state, PowerMenu.COUNTDOWN)
        self.assertEqual(menu.remaining, 10)
        self.assertIsNone(menu.tick(9.5))
        self.assertEqual(menu.remaining, 0.5)
        self.assertIsNone(menu.tick(1))
        self.assertEqual(menu.state, PowerMenu.NOTICE)
        self.assertEqual(menu.tick(2), "reboot")
        self.assertEqual(menu.state, PowerMenu.CLOSED)
        self.assertIsNone(menu.pending_action)

    def test_countdown_wording_and_singular_second(self):
        self.assertEqual(countdown_message("reboot", 10), "Reboot starts in 10 seconds")
        self.assertEqual(countdown_message("poweroff", 10), "Shutdown starts in 10 seconds")
        self.assertEqual(countdown_message("reboot", 1), "Reboot starts in 1 second")
        self.assertEqual(countdown_message("poweroff", 0.2), "Shutdown starts in 1 second")

    def test_shutdown_confirmation_can_be_cancelled_from_both_stages(self):
        menu = PowerMenu()
        menu.open()
        menu.move_selection(4)
        menu.activate()
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        self.assertTrue(menu.cancel())
        self.assertEqual(menu.state, PowerMenu.MENU)
        self.assertIsNone(menu.pending_action)

        menu.activate()
        menu.activate()
        self.assertEqual(menu.state, PowerMenu.COUNTDOWN)
        self.assertTrue(menu.cancel())
        self.assertEqual(menu.state, PowerMenu.MENU)
        self.assertEqual(menu.selected_action, "poweroff")
        self.assertIsNone(menu.tick(20))

    def test_disabled_action_stays_in_menu_and_explains_why(self):
        menu = PowerMenu()
        menu.set_availability("restart_app", False, "Start ITLW as a service first.")
        menu.open()
        menu.move_selection(1)

        self.assertIsNone(menu.activate())
        self.assertEqual(menu.state, PowerMenu.MENU)
        self.assertEqual(menu.message, "Start ITLW as a service first.")

    def test_cancel_from_menu_returns_to_app_and_closed_actions_are_noops(self):
        menu = PowerMenu()
        self.assertFalse(menu.cancel())
        self.assertIsNone(menu.activate())
        self.assertIsNone(menu.tick(1))

        menu.open()
        self.assertTrue(menu.cancel())
        self.assertEqual(menu.state, PowerMenu.CLOSED)
        self.assertFalse(menu.cancel())

    def test_countdown_never_advances_by_negative_elapsed_time(self):
        menu = PowerMenu(countdown_seconds=2)
        menu.open()
        menu.move_selection(3)
        menu.activate()
        menu.activate()

        self.assertIsNone(menu.tick(-5))
        self.assertEqual(menu.remaining, 2)

    def test_keyboard_routes_open_navigate_confirm_and_cancel(self):
        import pygame
        self.assertTrue(opens_power_menu_from_key(pygame.K_ESCAPE))
        self.assertTrue(opens_power_menu_from_key(pygame.K_p))
        menu = PowerMenu()
        menu.open()
        handle_power_menu_key(menu, pygame.K_DOWN)
        self.assertEqual(menu.selected_action, "restart_app")
        handle_power_menu_key(menu, pygame.K_RETURN)
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        self.assertEqual(handle_power_menu_key(menu, pygame.K_RETURN), "restart_app")

    def test_mouse_events_do_not_act_on_power_menu(self):
        import pygame
        menu = PowerMenu()
        menu.open()
        initial_selection = menu.selection
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                           pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            event = pygame.event.Event(event_type, pos=(450, 300), button=1, y=1)
            self.assertIsNone(handle_power_menu_event(menu, event))
        self.assertEqual(menu.state, PowerMenu.MENU)
        self.assertEqual(menu.selection, initial_selection)

    def test_hardware_routes_open_navigate_confirm_and_cancel(self):
        self.assertFalse(power_gesture_held({"vp_plus_10": True, "vp_minus_10": True}, 1999))
        self.assertTrue(power_gesture_held({"vp_plus_10": True, "vp_minus_10": True}, 2000))
        self.assertFalse(power_gesture_held({"vp_plus_10": True}, 2500))
        menu = PowerMenu()
        menu.open()
        handle_power_menu_hardware(menu, "vp_minus_1")
        self.assertEqual(menu.selected_action, "restart_app")
        handle_power_menu_hardware(menu, "btn_mode")
        self.assertEqual(menu.state, PowerMenu.CONFIRM)
        handle_power_menu_hardware(menu, "btn_reset")
        self.assertEqual(menu.state, PowerMenu.MENU)


if __name__ == "__main__":
    unittest.main()
