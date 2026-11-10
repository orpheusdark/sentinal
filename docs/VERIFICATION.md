# Verification — 0.3 preview, 2026-11-10

Application version: 0.3.0rc1, distributed as v0.3.0-preview.1. Supported releases: Windows x64 and Linux x86-64.

| Check | Observed result |
|---|---|
| Final full local suite | **116 passed, no skips**, 17.39 seconds with device access |
| Restricted-environment runs | Hardware tests were skipped when the camera was unavailable; earlier feature runs passed up to 111 tests with 3 skips |
| Lint / dependency consistency | Fatal Python lint, JavaScript syntax and pip check passed |
| Dependency advisories | Final pip-audit reported no known vulnerabilities |
| Python package | Source archive and wheel built successfully |
| Windows/Linux core CI | Four Python 3.11/3.12 jobs passed for core commit 22e4be6 |
| Native resource checks | Build scripts render setup/review/diagnostics pages and assets in frozen binaries |
| Signing | PowerShell syntax checked; credential-backed signing not run because no certificate exists |

## New behavior exercised

Tests cover bounded alert queue saturation and non-blocking enqueue under a stalled network sender; schedule boundaries/overnight windows; ignored motion outside zones; two independent synthetic camera pipelines; event finalization and thumbnail persistence; video segment rotation; global recording disable; archive reconciliation and companion deletion; setup JSON validation/persistence; decoded playback and seek; linked timeline; protected APIs; redacted diagnostics; update ordering and URL containment; and an optional ONNX adapter with generated output tensors.

## Browser evidence

An isolated server used generated test footage. Camera name, zone and weekday schedule edits saved successfully and showed the restart requirement. Timeline, thumbnails and playback rendered. Play/pause and keyboard seeking were checked. A content-policy issue blocking playback blob images was found and fixed. Diagnostics rendered, a real public GitHub update check completed, and update preference persistence worked. At a 390-pixel requested viewport, content width matched available viewport width with no horizontal overflow. Screenshots contain synthetic footage only.

## Scope limits

Basic webcam tests passed locally. Simultaneous physical multi-camera capacity, full installer/upgrade/uninstall acceptance, long recording/cleanup/reconnect/power-loss operation, optional model accuracy, actual Telegram delivery and remote TLS deployment remain to be checked on target devices. In-app playback is a five-FPS JPEG review preview; original downloads retain recording FPS and recordings have no audio. Optional vehicle detection requires a user-supplied compatible local model. Eight profile slots do not certify eight-camera performance.

The Windows signing workflow is prepared, but no signing identity was supplied. Current packages remain unsigned. Model weights and signing secrets were not downloaded or fabricated. The MIT license and third-party notices accompany releases.

Historical [0.2 verification](releases/0.2.0-verification.md) is retained separately. See [Testing](TESTING.md), [Efficiency](EFFICIENCY.md) and [Audit](AUDIT.md) for interpretation and remaining work. Core CI evidence: [Windows/Linux verification](https://github.com/orpheusdark/sentinal/actions/runs/42759396443).
