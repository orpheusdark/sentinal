# Desktop packaging and distribution

## Build

Use Python 3.11 and install requirements-dev.txt in a clean environment with updated pip/setuptools. Build on the OS and CPU architecture you intend to distribute:

```sh
python scripts/build_desktop.py
```

PyInstaller bundles OpenCV, NumPy, Flask, SQLite ORM, Tkinter, templates, static assets and sanitized default configuration. Outputs are under dist/. On Windows, distribute the complete Sentinel directory, or build the single-file per-user installer:

```sh
python scripts/build_windows_setup.py
```

The setup executable installs into the user's local Programs directory, creates a Start menu shortcut and offers to launch Sentinel. It does not need admin privileges or a preinstalled Python. Stop an existing Sentinel before an update. For standard add/remove-programs integration and an uninstaller, compile scripts/windows-installer.iss with Inno Setup after the desktop bundle build; that compiler is optional and not bundled.

## User data and upgrades

Windows data: LOCALAPPDATA/Sentinel. macOS data: ~/Library/Application Support/Sentinel. Linux data: XDG_DATA_HOME/sentinel or ~/.local/share/sentinel. `desktop.py --data-dir PATH` selects a custom data directory. Bundled defaults are copied only when no configuration exists. No credentials or user videos belong in a distribution archive.

## Cross-platform status

Windows x64 is the platform built in this session. Source launchers and a manual Actions build matrix target macOS/Linux too. Native builds cannot be cross-compiled with this recipe; ARM and Linux ABI compatibility need their own runner/device checks. Linux may need system GUI/OpenGL libraries. macOS distribution needs camera permission metadata, Developer ID signing/notarization and device testing before public release. Windows Authenticode signing similarly requires the maintainer's signing identity; no signing credentials were requested or embedded.

A package build is not proof of camera capture or a production soak test. Run the acceptance checks in TESTING.md. The portable ZIP and custom setup executable are unsigned review builds. The custom setup has no automatic updater, rollback or Add/Remove Programs registration; the Inno recipe provides conventional install/uninstall integration when compiled.

## Automation

Actions → Build desktop apps → Run workflow builds on Windows/Linux/macOS and uploads temporary artifacts. Verify workflow success before distributing artifacts. The Verify workflow runs tests, lint, resource self-check, Python build and dependency audit for pushes/pull requests. Artifacts are not automatically published as GitHub Releases.
