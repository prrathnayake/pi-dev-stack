from __future__ import annotations

import asyncio
import unittest
from unittest import mock


class LayoutComponentTests(unittest.TestCase):
    def test_side_panel_tracks_active_page_and_toggle_request(self) -> None:
        from tui.components.side_panel import SidePanel

        panel = SidePanel()
        self.assertEqual(panel.active, "Dashboard")
        self.assertFalse(hasattr(panel, "logo_text"))

        panel._buttons = {"Dashboard": mock.Mock(), "Services": mock.Mock()}
        panel.set_active("Services")

        panel._buttons["Services"].add_class.assert_called_once_with("-active")
        panel._buttons["Dashboard"].remove_class.assert_called_once_with("-active")
        self.assertEqual(panel.active, "Services")

    def test_action_bar_includes_menu_action_for_small_screens(self) -> None:
        from tui.components.action_bar import ActionBar

        actions = ActionBar.actions()

        self.assertEqual(actions[0].action, "menu")
        self.assertIn("start", {action.action for action in actions})
        self.assertIn("quit", {action.action for action in actions})

    def test_status_badge_starts_animation_after_state_changes_to_running(self) -> None:
        from tui.components.status_badge import StatusBadge

        badge = StatusBadge("stopped")
        timer = mock.Mock()
        badge.set_interval = mock.Mock(return_value=timer)  # type: ignore[method-assign]

        with mock.patch.object(StatusBadge, "is_mounted", new_callable=mock.PropertyMock, return_value=True):
            badge.watch_state("running")

        badge.set_interval.assert_called_once()
        self.assertIs(badge._animation_timer, timer)

    def test_stat_gauge_uses_available_width_and_clamps_percent(self) -> None:
        from tui.components.stat_gauge import render_gauge

        rendered = render_gauge("CPU", 150, "hot", width=12)

        self.assertIn("100%", rendered)
        self.assertIn("hot", rendered)
        self.assertIn("██████", rendered)
        self.assertNotIn("150%", rendered)


class DialogAndAppTests(unittest.TestCase):
    def test_message_dialog_dismisses_on_button_press(self) -> None:
        from tui.components.dialogs import MessageDialog

        dialog = MessageDialog("Title", "Body", "Close")
        event = mock.Mock()

        dialog.dismiss = mock.Mock()  # type: ignore[method-assign]
        dialog.on_button_pressed(event)

        dialog.dismiss.assert_called_once_with(None)

    def test_compact_width_policy_collapses_menu_below_threshold(self) -> None:
        from tui.app import should_show_side_panel

        self.assertFalse(should_show_side_panel(79))
        self.assertTrue(should_show_side_panel(100))

    def test_help_action_uses_modal_dialog(self) -> None:
        from tui.app import HomelabTui
        from tui.components.dialogs import MessageDialog

        app = HomelabTui()
        app.push_screen = mock.Mock()  # type: ignore[method-assign]

        app.action_help_overlay()

        screen = app.push_screen.call_args.args[0]
        self.assertIsInstance(screen, MessageDialog)
        self.assertIn("keybindings", screen.message)

    def test_toggle_menu_updates_side_panel_visibility(self) -> None:
        from tui.app import HomelabTui

        panel = mock.Mock()
        app = HomelabTui()
        app.query_one = mock.Mock(return_value=panel)  # type: ignore[method-assign]
        app._side_panel_visible = False

        app.action_toggle_menu()

        panel.remove_class.assert_called_once_with("-collapsed")
        self.assertTrue(app._side_panel_visible)
        self.assertTrue(app._menu_user_overridden)


class AppSmokeTests(unittest.TestCase):
    def test_small_screen_starts_with_collapsed_side_panel(self) -> None:
        from tui.app import HomelabTui
        from tui.components.side_panel import SidePanel

        async def run() -> bool:
            app = HomelabTui()
            async with app.run_test(size=(78, 28)) as pilot:
                await pilot.pause(0.2)
                panel = app.query_one(SidePanel)
                return panel.has_class("-collapsed")

        self.assertTrue(asyncio.run(run()))


if __name__ == "__main__":
    unittest.main()
