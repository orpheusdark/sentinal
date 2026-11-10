# HTTP API

Base URL defaults to `http://127.0.0.1:5000`. Most routes return `{"success":true,"data":{...}}`; failures return `{"success":false,"error":"..."}`. Health is the exception: status/timestamp are top-level. Internal exception details stay in server logs.

| Method | Route | Result |
|---|---|---|
| GET | /api/health | Public process liveness, not camera readiness |
| GET | /api/auth/status | Session/auth flags |
| GET | /api/system/info | OS, CPU, memory, disk information |
| GET | /api/system/health | Resource assessment and camera connectivity |
| GET | /api/system/metrics | Nonblocking CPU/memory/disk snapshot |
| GET | /api/system/disk | Storage-volume status and recording directory statistics |
| GET | /api/recording/status | Current recording flag/path/status |
| GET | /api/cameras | Driver IDs, connection and status |
| GET | /api/analytics | Database totals and per-camera summaries |
| GET | /api/recordings | Filtered bounded archive |
| GET | /api/recordings/{id}/download | Attachment after storage-root containment check |
| GET | /api/motion-events | Latest events plus matching total |
| GET | /api/stream/frame | Current frame as base64 JPEG |
| GET | /api/config | Non-secret editable configuration sections |
| PUT | /api/config | Validate and persist allowed settings; restart required |

## Access control

With dashboard authentication enabled, private routes require a session from form POST `/login` (`username`, `password`, optional local `next`). Browser page requests redirect to login; unauthenticated API requests return 401. GET `/logout` clears the session. Authenticated admin sessions can use APIs without an API key. If API-key protection is enabled without session auth, protected API reads and writes require `X-API-Key`; public liveness remains accessible. Keys in query strings are rejected. When both protections are configured, an API key does not substitute for login.

JSON writes also require `Content-Type: application/json` and `X-Sentinel-Request: dashboard`. Cross-origin writes are rejected; CORS is not enabled. Credentials/settings remain admin-only under network access.

## Archive queries

`days` defaults to 7, clamped to 1–365; optional integer `camera_id` filters the database camera ID. `limit` defaults to 100, clamped to 1–500; `offset` defaults to zero. Ordering is newest first then descending ID. Response data includes recordings, count (returned rows), total (matching rows), limit and offset. Soft-deleted records are excluded. The legacy quality field returns null because historical schema does not store it.

Motion queries accept `hours` (default 24, clamped 1–8760) and optional camera_id. At most 100 latest events are returned; count is returned rows and total is the matching count. Naive ISO timestamp strings represent UTC; clients must interpret them as UTC.

## Settings example

```http
PUT /api/config
Content-Type: application/json
X-Sentinel-Request: dashboard

{"camera":{"fps":20},"recording":{"post_motion_seconds":15}}
```

Successful response: `{"success":true,"restart_required":true,"message":"Settings saved. Restart Sentinel to apply."}`. Invalid values, types or unapproved sections return 400. Missing custom write header returns 403. Request bodies are limited to 16 KiB. Downloads return 404 for missing metadata/video and 403 for a path outside configured storage. A frame with no signal returns 404. Managers unavailable at startup can return 500. No deletion API exists.
