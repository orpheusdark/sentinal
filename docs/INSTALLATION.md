# Install Sentinel — Windows and Linux

Download the packages from [GitHub Releases](https://github.com/orpheusdark/sentinal/releases). Choose the correct OS/architecture and verify the accompanying SHA256SUMS.txt.

## Windows x64

Run Sentinel-Setup-Windows.exe, choose Install Sentinel, then Open Sentinel. The per-user setup includes Python and creates a Start menu shortcut. Alternatively, extract the full portable archive and open Sentinel/Sentinel.exe; keep _internal beside it. Current preview packages are unsigned because no certificate has been configured.

In the launcher choose Start Sentinel, then use Cameras to detect devices, preview framing and configure profiles. Save and restart to apply. The dashboard defaults to http://127.0.0.1:5000. Missing cameras do not prevent the dashboard opening. Stop Sentinel finalizes recordings. Closing the launcher stops the service.

Binaries install under LOCALAPPDATA/Programs/Sentinel; private settings, logs, SQLite and recordings live under LOCALAPPDATA/Sentinel. Updates preserve private data. Close the app before updating. The custom preview installer is removed by deleting its program directory and Start menu shortcut after stopping it; retain private data if required. The optional Inno Setup recipe provides standard Windows uninstall registration.

## Linux x86-64

Extract Sentinel-Linux-x86_64.tar.gz and run ./Sentinel/Sentinel. Preserve executable permissions. The system may need Tk/OpenGL libraries supported by the bundled Python/OpenCV build. Data uses XDG_DATA_HOME/sentinel or ~/.local/share/sentinel. Camera drivers and device permissions are configured through normal OS tools by the user.

## From source

Requires Python 3.11+, a modern browser and compatible camera drivers. Create a virtual environment, install requirements.txt, then run desktop.py with that environment's Python. Windows convenience launcher: scripts/start-windows.bat. Linux: sh scripts/start-unix.sh. For headless use run python app.py --config config/local.json after installing dependencies. The desktop --data-dir option selects another private data directory.

## First-use checklist

Start with one camera at 720p/15 FPS. Verify a preview, motion-triggered recording, timeline/thumbnail/playback and an original download. Review the Diagnostics screen before adding feeds. Optional people/vehicle filtering is off by default; vehicle detection requires a local compatible model. Schedules use the host-local timezone. Changes require restart.

Windows and Linux are the supported native targets. Phones/tablets can view a secured host in a browser; no native mobile camera-server app is included. Configure authentication and TLS before remote access; do not forward the default local HTTP port to the public Internet. See [Deployment](DEPLOYMENT.md), [Security](SECURITY.md), [Packaging](PACKAGING.md) and [Efficiency](EFFICIENCY.md).
