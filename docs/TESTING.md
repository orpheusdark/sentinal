# Testing

Install `requirements-dev.txt` into an isolated environment after upgrading pip/setuptools. Run from the repository root:

```sh
python -m pytest -q
python -m ruff check .
python -m pip check
python -m pip_audit
python desktop.py --self-check
python -m build
```

Tests create independent configuration/databases under temporary directories and change working directory so retention tests cannot touch real recordings. Regression tests cover environment overrides, invalid JSON, schema creation, health SQL, login redirects/unicode passwords, API keys, cross-origin writes, settings validation/persistence, downloads/pagination/path containment, finalized recording metadata, renewed motion tails, JPEG caching/frame ownership and desktop data initialization. Original camera/motion/recording/web tests remain.

Camera integration tests may skip without a physical camera. MP4 writer tests depend on platform codec availability. A skip is not a validated hardware pass. The fatal-error linter checks undefined references/syntax, not all stylistic or typing issues.

`desktop.py --self-check` loads configuration and renders bundled pages/static resources without opening the GUI or accessing the camera. On Windows, run the frozen `dist/Sentinel/Sentinel.exe --self-check` and inspect its process exit code. This proves bundle imports/resources, not complete GUI/hardware operation.

## Acceptance checks per OS

Install as an ordinary user; start the app; allow the device's camera only through normal user-approved OS controls. Confirm live video, motion onset, resumed motion before tail expiry, finalized MP4 playback, metadata download, pagination, settings restart behavior, stop/start and window-close shutdown. Disconnect/reconnect the camera and fill a disposable test archive to exercise cleanup. Verify existing data survives application updates.

Use desktop/tablet/phone widths, keyboard-only navigation, 200% zoom, a screen reader and reduced-motion mode. Check that failures are visible and no horizontal overflow hides controls. Verify auth, TLS and cookie behavior on the actual remote-device URL. These are explicit release gates where the current host cannot provide evidence.

CI verifies supported Python versions on Windows, macOS and Linux; desktop bundles are available from a manually dispatched workflow. Consult [Verification](VERIFICATION.md) for results actually observed in this session.
