# HTTP API — 0.3 preview

Default base: `http://127.0.0.1:5000`. Normal JSON responses use `{"success":true,"data":{...}}`; failures use `{"success":false,"error":"..."}`. Public liveness is the exception and returns status/timestamp at the top level.

| Method | Route | Result |
|---|---|---|
| GET | /api/health | Public HTTP process liveness |
| GET | /api/auth/status | Session/authentication flags |
| GET | /api/system/info, /api/system/health, /api/system/metrics | Protected system information, health and telemetry |
| GET | /api/system/disk | Recording-volume and storage information |
| GET | /api/recording/status | Aggregate recording flag; legacy first-video field retained |
| GET | /api/cameras | Driver IDs, database IDs, indices, names and connectivity |
| GET | /api/analytics | Non-deleted archive totals and grouped camera counts |
| GET | /api/recordings | Paginated archive |
| GET | /api/recordings/{id}/download | Original file attachment |
| GET | /api/recordings/{id}/thumbnail | JPEG thumbnail; legacy rows get a decoded first-frame fallback |
| GET | /api/recordings/{id}/playback | Duration/FPS/dimensions and review preview metadata |
| GET | /api/recordings/{id}/frame?time=2.5 | JPEG frame at a non-negative finite time |
| GET | /api/motion-events | Recent events and matching total |
| GET | /api/timeline | Recent events linked to available recordings |
| GET | /api/stream/frame?camera_id=2 | Base64 JPEG from selected database camera ID; stale frames return 404 |
| GET | /api/camera-setup | Validated profiles and setup capabilities |
| POST | /api/camera-setup/discover | Bounded local camera discovery |
| POST | /api/camera-setup/preview | Snapshot using index/fps/resolution; active feeds are not reconfigured |
| PUT | /api/camera-setup | Persist `{profiles:[...]}` and require restart |
| GET, PUT | /api/config | Non-secret defaults / validated editable patch |
| GET | /api/diagnostics | Redacted process, camera, queue and update status |
| GET | /api/updates | Current cached update state |
| POST | /api/updates/check | Start a rate-limited background GitHub check |

HTML pages: `/`, `/recordings`, `/cameras/setup`, `/settings`, `/diagnostics`, `/login`.

## Access and writes

When enabled, dashboard authentication protects private routes. Browser page requests redirect to login; API requests without a session return 401. POST `/login` uses username/password and an optional local redirect. GET `/logout` clears the session. Authenticated admin sessions can use the APIs without a separate key. API-key-only mode requires `X-API-Key` for private reads and writes. A key does not substitute for login when session authentication is configured.

JSON writes require `Content-Type: application/json` and `X-Sentinel-Request: dashboard`. Cross-origin writes are rejected and CORS is not enabled. Bodies are limited to 128 KiB to accommodate bounded multi-camera profiles. Unknown fields/types/ranges return 400; missing request headers return 403. Discovery/preview already in progress returns 409. Hardware capability is not guaranteed by successful configuration validation.

## Query bounds

Archive: days defaults to 7 (1–365), limit to 100 (1–500), offset to zero, optional integer database camera_id. Newest first; response includes recordings, count, total, limit and offset. Deleted records are excluded. Historical quality remains null because the schema never stored it.

Events/timeline: hours defaults to 24, bounded 1–8760, optional camera_id. Events return at most 100 rows, timeline at most 200 events with up to 500 candidate recordings for matching. Naive ISO timestamps represent UTC. Schedules use host-local time, not these UTC event strings.

## Review and diagnostics limits

Playback is a seekable JPEG preview targeting 5 FPS, not a transcoded video or audio stream. At most four local decoders are cached; idle decoders expire after two minutes. All recording paths are contained under the storage root. A deleted/missing recording returns 404; invalid playback time returns 400; unsupported decode returns 415. Downloads preserve full source frame rate.

Diagnostics intentionally omit credentials, hostnames, IP addresses and paths. Camera names remain visible as configured. Update status is cached; only explicit checks or an opt-in startup/daily setting contact GitHub. A failed update check never changes installed software.
