# Repository audit

Audit baseline: 2a82a8a. Scope: application lifecycle, camera/motion/recording/storage, SQLAlchemy schema and queries, web/API/auth, browser code, dependency imports, runtime artifacts, packaging and documentation.

| Finding | Fix / disposition |
|---|---|
| Invalid triple-quoted header in JSON | Valid JSON example; malformed config fails closed |
| Environment fields split on every underscore | Schema-aware section/complete-field matching |
| Predictable signing key and unchecked login next | Random fallback key and local redirect validation |
| Public detailed system info / permissive CORS | Protected system routes; no global CORS |
| API keys bypass read routes and accepted URL query | Header-only constant-time checks for private reads/writes |
| Fake settings success | Whitelisted validation and atomic save, restart explicitly required |
| Duplicate SQLite global index names | Unique table-specific names |
| StaticPool shares one connection across threads | Default file-database connection pool |
| Raw SQL string fails SQLAlchemy 2 | text() health query |
| API sessions not reliably released | Request-owned teardown cleanup |
| Recording persistence opened a session per frame without saving | One finalized metadata insert after writer release |
| Nonexistent quality/video_path model attributes | Compatible null quality and correct filepath download |
| Recording disabled ignored / old tail stops renewed motion | Honor enable flags and reset tail on motion |
| Storage helpers missing and wrong volume | Configured root/volume and existing size formatter |
| Cleanup could target active files/symlinks | Containment and active-file exclusion |
| Maintenance assumed fixed 15 FPS | Monotonic periodic checks and regular retention |
| Repeated JPEG encode per client | Cache encoding per frame/quality; own frame copy |
| Broken dashboard method, memory IDs, no-op controls | Rewrite polling and controls; align IDs; explicit errors |
| Unbounded archive reads and HTML interpolation | Bounded pagination and safe DOM rendering |
| Unavailable dependency blocks install | Remove unused asyncio helper and unused libraries |
| Monitor disables TLS verification | Default validating context |
| Autostart disables auth | Preserve configured authentication |
| Runtime database/logs/bytecode committed | Remove from current tracked tree and add ignores |

## 0.3 follow-up fixes

Independent camera workers replace the single active detector/recorder. Linux camera capture now uses the platform backend. Background alert delivery removes Telegram network latency from frame processing. Event writes are throttled, cooldown is based on elapsed time, and sensitivity direction matches the UI. File cleanup reconciles database metadata and removes thumbnails. Continuous videos rotate into bounded segments. Wizard, zones, schedules, optional local object filtering, review playback, diagnostics and opt-in update checks are implemented and tested.

## Remaining engineering work

Validate simultaneous physical cameras, long-running storage/reconnect/power-loss scenarios and model accuracy. Current optional inference runs in its camera worker and can reduce that feed's FPS. The preview player decodes JPEG frames at five FPS and is not full-rate video playback. No source audio is captured. Windows signing is prepared but no certificate exists. No at-rest encryption, multi-user roles, RTSP provisioning, cloud backup, native phone server or automatic software installation is provided. Codecs, drivers and device capacity require target-device testing.
