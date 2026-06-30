from __future__ import annotations

import io
import json
import subprocess
import sys
import types
import unittest
from unittest import mock

from tui import data


class DataHelperTests(unittest.TestCase):
    def tearDown(self) -> None:
        data._DOCKER = None
        data._REGISTRY = None
        data._HOST_METADATA = None
        data._SYSTEM_STATS_PRIMED = False

    def test_service_info_url_variants_and_registry_filters(self) -> None:
        core = data.ServiceInfo("web", "core", "apps", "8080", "http", "/", "", "yes", "", "")
        extra = data.ServiceInfo("worker", "extras", "apps", "", "http", "/", "", "", "", "custom")

        with mock.patch.object(data, "load_registry", return_value=[core, extra]):
            self.assertEqual(data.service_names(), ["web", "worker"])
            self.assertEqual(data.core_services(), ["web"])
            self.assertEqual(data.extra_services(), ["worker"])

        self.assertTrue(core.has_web)
        self.assertTrue(core.is_tunnable)
        self.assertEqual(core.url, "web: http://localhost:8080/")
        self.assertEqual(extra.url, "custom")
        self.assertEqual(
            data.ServiceInfo("db", "core", "db", "", "http", "/", "", "", "", "").url,
            "db has no web UI",
        )

    def test_is_service_uses_registry(self) -> None:
        with mock.patch.object(data, "load_registry", return_value=[
            data.ServiceInfo("web", "core", "apps", "", "http", "/", "", "", "", "")
        ]):
            self.assertTrue(data.is_service("web"))
            self.assertFalse(data.is_service("missing"))

    def test_docker_command_detection_branches(self) -> None:
        with mock.patch("tui.data.shutil.which", return_value=None):
            self.assertEqual(data._docker_cmd(), ["docker"])

        ok = types.SimpleNamespace(returncode=0)
        fail = types.SimpleNamespace(returncode=1)
        with (
            mock.patch("tui.data.shutil.which", return_value="/usr/bin/docker"),
            mock.patch("tui.data.subprocess.run", return_value=ok),
        ):
            self.assertEqual(data._docker_cmd(), ["/usr/bin/docker"])

        with (
            mock.patch("tui.data.shutil.which", return_value="/usr/bin/docker"),
            mock.patch("tui.data.subprocess.run", side_effect=[fail, ok]),
        ):
            self.assertEqual(data._docker_cmd(), ["sudo", "docker"])

    def test_container_parsers_ignore_bad_lines(self) -> None:
        status_line = json.dumps({
            "Name": "pi-web",
            "State": "running",
            "Status": "Up 2 minutes",
            "Image": "web:latest",
            "Ports": "8080",
        })
        result = types.SimpleNamespace(returncode=0, stdout=f"\nnot json\n{status_line}\n")

        with (
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch.object(data, "load_registry", return_value=[
                data.ServiceInfo("web", "core", "apps", "", "http", "/", "", "", "", "")
            ]),
            mock.patch("tui.data.subprocess.run", return_value=result),
        ):
            statuses = data._containers_from_docker()

        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].service, "web")
        self.assertEqual(statuses[0].uptime, "Up 2 minutes")

        stats_result = types.SimpleNamespace(
            returncode=0,
            stdout="/pi-web\t1%\t2MiB / 1GiB\t3%\t0B / 0B\t0B / 0B\nbad\n",
        )
        with (
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch.object(data, "load_registry", return_value=[]),
            mock.patch("tui.data.subprocess.run", return_value=stats_result),
        ):
            stats = data._container_stats_from_docker()

        self.assertEqual(stats["web"].cpu_percent, "1%")

    def test_run_homelab_and_action_forward_to_cli(self) -> None:
        result = types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        with mock.patch("tui.data.subprocess.run", return_value=result) as run:
            self.assertEqual(data.action("web", "restart", timeout=7), (0, "ok", ""))

        self.assertIn("homelab", run.call_args.args[0][0])
        self.assertEqual(run.call_args.args[0][-2:], ["web", "restart"])

        with mock.patch("tui.data.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)):
            code, out, err = data.run_homelab("web")

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("timed out", err)

    def test_log_process_helpers(self) -> None:
        proc = mock.Mock()
        proc.stdout = io.StringIO("one\ntwo\n")
        proc.poll.return_value = None

        self.assertEqual(list(data.iter_process_lines(proc)), ["one", "two"])
        proc.wait.assert_called_once()

        proc.wait.reset_mock()
        proc.wait.side_effect = [subprocess.TimeoutExpired("x", 1), None]
        data.terminate_process(proc, timeout=0.01)
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()

    def test_docker_events_parse_json_and_skip_noise(self) -> None:
        proc = mock.Mock()
        proc.stdout = io.StringIO('\nnot-json\n{"Action":"start","Type":"container","Actor":{"Attributes":{"name":"pi-web","state":"running"}},"Time":42}\n')

        with (
            mock.patch.object(data, "docker_available", return_value=True),
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch.object(data, "load_registry", return_value=[]),
            mock.patch("tui.data.subprocess.Popen", return_value=proc),
        ):
            events = list(data.docker_events())

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].service, "web")
        self.assertTrue(events[0].is_state_change)

    def test_pull_progress_parses_layers(self) -> None:
        lines = [
            "abc: Pulling fs layer\n",
            "abc: Downloading 1 MB/2 MB\n",
            "abc: Pull complete\n",
        ]
        proc = mock.Mock()
        proc.stdout = lines

        with (
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch.object(data, "load_registry", return_value=[]),
            mock.patch("tui.data.subprocess.Popen", return_value=proc),
        ):
            snapshots = list(data.pull_progress("web"))

        self.assertEqual(round(snapshots[1]["abc"].percent or 0), 50)
        self.assertTrue(snapshots[-1]["abc"].completed)

    def test_wait_and_state_helpers(self) -> None:
        running = types.SimpleNamespace(returncode=0, stdout="running\n")
        missing = types.SimpleNamespace(returncode=1, stdout="")

        with (
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch("tui.data.subprocess.run", return_value=running),
        ):
            self.assertTrue(data.wait_for_running("web", timeout=0.1))
            self.assertEqual(data.container_state("web"), "running")

        with (
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch("tui.data.subprocess.run", return_value=missing),
            mock.patch("tui.data.time.sleep"),
        ):
            self.assertFalse(data.wait_for_running("web", timeout=0.0))
            self.assertEqual(data.container_state("web"), "missing")

    def test_start_service_success_failure_and_unknown(self) -> None:
        service = data.ServiceInfo("web", "extras", "apps", "", "http", "/", "", "", "", "")

        with mock.patch.object(data, "load_registry", return_value=[]):
            unknown = data.start_service("missing")
        self.assertFalse(unknown.success)

        ok = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        fail = types.SimpleNamespace(returncode=1, stdout="", stderr="bad")
        with (
            mock.patch.object(data, "load_registry", return_value=[service]),
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch("tui.data.subprocess.run", return_value=ok),
        ):
            self.assertTrue(data.start_service("web").success)

        with (
            mock.patch.object(data, "load_registry", return_value=[service]),
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch("tui.data.subprocess.run", return_value=fail),
        ):
            self.assertIn("Failed", data.start_service("web").message)

        with (
            mock.patch.object(data, "load_registry", return_value=[service]),
            mock.patch.object(data, "docker_cmd", return_value=["docker"]),
            mock.patch("tui.data.subprocess.run", side_effect=subprocess.TimeoutExpired("x", 1)),
        ):
            self.assertIn("Error", data.start_service("web").message)

    def test_system_stats_import_error_fallback(self) -> None:
        original = sys.modules.pop("psutil", None)
        try:
            with mock.patch.dict(sys.modules, {"psutil": None}):
                stats = data.system_stats()
        finally:
            if original is not None:
                sys.modules["psutil"] = original

        self.assertEqual(stats.cpu_percent, 0.0)


if __name__ == "__main__":
    unittest.main()
