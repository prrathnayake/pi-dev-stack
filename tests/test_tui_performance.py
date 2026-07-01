from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from tui import data


class FakePsutil(types.SimpleNamespace):
    def __init__(self) -> None:
        super().__init__()
        self.cpu_calls: list[object] = []

    def cpu_percent(self, interval=None, percpu=False):
        self.cpu_calls.append(interval)
        return [12.0, 13.0] if percpu else 42.0

    def cpu_count(self):
        return 2

    def virtual_memory(self):
        return types.SimpleNamespace(total=100, used=40, percent=40.0)

    def swap_memory(self):
        return types.SimpleNamespace(total=0, used=0, percent=0.0)

    def disk_usage(self, path):
        return types.SimpleNamespace(total=200, used=60, percent=30.0)

    def boot_time(self):
        return 1.0

    def net_io_counters(self):
        return types.SimpleNamespace(bytes_sent=10, bytes_recv=20)

    def sensors_temperatures(self):
        return {}


class DataPerformanceTests(unittest.TestCase):
    def tearDown(self) -> None:
        data._SYSTEM_STATS_PRIMED = False
        data._HOST_METADATA = None

    def test_system_stats_uses_non_blocking_cpu_sampling(self) -> None:
        fake_psutil = FakePsutil()
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}):
            stats = data.system_stats()

        self.assertEqual(stats.cpu_percent, 42.0)
        self.assertEqual(stats.cpu_per_core, [12.0, 13.0])
        self.assertGreaterEqual(len(fake_psutil.cpu_calls), 2)
        self.assertTrue(all(interval is None for interval in fake_psutil.cpu_calls))

    def test_docker_snapshot_checks_availability_once(self) -> None:
        calls = []
        status = data.ContainerStatus(
            name="pi-web",
            service="web",
            state="running",
            status="Up 3 minutes",
            image="web:latest",
        )
        stat = data.ContainerStats(
            name="pi-web",
            cpu_percent="1.0%",
            mem_usage="10MiB / 1GiB",
            mem_percent="1.0%",
            net_io="0B / 0B",
            block_io="0B / 0B",
        )

        with (
            mock.patch.object(data, "docker_available", side_effect=lambda: calls.append("check") or True),
            mock.patch.object(data, "_containers_from_docker", return_value=[status]),
            mock.patch.object(data, "_container_stats_from_docker", return_value={"web": stat}),
        ):
            snapshot = data.docker_snapshot()

        self.assertTrue(snapshot.available)
        self.assertEqual(calls, ["check"])
        self.assertEqual(snapshot.statuses, {"web": status})
        self.assertEqual(snapshot.stats, {"web": stat})

    def test_docker_snapshot_handles_unavailable_docker(self) -> None:
        with mock.patch.object(data, "docker_available", return_value=False):
            snapshot = data.docker_snapshot()

        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.statuses, {})
        self.assertEqual(snapshot.stats, {})


class ComponentPerformanceTests(unittest.TestCase):
    def test_service_card_skips_unchanged_state_updates(self) -> None:
        from tui.components.service_card import ServiceCard

        card = ServiceCard("web")
        card.state = "running"
        card.port = "8080"
        card.uptime = "Up"
        card.cpu = "1%"
        card.mem = "2%"
        card.profile = "core"

        touched = []
        card.remove_class = lambda *names: touched.append(("remove", names))  # type: ignore[method-assign]
        card.add_class = lambda *names: touched.append(("add", names))  # type: ignore[method-assign]
        card.query_one = lambda *args, **kwargs: touched.append(("query", args))  # type: ignore[method-assign]

        card.update_state("running", "8080", "Up", "1%", "2%", "core")

        self.assertEqual(touched, [])

    def test_service_grid_snapshot_preserves_selected_service(self) -> None:
        from tui.components.service_grid import ServiceGrid

        selected_card = mock.Mock()
        other_card = mock.Mock()
        grid = ServiceGrid()
        grid._selected = "web"
        grid._cards = {"web": selected_card, "db": other_card}

        snapshot = data.DockerSnapshot(
            statuses={
                "web": data.ContainerStatus("pi-web", "web", "running", "Up", "web:latest"),
                "db": data.ContainerStatus("pi-db", "db", "exited", "Exited", "db:latest"),
            },
            stats={},
            available=True,
        )

        with mock.patch.object(data, "load_registry", return_value=[]):
            grid.update_snapshot(snapshot)

        self.assertEqual(grid.selected_service, "web")
        selected_card.select.assert_not_called()
        selected_card.deselect.assert_not_called()

    def test_log_panel_stop_cancels_worker_and_terminates_process(self) -> None:
        from tui.components import log_panel

        panel = log_panel.LogPanel()
        worker = mock.Mock()
        proc = mock.Mock()
        panel._stream_worker = worker
        panel._stream_proc = proc
        panel._stream_generation = 4

        with mock.patch.object(log_panel, "terminate_process") as terminate:
            panel._stop_stream()

        worker.cancel.assert_called_once_with()
        terminate.assert_called_once_with(proc)
        self.assertIsNone(panel._stream_worker)
        self.assertIsNone(panel._stream_proc)
        self.assertEqual(panel._stream_generation, 5)


if __name__ == "__main__":
    unittest.main()
