# Testing — 0.3 preview

Install requirements-dev.txt in a virtual environment with updated pip/setuptools. Run:

```sh
python -m pytest -q
python -m ruff check .
python -m pip check
python -m pip_audit
python desktop.py --self-check
python -m build
```

The full local run passed 116 tests with device access. Restricted-environment runs skipped the three original hardware tests. Tests isolate configuration, SQLite and storage in temporary directories so retention cannot touch real footage.

New coverage exercises queue saturation/slow delivery, schedule boundaries and overnight windows, ignored motion outside zones, per-camera event/recording isolation, thumbnail generation, file/database reconciliation, bounded segment rotation, setup validation/persistence, JPEG playback and seek, event-to-recording links, API access control, diagnostics redaction, update version ordering and the optional ONNX adapter with synthetic model output. These tests do not establish real-world detector accuracy.

## Browser acceptance performed

An isolated local preview used synthetic footage. Camera name/zone/schedule edits saved successfully with the expected restart message. Timeline and archive thumbnails rendered. A recording opened, played and supported keyboard seeking. Diagnostics and a live GitHub update check returned usable results; update preferences saved. The wizard was checked at a narrow 390-pixel viewport with no horizontal overflow. Screenshots contain synthetic frames, not private camera footage.

## Native verification

Build with `python scripts/build_desktop.py`, then `python scripts/check_desktop.py`. On Windows build setup with `python scripts/build_windows_setup.py`. The frozen check renders pages/static resources without starting camera capture. CI targets Windows/Linux on Python 3.11/3.12. Signing is optional until credentials exist; the build input `require_windows_signing=true` fails instead of silently producing an unsigned package when signing was required.

## Remaining device and soak checks

Complete installation/update/uninstallation acceptance, simultaneous physical multi-camera capture, long-running disk pressure/reconnect, power-loss recovery and network TLS tests on target devices. Validate optional HOG/ONNX models with representative local scenes, varied lighting and false-positive/negative measurements. Real Telegram delivery was not tested with user credentials. Do not infer eight-camera capacity or critical-security reliability from synthetic tests.
