from __future__ import annotations

import unittest
from unittest import mock


class ActionFlowTests(unittest.TestCase):
    def test_docker_event_message_stores_event(self) -> None:
        from tui.app import DockerEventMessage
        from tui.data import DockerEvent

        event = DockerEvent("container", "start", "pi-web", "web", "running", "1")
        self.assertIs(DockerEventMessage(event).event, event)

    def test_action_progress_message_uses_correct_gerund(self) -> None:
        from tui.app import action_progress_message

        self.assertEqual(action_progress_message("start", "web"), "Starting web...")
        self.assertEqual(action_progress_message("stop", "web"), "Stopping web...")
        self.assertEqual(action_progress_message("restart", "web"), "Restarting web...")

    def test_no_selected_service_action_uses_dialog(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        app._get_selected_service = mock.Mock(return_value=None)  # type: ignore[method-assign]
        app._show_dialog = mock.Mock()  # type: ignore[method-assign]

        app._do_service_action("start")

        app._show_dialog.assert_called_once()
        self.assertIn("No service", app._show_dialog.call_args.args[0])

    def test_selected_service_action_runs_worker_thread(self) -> None:
        from tui.app import HomelabTui

        class ImmediateThread:
            def __init__(self, target, daemon=False):
                self.target = target
                self.daemon = daemon

            def start(self):
                self.target()

        app = HomelabTui()
        app._get_selected_service = mock.Mock(return_value="web")  # type: ignore[method-assign]
        app._show_loading = mock.Mock()  # type: ignore[method-assign]
        app.call_from_thread = mock.Mock()  # type: ignore[method-assign]
        with (
            mock.patch("tui.app.do_action", return_value=(0, "", "")),
            mock.patch("tui.app.threading.Thread", ImmediateThread),
        ):
            app._do_service_action("stop")

        app._show_loading.assert_called_once_with("Stopping web...")
        app.call_from_thread.assert_called_once()

    def test_handle_action_routes_all_actions(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        app.exit = mock.Mock()  # type: ignore[method-assign]
        app.action_toggle_menu = mock.Mock()  # type: ignore[method-assign]
        app._do_service_action = mock.Mock()  # type: ignore[method-assign]
        app._show_url = mock.Mock()  # type: ignore[method-assign]
        app._show_logs = mock.Mock()  # type: ignore[method-assign]

        app._handle_action("menu")
        app._handle_action("start")
        app._handle_action("url")
        app._handle_action("logs")
        app._handle_action("quit")

        app.action_toggle_menu.assert_called_once_with()
        app._do_service_action.assert_called_once_with("start")
        app._show_url.assert_called_once_with()
        app._show_logs.assert_called_once_with()
        app.exit.assert_called_once_with()

    def test_show_url_uses_dialog_for_selected_service(self) -> None:
        from tui.app import HomelabTui
        from tui.data import ServiceInfo

        app = HomelabTui()
        app._get_selected_service = mock.Mock(return_value="web")  # type: ignore[method-assign]
        app._show_dialog = mock.Mock()  # type: ignore[method-assign]
        service = ServiceInfo("web", "core", "apps", "8080", "http", "/", "", "", "", "")

        with mock.patch("tui.app.load_registry", return_value=[service]):
            app._show_url()

        app._show_dialog.assert_called_once_with("web URL", "web: http://localhost:8080/")

    def test_show_logs_switches_page_and_selects_service(self) -> None:
        from tui.app import HomelabTui

        activities = mock.Mock()
        app = HomelabTui()
        app._get_selected_service = mock.Mock(return_value="web")  # type: ignore[method-assign]
        app._switch_page = mock.Mock()  # type: ignore[method-assign]
        app.query_one = mock.Mock(return_value=activities)  # type: ignore[method-assign]

        app._show_logs()

        app._switch_page.assert_called_once_with("Activities")
        activities.select_service.assert_called_once_with("web")

    def test_show_url_dialog_branches(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        app._show_dialog = mock.Mock()  # type: ignore[method-assign]
        app._get_selected_service = mock.Mock(return_value=None)  # type: ignore[method-assign]
        app._show_url()
        app._show_dialog.assert_called_with("No service selected", "Select a service card first to view its URL.")

        app._show_dialog.reset_mock()
        app._get_selected_service = mock.Mock(return_value="missing")  # type: ignore[method-assign]
        with mock.patch("tui.app.load_registry", return_value=[]):
            app._show_url()
        app._show_dialog.assert_called_with("Unknown service", "Unknown service: missing")

    def test_show_logs_no_selection_uses_dialog(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        app._show_dialog = mock.Mock()  # type: ignore[method-assign]
        app._get_selected_service = mock.Mock(return_value=None)  # type: ignore[method-assign]

        app._show_logs()

        app._show_dialog.assert_called_once_with("No service selected", "Select a service card first to view logs.")

    def test_action_done_reports_result_and_refreshes(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        app._hide_loading = mock.Mock()  # type: ignore[method-assign]
        app._show_dialog = mock.Mock()  # type: ignore[method-assign]
        app._schedule_docker_refresh = mock.Mock()  # type: ignore[method-assign]

        app._action_done("web", "start", 0, "")
        app._show_dialog.assert_called_with("Action complete", "Start web completed.")

        app._action_done("web", "stop", 1, "")
        app._show_dialog.assert_called_with("Action failed", "stop web failed:\n\nNo error output returned.")
        self.assertEqual(app._schedule_docker_refresh.call_count, 2)

    def test_refresh_workers_and_apply_methods(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerSnapshot, SystemStats

        app = HomelabTui()
        app.run_worker = mock.Mock()  # type: ignore[method-assign]
        app._schedule_system_refresh()
        app._schedule_docker_refresh()
        self.assertEqual(app.run_worker.call_count, 2)

        stats = SystemStats(cpu_percent=1, cpu_count=1)
        stats_bar = mock.Mock()
        dashboard = mock.Mock()
        app.query_one = mock.Mock(side_effect=[stats_bar, dashboard])  # type: ignore[method-assign]
        app._apply_system_stats(stats)
        stats_bar.update_stats.assert_called_once_with(stats)
        dashboard.update_system.assert_called_once_with(stats)

        dashboard = mock.Mock()
        services = mock.Mock()
        snapshot = DockerSnapshot({}, {}, True)
        app.query_one = mock.Mock(side_effect=[dashboard, services])  # type: ignore[method-assign]
        app._apply_docker_snapshot(snapshot)
        dashboard.update_docker.assert_called_once_with(snapshot)
        services.update_snapshot.assert_called_once_with(snapshot)

    def test_load_workers_call_back_to_ui_thread(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerSnapshot, SystemStats

        app = HomelabTui()
        app.call_from_thread = mock.Mock()  # type: ignore[method-assign]
        with mock.patch("tui.app.system_stats", return_value=SystemStats(cpu_percent=2, cpu_count=1)):
            app._load_system_stats()
        self.assertEqual(app.call_from_thread.call_args.args[0], app._apply_system_stats)

        app.call_from_thread.reset_mock()
        with mock.patch("tui.app.docker_snapshot", return_value=DockerSnapshot({}, {}, True)):
            app._load_docker_snapshot()
        self.assertEqual(app.call_from_thread.call_args.args[0], app._apply_docker_snapshot)

        app.call_from_thread = mock.Mock(side_effect=Exception("closed"))  # type: ignore[method-assign]
        with mock.patch("tui.app.system_stats", return_value=SystemStats(cpu_percent=2, cpu_count=1)):
            app._load_system_stats()
        with mock.patch("tui.app.docker_snapshot", return_value=DockerSnapshot({}, {}, True)):
            app._load_docker_snapshot()

    def test_docker_event_updates_state_and_debounces_refresh(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerEvent

        grid = mock.Mock()
        app = HomelabTui()
        app.query_one = mock.Mock(return_value=grid)  # type: ignore[method-assign]
        app._schedule_debounced_docker_refresh = mock.Mock()  # type: ignore[method-assign]
        app.notify = mock.Mock()  # type: ignore[method-assign]

        app._on_docker_event(DockerEvent("container", "die", "pi-web", "web", "exited", "1"))

        grid.update_service_state.assert_called_once_with("web", "stopped")
        app._schedule_debounced_docker_refresh.assert_called_once_with()

    def test_selected_service_and_cleanup_paths(self) -> None:
        from tui.app import HomelabTui
        from tui.components.log_panel import LogPanel
        from tui.components.services_page import ServicesPage

        app = HomelabTui()
        app.on_services_page_service_selected(ServicesPage.ServiceSelected("web"))
        self.assertEqual(app._selected_service, "web")
        app.on_log_panel_service_log_selected(LogPanel.ServiceLogSelected("db"))
        self.assertEqual(app._selected_service, "db")

        app._active_page = "Dashboard"
        self.assertEqual(app._get_selected_service(), "db")

        timer = mock.Mock()
        app._system_timer = app._docker_timer = app._docker_reconcile_timer = app._idle_timer = timer
        app.on_unmount()
        self.assertEqual(timer.stop.call_count, 4)

    def test_page_switch_and_action_message_wrappers(self) -> None:
        from tui.app import HomelabTui
        from tui.components.side_panel import SidePanel

        app = HomelabTui()
        panel = mock.Mock()
        content = mock.Mock()
        child = mock.Mock()
        content.children = [child]
        page = mock.Mock()
        app.query_one = mock.Mock(side_effect=[panel, content, page])  # type: ignore[method-assign]
        app._switch_page("Services")
        panel.set_active.assert_called_once_with("Services")
        child.remove_class.assert_called_once_with("-visible")
        page.add_class.assert_called_once_with("-visible")

        app._switch_page = mock.Mock()  # type: ignore[method-assign]
        app.action_switch_page("Activities")
        app._switch_page.assert_called_once_with("Activities")
        app.on_side_panel_page_selected(SidePanel.PageSelected("Dashboard"))
        app._switch_page.assert_called_with("Dashboard")

        app._handle_action = mock.Mock()  # type: ignore[method-assign]
        app.on_action_bar_action_triggered(mock.Mock(action="start"))
        app.action_do_action("stop")
        self.assertEqual(app._handle_action.call_args_list[-2:], [mock.call("start"), mock.call("stop")])

        app._switch_page = HomelabTui._switch_page.__get__(app, HomelabTui)  # type: ignore[method-assign]
        app.query_one = mock.Mock(side_effect=[panel, content, Exception("missing")])  # type: ignore[method-assign]
        app._switch_page("Services")

    def test_debounce_and_loading_overlay_branches(self) -> None:
        from tui.app import HomelabTui

        app = HomelabTui()
        timer = mock.Mock()
        with mock.patch.object(HomelabTui, "is_running", new_callable=mock.PropertyMock, return_value=True):
            app._docker_reconcile_timer = timer
            app._schedule_debounced_docker_refresh()
            timer.reset.assert_called_once_with()

            app._docker_reconcile_timer = None
            app.set_timer = mock.Mock(return_value=timer)  # type: ignore[method-assign]
            app._schedule_debounced_docker_refresh()
            self.assertIs(app._docker_reconcile_timer, timer)

        app._schedule_docker_refresh = mock.Mock()  # type: ignore[method-assign]
        app._run_debounced_docker_refresh()
        self.assertIsNone(app._docker_reconcile_timer)
        app._schedule_docker_refresh.assert_called_once_with()

        old_overlay = mock.Mock()
        app.query = mock.Mock(return_value=[old_overlay])  # type: ignore[method-assign]
        app.mount = mock.Mock()  # type: ignore[method-assign]
        app._show_loading("Working")
        old_overlay.remove.assert_called_once_with()
        app.mount.assert_called_once()
        app._hide_loading()

    def test_selected_service_container_fallbacks_and_event_noops(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerEvent

        app = HomelabTui()
        services = mock.Mock(selected_service="web")
        app._active_page = "Services"
        app.query_one = mock.Mock(return_value=services)  # type: ignore[method-assign]
        self.assertEqual(app._get_selected_service(), "web")

        app._selected_service = "cached"
        app.query_one = mock.Mock(side_effect=Exception("missing"))  # type: ignore[method-assign]
        self.assertEqual(app._get_selected_service(), "cached")

        app.query_one = mock.Mock()  # type: ignore[method-assign]
        app._on_docker_event(DockerEvent("container", "rename", "pi-web", "web", "", "1"))
        app.query_one.assert_not_called()

        app.query_one = mock.Mock(side_effect=Exception("boom"))  # type: ignore[method-assign]
        app._on_docker_event(DockerEvent("container", "start", "pi-web", "web", "", "1"))

    def test_apply_and_show_logs_exception_branches(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerSnapshot, SystemStats

        app = HomelabTui()
        app.query_one = mock.Mock(side_effect=Exception("missing"))  # type: ignore[method-assign]
        app._apply_system_stats(SystemStats(cpu_percent=1, cpu_count=1))
        app._apply_docker_snapshot(DockerSnapshot({}, {}, True))

        app._get_selected_service = mock.Mock(return_value="web")  # type: ignore[method-assign]
        app._switch_page = mock.Mock()  # type: ignore[method-assign]
        app.query_one = mock.Mock(side_effect=Exception("missing"))  # type: ignore[method-assign]
        app._show_logs()

    def test_event_stream_thread_body(self) -> None:
        from tui.app import HomelabTui
        from tui.data import DockerEvent

        class ImmediateThread:
            def __init__(self, target, daemon=False):
                self.target = target

            def start(self):
                self.target()

        app = HomelabTui()
        app.call_from_thread = mock.Mock()  # type: ignore[method-assign]
        event = DockerEvent("container", "start", "pi-web", "web", "", "1")
        with (
            mock.patch("tui.app.docker_events", return_value=iter([event])),
            mock.patch("tui.app.threading.Thread", ImmediateThread),
        ):
            app._start_event_stream()
        app.call_from_thread.assert_called_once_with(app._on_docker_event, event)

    def test_action_bar_button_posts_expected_action(self) -> None:
        from tui.components.action_bar import ActionBar

        bar = ActionBar()
        bar.post_message = mock.Mock()  # type: ignore[method-assign]
        event = mock.Mock()
        event.button.id = "btn-restart"

        bar.on_button_pressed(event)

        message = bar.post_message.call_args.args[0]
        self.assertEqual(message.action, "restart")


if __name__ == "__main__":
    unittest.main()
