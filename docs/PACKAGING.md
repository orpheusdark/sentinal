# Windows and Linux packaging

Supported release targets are Windows x64 and Linux x86-64. macOS/Apple packages are no longer produced at the owner's request.

```sh
python -m pip install -r requirements-dev.txt
python scripts/build_desktop.py
python scripts/check_desktop.py
```

Build on the target OS/architecture. PyInstaller includes Python, OpenCV, NumPy, Flask, SQLite ORM, Tk, templates, static assets and sanitized defaults. Windows binaries include version metadata. Distribute the complete onedir bundle, or build the single-file per-user setup:

```sh
python scripts/build_windows_setup.py
```

The setup installs into LOCALAPPDATA/Programs/Sentinel, creates a Start menu shortcut and preserves private data under LOCALAPPDATA/Sentinel. Close Sentinel before updating. The optional Inno Setup recipe supplies conventional Windows install/uninstall registration if compiled. The custom preview setup has no automatic updater or Add/Remove Programs registration.

On Linux, preserve executable permissions by distributing a tar.gz. GUI use may require system Tk/OpenGL libraries. Private data uses XDG_DATA_HOME/sentinel or ~/.local/share/sentinel. Python source distributions can also be installed in a virtual environment. Source version is 0.3.0rc1, corresponding to GitHub tag v0.3.0-preview.1.

## Windows signing

No signing identity was supplied, so current binaries remain unsigned. The Actions workflow signs both the application and setup when these repository secrets are configured:

- WINDOWS_SIGNING_PFX_BASE64
- WINDOWS_SIGNING_PFX_PASSWORD
- WINDOWS_SIGNING_TIMESTAMP_URL (an HTTPS RFC 3161 service)

The helper imports the certificate into the ephemeral runner's user certificate store, signs with SHA-256, verifies the result, and removes temporary certificate material. Certificate/password values are not command-line arguments. Set the manual workflow input `require_windows_signing` to true for a build that must fail if signing is unavailable. Hardware-backed/cloud signing identities require an adapted provider integration rather than exporting a PFX.

## Release handling

Checksums and MIT/third-party license notices accompany release assets. Application signing and package integrity are distinct: SHA-256 checksums do not establish publisher identity. Build success and frozen-resource checks do not substitute for actual installation/device acceptance. Signing certificates and long-running real-device validation remain release-owner requirements.
