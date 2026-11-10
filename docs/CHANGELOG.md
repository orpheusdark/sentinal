# Changelog

## 0.3.0 Preview 1 — 2026-11-10

Added camera discovery/setup previews; validated independent camera profiles; per-camera workers, motion zones and weekly/overnight schedules; optional built-in people detection and local COCO ONNX people/vehicle filtering; thumbnails, linked event timeline and seekable JPEG review playback; diagnostics export and opt-in release notifications. Added bounded background Telegram retries, archive/file reconciliation and maximum video segment duration. Fixed Linux capture backend, sensitivity direction, time-based cooldown, global recording master switch and repeated error-log flooding. OpenCV defaults to one internal thread based on local component measurements. Added Windows version metadata and certificate-backed signing hooks. Windows and Linux are the supported release targets; no signing identity was supplied.

## 0.2.0 — 2026-11-10

Added native desktop launcher and Windows packaging, per-user installer builder, native build workflow, responsive dashboard redesign, archive pagination, local preview pause/refresh controls, real validated settings persistence and comprehensive operating/developer documentation.

Continuous recording now remains active when a motion event ends; post-motion stop timers apply only to motion-triggered recording. Native packages preserve executable permissions and include a macOS camera usage description.

Fixed invalid configuration JSON; underscore environment overrides; duplicate SQLite index names; SQLAlchemy health-check SQL; shared single-connection pooling; API session cleanup; recording metadata persistence; missing recording schema attributes; recording download filename/root containment; disabled recording behavior; renewed-motion tail timer; camera resolution propagation; nonexistent cleanup helpers; active/symlink cleanup safety; periodic maintenance timing; missing-camera dashboard startup; and graceful web shutdown.

Hardened session secret generation, cookie/response headers, redirect validation, API key handling, network binding, write-origin checks, HTTPS certificate verification and Telegram error redaction. Removed unused runtime dependencies, invalid unavailable asyncio-contextmanager pin and tracked runtime artifacts. Kept existing source launch and supervisors.

## Upgrade notes

Back up private data first. Default access is local only. Non-loopback binding now requires auth; enabling auth with the sample password fails. API key mode protects reads too. JSON writes require X-Sentinel-Request. Invalid config fails instead of using fallback defaults. Settings changes need restart. Historical quality is null because the schema never stored it. The inert Delete button was removed. Runtime files are untracked in the new tree but remain in Git history. Python minimum is now 3.11. Existing PHASE documents describe historical claims and are not current operating instructions.
