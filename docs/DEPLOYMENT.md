# Deployment

## Local appliance

Run the desktop launcher for interactive use. For unattended source use, run `python app.py --config config/local.json` under a supervised process with its working directory fixed to the intended data directory. The legacy Windows Task Scheduler helper now preserves configured authentication. `--no-auth` is retained for compatibility and forces loopback binding. Do not use multiple supervisors simultaneously or run multiple instances against the same camera/database.

The monitor/watchdog scripts remain available. The monitor now validates HTTPS certificates; deploy a properly trusted certificate chain. The public `/api/health` endpoint reports HTTP process liveness only. `/api/system/health` includes camera/resource state and is protected when authentication is enabled.

## Remote browser, phone or tablet

Run the camera server on Windows/Linux; a mobile browser connects to it. Configure a private admin password/hash, enable security.enable_auth, set a random persistent session secret, and enable HTTPS with certificate and key paths. Then bind web.host to the intended private interface and choose a permitted port. Keep firewall access restricted to intended clients or a private VPN. Do not disable authentication for convenience. A phone's localhost points to the phone, not to the Sentinel host.

The responsive UI supports viewing and settings from modern browsers; this update does not create Android/iOS native apps or capture a phone camera remotely. Test your actual certificate, hostname, proxy setup and mobile browser. No firewall, router or system privacy settings are changed automatically.

## Backups and upgrades

Stop Sentinel to finalize recordings, then back up the data directory, configuration and SQLite database (including WAL/SHM if copying an active database; prefer SQLite backup API when online). Verify recovery in a separate directory. Record the installed version and dependency lock. Install new binaries separately from private data, restart and inspect logs. Keep a previous bundle for rollback. Schema creation is additive; there is no migration framework or automatic destructive migration.

## Packaging

Native executables are built with PyInstaller on each target OS/architecture. Windows per-user installer and optional Inno Setup definition are in scripts/. GitHub Actions uploads build artifacts without publishing releases or embedding signing credentials. See [Packaging](PACKAGING.md) for commands and release limitations.
