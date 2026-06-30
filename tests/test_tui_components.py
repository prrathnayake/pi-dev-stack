from __future__ import annotations

import asyncio
import unittest
from unittest import mock


class ComponentBehaviorTests(unittest.TestCase):
    def test_entrypoint_runs_app(self) -> None:
        from tui import __main__

        app = mock.Mock()
        with mock.patch("tui.__main__.HomelabTui", return_value=app):
            __main__.main()
        app.run.assert_called_once_with()

    def test_banner_pulse_switches_precomputed_frames(self) -> None:
        from tui.components.banner import HomelabBanner

        banner = HomelabBanner()
        logo = mock.Mock()
        banner.query_one = mock.Mock(return_value=logo)  # type: ignore[method-assign]
        banner._pulse()
        banner._pulse()
        self.assertEqual(logo.update.call_count, 2)

    def test_loading_spinner_lifecycle_and_render(self) -> None:
        from rich.spinner import Spinner
        from tui.components.loading_spinner import OrangeSpinner

        spinner = OrangeSpinner("Loading")
        self.assertIn("Loading", str(spinner.render()))
        spinner.set_interval = mock.Mock()  # type: ignore[method-assign]
        spinner.on_mount()
        self.assertIsInstance(spinner.render(), Spinner)
        spinner.update_text("Next")
        self.assertEqual(str(spinner._spinner.text), "Next")

    def test_side_panel_button_press_posts_page(self) -> None:
        from tui.components.side_panel import SidePanel

        panel = SidePanel()
        panel.post_message = mock.Mock()  # type: ignore[method-assign]
        event = mock.Mock()
        event.button.id = "side-system"
        panel.on_button_pressed(event)

        self.assertEqual(panel.active, "System")
        self.assertEqual(panel.post_message.call_args.args[0].page, "System")

    def test_service_card_update_branches_and_clicks(self) -> None:
        from tui.components.service_card import ServiceCard

        card = ServiceCard("web")
        badge = mock.Mock()
        port = mock.Mock()
        stats = mock.Mock()
        card._badge = badge
        card._port_label = port
        card._stats_label = stats
        card.post_message = mock.Mock()  # type: ignore[method-assign]
        card.add_class = mock.Mock()  # type: ignore[method-assign]
        card.remove_class = mock.Mock()  # type: ignore[method-assign]

        for idx, (state, expected) in enumerate([
            ("running", "-running"),
            ("pulling", "-pulling"),
            ("error", "-error"),
            ("missing", "-stopped"),
        ]):
            card.update_state(state, "8080", "up", f"{idx}%", "2%", "core")
            self.assertIn(mock.call(expected), card.add_class.mock_calls)

        card.on_click(mock.Mock())
        self.assertEqual(card.post_message.call_args.args[0].service, "web")
        card.select()
        card.deselect()

    def test_service_grid_selection_and_event_update(self) -> None:
        from tui.components.service_grid import ServiceGrid

        grid = ServiceGrid()
        first = mock.Mock()
        second = mock.Mock()
        grid._cards = {"web": first, "db": second}
        grid.select_service("web")
        grid.select_service("db")
        first.deselect.assert_called_once_with()
        second.select.assert_called_once_with()

        grid.update_service_state("db", "running")
        second.update_state.assert_called_with("running", second.port, second.uptime, second.cpu, second.mem, second.profile)

    def test_log_panel_direct_helpers(self) -> None:
        from tui.components.log_panel import LogPanel

        panel = LogPanel()
        out = mock.Mock()
        status = mock.Mock()
        panel.query_one = mock.Mock(side_effect=[out, status, out, status, out])  # type: ignore[method-assign]
        panel.clear_log()
        panel.stop_stream()
        self.assertEqual(panel.current_service, None)

        panel._stream_generation = 3
        proc = mock.Mock()
        with mock.patch("tui.components.log_panel.terminate_process") as terminate:
            panel._set_stream_process(2, proc)
        terminate.assert_called_once_with(proc)

        panel._set_stream_process(4, proc)
        panel._write_log_line(2, "old")
        panel._stream_failed(2, "web")

    def test_log_panel_selection_and_stream_setup(self) -> None:
        from tui.components.log_panel import LogPanel
        from tui.data import ServiceInfo

        panel = LogPanel()
        web_button = mock.Mock()
        db_button = mock.Mock()
        panel.query_one = mock.Mock(side_effect=[web_button, db_button])  # type: ignore[method-assign]
        panel._start_stream = mock.Mock()  # type: ignore[method-assign]
        panel.post_message = mock.Mock()  # type: ignore[method-assign]
        services = [
            ServiceInfo("web", "core", "", "", "http", "/", "", "", "", ""),
            ServiceInfo("db", "core", "", "", "http", "/", "", "", "", ""),
        ]

        with mock.patch("tui.data.load_registry", return_value=services):
            panel._select_service("web")

        web_button.add_class.assert_called_once_with("-active")
        db_button.remove_class.assert_called_once_with("-active")
        panel._start_stream.assert_called_once_with()
        self.assertEqual(panel.post_message.call_args.args[0].service, "web")

    def test_log_panel_button_and_stream_branches(self) -> None:
        from tui.components.log_panel import LogPanel

        panel = LogPanel()
        panel._select_service = mock.Mock()  # type: ignore[method-assign]
        event = mock.Mock()
        event.button.id = "log-svc-web"
        panel.on_button_pressed(event)
        panel._select_service.assert_called_once_with("web")

        panel._current_service = None
        panel._stop_stream = mock.Mock()  # type: ignore[method-assign]
        panel._start_stream()
        panel._stop_stream.assert_called_once_with()

        proc = mock.Mock()
        panel._stream_generation = 4
        panel._set_stream_process(4, proc)
        self.assertIs(panel._stream_proc, proc)

        log = mock.Mock()
        status = mock.Mock()
        panel.query_one = mock.Mock(side_effect=[log, status])  # type: ignore[method-assign]
        panel._write_log_line(4, "line")
        panel._stream_failed(4, "web")
        log.write.assert_called_once_with("line")
        status.update.assert_called_once_with("Unable to stream logs for web")

        panel.select_service("")
        self.assertEqual(panel._current_service, None)

    def test_log_panel_start_stream_schedules_worker(self) -> None:
        from tui.components.log_panel import LogPanel

        panel = LogPanel()
        log = mock.Mock()
        status = mock.Mock()
        worker = mock.Mock()
        panel._current_service = "web"
        panel._stop_stream = mock.Mock()  # type: ignore[method-assign]
        panel.query_one = mock.Mock(side_effect=[log, status])  # type: ignore[method-assign]
        panel.run_worker = mock.Mock(return_value=worker)  # type: ignore[method-assign]

        panel._start_stream()

        panel._stop_stream.assert_called_once_with()
        log.clear.assert_called_once_with()
        status.update.assert_called_once_with("[$accent]Streaming:[/] web")
        self.assertIs(panel._stream_worker, worker)

    def test_status_badge_state_branches_and_stop_timer(self) -> None:
        from tui.components.status_badge import StatusBadge

        timer = mock.Mock()
        badge = StatusBadge("running")
        badge.set_interval = mock.Mock(return_value=timer)  # type: ignore[method-assign]
        with mock.patch.object(StatusBadge, "is_mounted", new_callable=mock.PropertyMock, return_value=True):
            badge.on_mount()
            badge.watch_state("paused")
        timer.stop.assert_called_once_with()
        badge.watch_state("dead")
        badge.watch_state("missing")

    def test_stats_and_system_format_helpers(self) -> None:
        from tui.components.stats_bar import _fmt_bytes as compact_bytes
        from tui.components.system_dashboard import _fmt_bytes, _fmt_uptime

        self.assertEqual(compact_bytes(1024), "1K")
        self.assertEqual(_fmt_bytes(1024), "1.0KB")
        self.assertEqual(_fmt_uptime(90061), "1d 1h 1m")


class MountedComponentTests(unittest.TestCase):
    def test_dialog_and_log_panel_mount_paths(self) -> None:
        from textual.app import App, ComposeResult
        from tui.components.dialogs import MessageDialog
        from tui.components.log_panel import LogPanel

        class Harness(App):
            def compose(self) -> ComposeResult:
                yield LogPanel()

        async def run() -> None:
            app = Harness()
            async with app.run_test(size=(90, 30)) as pilot:
                await pilot.pause(0.1)
                app.push_screen(MessageDialog("Title", "Body"))
                await pilot.pause(0.1)
                await pilot.press("enter")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
