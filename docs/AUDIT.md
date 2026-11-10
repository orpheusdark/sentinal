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

## Remaining engineering work

Analytics now uses grouped counts and a database SUM to avoid per-camera queries and loading every size row. Directory-size traversal is on demand. Telegram sending is synchronous and can block capture; move to a bounded retry queue for strict capture latency. Loop sleep adds processing time to configured FPS; measured acquisition FPS is not a strict real-time guarantee.

Single active detector/recorder, camera index 0 discovery, legacy configuration fields, missing schema migration tooling, stale metadata after retention, process-global login lockout and lack of multi-user authorization remain documented limitations. There is no at-rest encryption, AI inference, pre-motion buffering, cloud storage, native mobile server or signed desktop release. Stop/start and shutdown races and physical camera codecs need device/soak testing. No claims of complete security or 24/7 production certification are made.
