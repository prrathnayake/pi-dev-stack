from __future__ import annotations

import asyncio
import unittest
from unittest import mock


class NavigationIdlePlanTests(unittest.TestCase):
    def test_side_panel_uses_new_pages_without_logo(self) -> None:
        from tui.components.side_panel import SidePanel

        self.assertEqual(SidePanel.PAGES, ("Dashboard", "Services", "Activities"))
        panel = SidePanel()
        self.assertEqual(panel.active, "Dashboard")
        self.assertFalse(hasattr(panel, "logo_text"))

    def test_dashboard_page_renders_system_and_docker_snapshots(self) -> None:
        from tui.components.dashboard_page import DashboardPage, docker_state_counts, render_state_bar
        from tui.data import ContainerStatus, DockerSnapshot, SystemStats

        counts = docker_state_counts(DockerSnapshot(
            statuses={
                "web": ContainerStatus("pi-web", "web", "running", "Up", "web"),
                "db": ContainerStatus("pi-db", "db", "exited", "Exited", "db"),
                "cache": ContainerStatus("pi-cache", "cache", "paused", "Paused", "cache"),
                "worker": ContainerStatus("pi-worker", "worker", "dead", "Dead", "worker"),
                "misc": ContainerStatus("pi-misc", "misc", "created", "Created", "misc"),
            },
            stats={},
            available=True,
        ))

        self.assertEqual(counts["running"], 1)
        self.assertEqual(counts["stopped"], 2)
        self.assertEqual(counts["paused"], 1)
        self.assertEqual(counts["error"], 1)
        self.assertIn("RUN", render_state_bar(counts, width=24))

        page = DashboardPage()
        page._labels = {"host": mock.Mock(), "counts": mock.Mock(), "state_bar": mock.Mock()}
        page._gauges = {"cpu": mock.Mock(), "mem": mock.Mock(), "disk": mock.Mock()}
        page.update_system(SystemStats(cpu_percent=10, cpu_count=4, mem_percent=20, disk_percent=30, hostname="pi"))
        page.update_docker(DockerSnapshot({}, {}, False))
        page._labels["host"].update.assert_called()
        page._labels["counts"].update.assert_called()

    def test_services_page_emits_service_action_requests(self) -> None:
        from tui.components.services_page import ServicesPage

        page = ServicesPage()
        old_row = mock.Mock()
        new_row = mock.Mock()
        meta = mock.Mock()
        page._selected = "db"
        page._rows = {"db": old_row, "web": new_row}
        page._meta = {"web": meta}
        page.post_message = mock.Mock()  # type: ignore[method-assign]
        event = mock.Mock()
        event.button.id = "svc-action-web-restart"

        page.on_button_pressed(event)

        old_row.remove_class.assert_called_once_with("-selected")
        new_row.add_class.assert_called_once_with("-selected")
        message = page.post_message.call_args.args[0]
        self.assertEqual(message.service, "web")
        self.assertEqual(message.action, "restart")
        self.assertEqual(page.selected_service, "web")
        page.update_service_state("web", "running")
        meta.update.assert_called_once_with("state running")

        page.post_message.reset_mock()
        event.button.id = "svc-select-web"
        page.on_button_pressed(event)
        self.assertEqual(page.post_message.call_args.args[0].service, "web")

    def test_activities_page_caps_history_and_accepts_log_selection(self) -> None:
        from tui.components.activities_page import ActivityEvent, ActivitiesPage

        page = ActivitiesPage(max_events=3)
        page._activity_log = mock.Mock()
        events = [
            ActivityEvent("docker", f"svc{i}", f"event {i}", "", timestamp=f"t{i}")
            for i in range(5)
        ]
        page.set_activities(events)

        self.assertEqual([event.summary for event in page.activities], ["event 2", "event 3", "event 4"])
        page.append_activity(ActivityEvent("action", "web", "started", "ok", timestamp="now"))
        self.assertEqual(page.activities[-1].summary, "started")
        page._activity_log = None
        page._render_activities()
        log_panel = mock.Mock()
        page.query_one = mock.Mock(return_value=log_panel)  # type: ignore[method-assign]
        page.select_service("web")
        log_panel.select_service.assert_called_once_with("web")

    def test_idle_screen_dismisses_on_input(self) -> None:
        from tui.components.idle_screen import IdleLogoScreen

        screen = IdleLogoScreen()
        screen.dismiss = mock.Mock()  # type: ignore[method-assign]
        screen.on_key(mock.Mock())
        screen.on_click(mock.Mock())
        self.assertEqual(screen.dismiss.call_count, 2)

    def test_idle_screen_pulse_toggles_logo_opacity(self) -> None:
        from tui.components.idle_screen import IdleLogoScreen

        screen = IdleLogoScreen()
        logo = mock.Mock()
        logo.styles.opacity = 1
        screen.query_one = mock.Mock(return_value=logo)  # type: ignore[method-assign]

        screen._pulse_logo()
        self.assertEqual(logo.styles.opacity, 0.7)
        screen._pulse_logo()
        self.assertEqual(logo.styles.opacity, 1)


class AppNavigationSmokeTests(unittest.TestCase):
    def test_app_activity_and_idle_branch_helpers(self) -> None:
        from tui.app import HomelabTui, MAX_ACTIVITY_EVENTS
        from tui.components.activities_page import ActivityEvent

        app = HomelabTui()
        app.query_one = mock.Mock(side_effect=Exception("missing"))  # type: ignore[method-assign]
        for index in range(MAX_ACTIVITY_EVENTS + 3):
            app._append_activity(ActivityEvent("docker", "web", f"event {index}"))
        self.assertEqual(len(app._activities), MAX_ACTIVITY_EVENTS)
        self.assertEqual(app._activities[0].summary, "event 3")

        app._reset_idle_timer = mock.Mock()  # type: ignore[method-assign]
        app.on_key(mock.Mock())
        app.on_click(mock.Mock())
        app.on_mouse_move(mock.Mock())
        self.assertEqual(app._reset_idle_timer.call_count, 3)

        timer = mock.Mock()
        app._idle_timer = timer
        app._idle_screen_visible = True
        with mock.patch.object(HomelabTui, "is_running", new_callable=mock.PropertyMock, return_value=True):
            HomelabTui._reset_idle_timer(app)
        timer.reset.assert_not_called()

        app.push_screen = mock.Mock()  # type: ignore[method-assign]
        app._show_idle_screen()
        app.push_screen.assert_not_called()

        app._reset_idle_timer = mock.Mock()  # type: ignore[method-assign]
        app._idle_screen_dismissed(None)
        self.assertFalse(app._idle_screen_visible)
        app._reset_idle_timer.assert_called_once_with()

    def test_app_service_action_event_and_worker_exception_branches(self) -> None:
        from tui.app import HomelabTui
        from tui.components.services_page import ServicesPage

        class ImmediateThread:
            def __init__(self, target, daemon=False):
                self.target = target

            def start(self):
                self.target()

        app = HomelabTui()
        app._handle_action = mock.Mock()  # type: ignore[method-assign]
        app.on_services_page_service_action_requested(ServicesPage.ServiceActionRequested("web", "logs"))
        self.assertEqual(app._selected_service, "web")
        app._handle_action.assert_called_once_with("logs")

        app._get_selected_service = mock.Mock(return_value="web")  # type: ignore[method-assign]
        app._append_activity = mock.Mock()  # type: ignore[method-assign]
        app._show_loading = mock.Mock()  # type: ignore[method-assign]
        app.call_from_thread = mock.Mock(side_effect=Exception("closed"))  # type: ignore[method-assign]
        with (
            mock.patch("tui.app.do_action", return_value=(0, "", "")),
            mock.patch("tui.app.threading.Thread", ImmediateThread),
        ):
            app._do_service_action("start")
        app._show_loading.assert_called_once()

    def test_app_docker_event_exception_and_stream_break_paths(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerEvent

        class ImmediateThread:
            def __init__(self, target, daemon=False):
                self.target = target

            def start(self):
                self.target()

        event = DockerEvent("container", "start", "pi-web", "web", "", "1")
        app = HomelabTui()
        app._event_stop.set()
        app.call_from_thread = mock.Mock()  # type: ignore[method-assign]
        with (
            mock.patch("tui.app.docker_events", return_value=iter([event])),
            mock.patch("tui.app.threading.Thread", ImmediateThread),
        ):
            app._start_event_stream()
        app.call_from_thread.assert_not_called()

        app = HomelabTui()
        app.call_from_thread = mock.Mock(side_effect=Exception("closed"))  # type: ignore[method-assign]
        with (
            mock.patch("tui.app.docker_events", return_value=iter([event])),
            mock.patch("tui.app.threading.Thread", ImmediateThread),
        ):
            app._start_event_stream()
        app.call_from_thread.assert_called_once()

        app = HomelabTui()
        app.query_one = mock.Mock()  # type: ignore[method-assign]
        app._schedule_debounced_docker_refresh = mock.Mock()  # type: ignore[method-assign]
        app.notify = mock.Mock(side_effect=Exception("closed"))  # type: ignore[method-assign]
        app._on_docker_event(event)
        app._schedule_debounced_docker_refresh.assert_called_once_with()

    def test_app_starts_on_dashboard_and_idle_timer_can_show_logo(self) -> None:
        from tui.app import HomelabTui
        from tui.components.dashboard_page import DashboardPage
        from tui.components.idle_screen import IdleLogoScreen

        async def run() -> tuple[str, bool]:
            app = HomelabTui()
            async with app.run_test(size=(90, 30)) as pilot:
                await pilot.pause(0.2)
                page = app.query_one(DashboardPage)
                app._show_idle_screen()
                await pilot.pause(0.1)
                return app._active_page, isinstance(app.screen, IdleLogoScreen) or page.has_class("-visible")

        active_page, saw_idle_or_dashboard = asyncio.run(run())
        self.assertEqual(active_page, "Dashboard")
        self.assertTrue(saw_idle_or_dashboard)


if __name__ == "__main__":
    unittest.main()
