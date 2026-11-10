# Verification — 2026-11-10

Verified locally on Windows x64 with Python 3.11.9 in a fresh project virtual environment. Baseline checkout: `2a82a8a`. Initial dependency installation failed because `asyncio-contextmanager==1.0.0` is unavailable; that unused dependency and other unused imports' packages were removed.

| Check | Observed result |
|---|---|
| Final full pytest suite | **92 passed, no skips** in 17.00 seconds |
| Hardware tests | Earlier restricted runs skipped three camera tests; all three passed in the final run with device access |
| Coverage run | 63% across measured runtime modules in the earlier 88-pass/3-skip run; not full behavioral coverage |
| Synthetic capture pipeline | Eight generated frames recorded, finalized, decoded and persisted with metadata |
| Lifecycle | Startup without a camera and graceful shutdown tested with HTTP startup mocked |
| Windows installer logic | Payload extraction and preservation of existing user data tested with shortcut creation mocked |
| Fatal Python lint | `python -m ruff check .` passed |
| Dependency consistency | `python -m pip check` passed |
| Dependency advisories | Final `pip-audit` reports **no known vulnerabilities** in the installed environment |
| Legacy setup checker | All six setup checks passed |
| Python distribution | Source archive and wheel built successfully |
| Desktop distribution | PyInstaller Windows bundle built; bundled-resource check exit code 0 |
| Windows setup | Single-file per-user installer built from the native bundle |
| GitHub verification matrix | All six Windows/macOS/Linux jobs on Python 3.11/3.12 passed for `9b94519` |
| Native macOS/Linux | Both final native builds and frozen-resource checks passed in GitHub Actions |

The original suite had 56 passing tests and 3 hardware skips after initial corrections. Added regressions cover materially broken behavior. An earlier audit identified 21 advisory entries in old pip/setuptools tooling; both were upgraded and the final scan was clean. `requirements-verified-windows.txt` records the exact verified development/build environment, including test and audit tools; it is a platform snapshot rather than a universal runtime lock.

## Verification limits and release gates

- The in-app browser and native browser could not reach the local preview. The environment reported restricted socket access during connectivity checks. Page rendering is covered through Flask clients, but no successful browser visual/interaction test is claimed. Responsive layouts and accessibility require real-browser acceptance checks.
- Basic webcam connect/frame/manager tests passed in the final local run. Real motion footage, long-running recording/cleanup, actual Telegram delivery and private-network TLS/mobile access were not validated. Synthetic video round-trip testing passed.
- The frozen resource check exercises imports/templates/static files without launching the GUI or camera. Full GUI start/stop/install/uninstall acceptance remains necessary. Installer file behavior was tested in temporary folders with shell shortcut creation mocked; the installer was not installed into the user's real Programs directory.
- macOS/Linux native builds and resource checks passed on hosted runners. Physical camera and GUI runtime behavior on those platforms remain unverified on end-user devices. Android/iOS native apps are not provided; mobile devices use the responsive browser interface of a secured host.
- Desktop outputs lack distribution signing. Code signing/notarization and platform acceptance tests remain release-owner gates. The repository owner selected the MIT license; third-party libraries retain their own licenses. No signing secrets were accessed.
- Build/test temporary-file renames in the restricted system temp directory failed. Retrying in workspace-owned temporary directories succeeded; this did not require weakening application file writes.

Review [Audit](AUDIT.md), [Security](SECURITY.md) and [Testing](TESTING.md) for remaining risks and reproducible checks. Remote evidence: [verification matrix](https://github.com/orpheusdark/sentinal/actions/runs/42753365015), [final native build run](https://github.com/orpheusdark/sentinal/actions/runs/42753467209). Remote native success proves packaged resources and imports, not physical-device acceptance.
