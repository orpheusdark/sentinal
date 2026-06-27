"""Audit monitor for Project Sentinel.

Runs as a side process that starts and supervises the main application.
It logs startup, shutdown, crashouts, component health, system metrics,
and every monitored event in structured JSON format.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import sys
import threading
import time
import ssl
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

from utils import initialize_logging, get_logger
from utils.system import ResourceMonitor, SystemInfo
from config.settings import initialize_config


class AppProcessMonitor:
    """Manage the main sentinel process and stream its stdout/stderr."""

    def __init__(self, app_script: str, app_args: Optional[List[str]] = None):
        self.app_script = Path(app_script).resolve()
        self.app_args = app_args or []
        self.process: Optional[subprocess.Popen] = None
        self.stdout_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.logger = get_logger("monitor.app")

    def start(self) -> bool:
        if self.is_running():
            return True

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(self.app_script), *self.app_args],
                cwd=self.app_script.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            self.logger.info("app_process_start", extra={
                "event": "app_process_start",
                "pid": self.process.pid,
                "script": str(self.app_script),
            })

            self._stop_event.clear()
            self.stdout_thread = threading.Thread(target=self._stream_pipe, args=(self.process.stdout, "stdout"), daemon=True)
            self.stderr_thread = threading.Thread(target=self._stream_pipe, args=(self.process.stderr, "stderr"), daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()
            return True
        except Exception as exc:
            self.logger.error("app_process_start_failed", extra={
                "event": "app_process_start_failed",
                "error": str(exc),
            })
            return False

    def stop(self) -> None:
        if not self.process:
            return

        self.logger.info("app_process_stop_requested", extra={
            "event": "app_process_stop_requested",
            "pid": self.process.pid,
        })

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
                self.logger.info("app_process_stopped", extra={
                    "event": "app_process_stopped",
                    "pid": self.process.pid,
                    "returncode": self.process.returncode,
                })
            except subprocess.TimeoutExpired:
                self.logger.warning("app_process_kill_timeout", extra={
                    "event": "app_process_kill_timeout",
                    "pid": self.process.pid,
                })
                self.process.kill()
                self.process.wait()
                self.logger.info("app_process_killed", extra={
                    "event": "app_process_killed",
                    "pid": self.process.pid,
                    "returncode": self.process.returncode,
                })
        except Exception as exc:
            self.logger.error("app_process_stop_failed", extra={
                "event": "app_process_stop_failed",
                "error": str(exc),
            })
        finally:
            self._stop_event.set()
            self.process = None

    def is_running(self) -> bool:
        return bool(self.process and self.process.poll() is None)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.is_running(),
            "pid": self.process.pid if self.process else None,
            "returncode": self.process.returncode if self.process else None,
        }

    def _stream_pipe(self, pipe: Optional[Any], stream_name: str) -> None:
        if not pipe:
            return

        for line in pipe:
            if self._stop_event.is_set():
                break
            self.logger.info("app_output", extra={
                "event": "app_output",
                "stream": stream_name,
                "text": line.rstrip("\n"),
            })

        pipe.close()


class Monitor:
    """Continuous monitor for Project Sentinel."""

    def __init__(self, app_script: str = "app.py", app_args: Optional[List[str]] = None, config_path: Optional[str] = None, check_interval: int = 15):
        self.app_script = app_script
        self.app_args = app_args or []
        self.config_path = config_path
        self.check_interval = check_interval
        self.running = False
        self.app_monitor = AppProcessMonitor(app_script, self.app_args)
        self.logger = self._setup_logging()
        self.config = self._load_config()
        self.health_url = self._build_health_url()
        self.metrics_url = self._build_metrics_url()
        self.cameras_url = self._build_cameras_url()
        self.recording_status_url = self._build_recording_status_url()

    def _setup_logging(self) -> logging.Logger:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        initialize_logging(str(log_dir), "json")
        logger = get_logger("monitor", level="INFO")
        logger.info("monitor_initialized", extra={
            "event": "monitor_initialized",
            "timestamp": datetime.utcnow().isoformat(),
        })
        return logger

    def _load_config(self) -> Any:
        try:
            return initialize_config(self.config_path) if self.config_path else initialize_config()
        except Exception as exc:
            self.logger.warning("config_load_failed", extra={
                "event": "config_load_failed",
                "error": str(exc),
            })
            return None

    def _build_health_url(self) -> str:
        use_https = bool(self.config and getattr(self.config.web, "use_https", False))
        scheme = "https" if use_https else "http"
        port = getattr(self.config.web, "port", 5000) if self.config else 5000
        return f"{scheme}://127.0.0.1:{port}/api/system/health"

    def _build_metrics_url(self) -> str:
        use_https = bool(self.config and getattr(self.config.web, "use_https", False))
        scheme = "https" if use_https else "http"
        port = getattr(self.config.web, "port", 5000) if self.config else 5000
        return f"{scheme}://127.0.0.1:{port}/api/system/metrics"

    def _build_cameras_url(self) -> str:
        use_https = bool(self.config and getattr(self.config.web, "use_https", False))
        scheme = "https" if use_https else "http"
        port = getattr(self.config.web, "port", 5000) if self.config else 5000
        return f"{scheme}://127.0.0.1:{port}/api/cameras"

    def _build_recording_status_url(self) -> str:
        use_https = bool(self.config and getattr(self.config.web, "use_https", False))
        scheme = "https" if use_https else "http"
        port = getattr(self.config.web, "port", 5000) if self.config else 5000
        return f"{scheme}://127.0.0.1:{port}/api/recording/status"

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        self.logger.info("monitor_received_signal", extra={
            "event": "monitor_received_signal",
            "signal": signum,
        })
        self.running = False

    def _http_get(self, url: str, timeout: int = 8) -> Dict[str, Any]:
        try:
            context = ssl._create_unverified_context() if url.startswith("https://") else None
            req = request.Request(url, method="GET")
            with request.urlopen(req, timeout=timeout, context=context) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body) if body else {}
                self.logger.debug("monitor_http_response", extra={
                    "event": "monitor_http_response",
                    "url": url,
                    "status": resp.status,
                    "body": data,
                })
                return {"success": True, "status": resp.status, "data": data}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            self.logger.warning("monitor_http_error", extra={
                "event": "monitor_http_error",
                "url": url,
                "status": exc.code,
                "error": body,
            })
            return {"success": False, "status": exc.code, "error": body}
        except Exception as exc:
            self.logger.error("monitor_http_exception", extra={
                "event": "monitor_http_exception",
                "url": url,
                "error": str(exc),
            })
            return {"success": False, "error": str(exc)}

    def _check_application(self) -> bool:
        if not self.app_monitor.is_running():
            self.logger.error("app_not_running", extra={
                "event": "app_not_running",
            })
            return False

        health = self._http_get(self.health_url)
        if not health.get("success") or not health.get("data") or not health["data"].get("overall_healthy", False):
            self.logger.warning("app_health_failed", extra={
                "event": "app_health_failed",
                "url": self.health_url,
                "response": health,
            })
            return False

        cameras = self._http_get(self.cameras_url)
        recording = self._http_get(self.recording_status_url)

        if not cameras.get("success"):
            self.logger.warning("camera_endpoint_failed", extra={
                "event": "camera_endpoint_failed",
                "response": cameras,
            })
            return False

        if not recording.get("success"):
            self.logger.warning("recording_status_failed", extra={
                "event": "recording_status_failed",
                "response": recording,
            })
            return False

        self.logger.info("app_components_ok", extra={
            "event": "app_components_ok",
            "camera_count": len(cameras.get("data", {}).get("data", {}).get("cameras", [])) if cameras.get("data") else None,
            "recording_status": recording.get("data"),
        })
        return True

    def _check_system(self) -> bool:
        healthy, status = ResourceMonitor.full_health_check()
        self.logger.info("system_health", extra={
            "event": "system_health",
            "healthy": healthy,
            "status": status,
        })
        return healthy

    def _log_startup(self) -> None:
        info = SystemInfo.get_system_info()
        self.logger.info("monitor_startup", extra={
            "event": "monitor_startup",
            "system": info,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def _log_shutdown(self) -> None:
        self.logger.info("monitor_shutdown", extra={
            "event": "monitor_shutdown",
            "timestamp": datetime.utcnow().isoformat(),
        })

    def run(self) -> int:
        self._setup_signal_handlers()
        self.running = True
        self._log_startup()

        if not self.app_monitor.start():
            self.logger.error("monitor_app_start_failed", extra={"event": "monitor_app_start_failed"})
            return 1

        exit_code = 0
        try:
            while self.running:
                try:
                    if not self.app_monitor.is_running():
                        self.logger.error("app_crash_detected", extra={
                            "event": "app_crash_detected",
                            "status": self.app_monitor.get_status(),
                        })
                        self.app_monitor.start()

                    app_ok = self._check_application()
                    sys_ok = self._check_system()

                    if not app_ok or not sys_ok:
                        self.logger.warning("monitor_recovery_attempt", extra={
                            "event": "monitor_recovery_attempt",
                            "app_ok": app_ok,
                            "sys_ok": sys_ok,
                        })
                        self.app_monitor.stop()
                        time.sleep(2)
                        self.app_monitor.start()

                    time.sleep(self.check_interval)
                except Exception as exc:
                    self.logger.error("monitor_loop_exception", extra={
                        "event": "monitor_loop_exception",
                        "error": str(exc),
                    })
                    time.sleep(self.check_interval)
        finally:
            self._log_shutdown()
            self.app_monitor.stop()

        return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel monitor and supervisor")
    parser.add_argument("--no-auth", action="store_true", help="Pass through to app.py to disable dashboard auth")
    parser.add_argument("--config", dest="config_file", default=None, help="Pass through to app.py config path")
    parser.add_argument("--check-interval", dest="check_interval", type=int, default=15, help="Monitor polling interval in seconds")
    parser.add_argument("--app-arg", dest="app_args", action="append", default=[], help="Additional argument to pass through to app.py")
    args = parser.parse_args()

    app_args: List[str] = []
    if args.no_auth:
        app_args.append("--no-auth")
    if args.config_file:
        app_args.extend(["--config", args.config_file])
    app_args.extend(args.app_args)

    config_path = Path(__file__).parent / "config" / "settings.json"
    monitor = Monitor(
        app_script=str(Path(__file__).parent / "app.py"),
        app_args=app_args,
        config_path=str(config_path),
        check_interval=args.check_interval,
    )
    return monitor.run()


if __name__ == "__main__":
    raise SystemExit(main())
