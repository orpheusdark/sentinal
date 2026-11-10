# Installation

## Windows app

Run `Sentinel-Setup-Windows.exe`, choose **Install Sentinel**, then **Open Sentinel**. Installation is per-user, requires no Python and creates a Start menu shortcut. Close a running Sentinel instance before updating. The app is currently unsigned; signing is a release-maintainer task.

For the portable package, extract the entire ZIP and open `Sentinel.exe`. Keep `_internal` beside the executable. In the launcher, click **Start Sentinel**. The browser opens when startup completes; **Stop Sentinel** flushes recordings and closes the server. Closing the launcher also stops the service.

App binaries install to `%LOCALAPPDATA%\Programs\Sentinel`. Private settings, database, logs and recordings live separately under `%LOCALAPPDATA%\Sentinel`. Updates preserve that data. To remove the custom per-user installation, stop the app, remove its program directory and Start menu shortcut. Keep the data directory if recordings are needed. The optional Inno Setup installer supports normal Windows uninstallation.

## Run from source

Requires Python 3.11+, a modern browser and camera drivers. A camera is optional for viewing the dashboard. Install only on operating systems supported by the chosen Python/OpenCV wheels.

```powershell
git clone https://github.com/orpheusdark/sentinal.git
cd sentinal
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip setuptools
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python desktop.py
```

Windows convenience launcher: `scripts/start-windows.bat`.

Linux: `sh scripts/start-unix.sh`, or create a virtual environment with `python3 -m venv .venv`, install requirements using `.venv/bin/python -m pip`, and run `.venv/bin/python desktop.py`. Linux may require the distribution's `python3-tk`, `python3-venv` and OpenCV GUI libraries. Headless operation uses `python app.py --config config/local.json` without the desktop launcher.

The default dashboard is http://127.0.0.1:5000. First startup creates an empty database. If a camera is absent, the dashboard remains available and camera discovery retries every 30 seconds.

## Other devices

