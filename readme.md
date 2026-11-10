# Sentinel

A local camera surveillance application with motion-triggered MP4 recording, a responsive dashboard, recording archive, system telemetry and optional Telegram alerts.

## Start using it

Windows: run the provided Sentinel setup executable, or extract the complete portable app and open Sentinel.exe. In the launcher choose **Start Sentinel**; the dashboard opens in your browser. Python is bundled in native builds.

From source (Python 3.11+): run `scripts/start-windows.bat` on Windows or `sh scripts/start-unix.sh` on macOS/Linux. For a headless host, install requirements.txt and run `python app.py`. The default dashboard is http://127.0.0.1:5000.

The desktop app keeps private data outside its installation folder. Network access requires configured authentication. Settings saved through the UI apply after restart. Phones/tablets use the responsive browser interface of a securely configured host; there is no native mobile camera-server app.

## Documentation

Start with [Installation](docs/INSTALLATION.md), [Features](docs/FEATURES.md) and [Configuration](docs/CONFIGURATION.md). The [documentation index](docs/README.md) covers architecture, API, security, tests, deployment, packaging, troubleshooting, audit, changelog and contributing. See [Verification](docs/VERIFICATION.md) for exact check results and remaining release gates.

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m build
```

Build a native bundle with `python scripts/build_desktop.py` on the target OS. GitHub Actions contains verification and manual desktop-build workflows. Windows builds are unsigned; macOS/Linux native artifacts require target-device verification. Historical PHASE documents are retained as development history.
