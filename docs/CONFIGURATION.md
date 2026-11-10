# Configuration — 0.3 preview

Configuration loads dataclass defaults, the selected JSON file, then `SENTINEL_` environment overrides. Invalid JSON and unknown overrides fail clearly. Field names preserve underscores, for example `SENTINEL_MOTION_MIN_CONTOUR_AREA=700`. Credential fields remain strings even when numeric-looking. `.env` loading is not implemented.

Source use defaults to `config/settings.json`; select a private file with `python app.py --config config/local.json`. Desktop use copies bundled defaults once to the user data directory. Relative paths resolve against the working directory: desktop uses its private data directory; source use uses the launch directory. Software version comes from `sentinel_version.py` and cannot be pinned by an old user settings file.

## Camera profiles

The Cameras wizard writes `camera.sources`. An empty list with camera enabled retains the legacy default camera. Saving no profiles through the wizard disables the camera system. Up to eight unique device indices/names are accepted.

```json
{"camera":{"opencv_threads":1,"sources":[
  {"index":0,"name":"Entrance","enabled":true,"fps":15,"resolution":"720p",
   "motion_enabled":true,"sensitivity":30,"min_contour_area":300,
   "recording_enabled":true,"record_on_motion":true,"post_motion_seconds":10,
   "max_duration_seconds":300,"zones":[[0.1,0.1,0.8,0.8]],
   "schedule":[{"days":[0,1,2,3,4],"start":"09:00","end":"17:00"}],
   "object_detection_enabled":false}
]}}
```

Device indices are 0–15; discovery scans 0–7. FPS is 1–60. Resolutions are 360p/480p/720p/1080p, subject to actual camera capability. Motion threshold is 0–100, lower detects more. Zones are `[x,y,width,height]` fractions inside the image, up to twelve. Schedule days use Monday=0 through Sunday=6, up to 28 windows. Empty schedule means always active. Overnight windows belong to the day they start. Segment duration is 1–3600 seconds; default 300.

Profiles override global capture/motion defaults. `recording.enabled` remains a global master switch; a profile cannot enable recording while it is off. Global motion enabled also acts as a master switch. All persisted setting changes require restart. The API saves whitelisted fields only and never copies environment credentials into JSON.

## Other settings

| Section | Principal fields |
|---|---|
| recording | enabled, record_on_motion, post_motion_seconds, max_duration_seconds, codec, quality, auto_cleanup |
| storage | recordings_dir, retention_days, warning_disk_percent, critical_disk_percent, target_free_percent, cleanup_check_interval |
| database | path; SQLite WAL is initialized |
| web | host, port, use_https, ssl_cert_path, ssl_key_path, check_updates |
| security | enable_auth, admin_username, admin_password, session_secret, require_api_key, api_key |
| telegram | enabled, bot_token, chat_id, notify_motion/startup/shutdown |
| streaming | quality; live pipeline FPS follows its camera profile |

Some inherited schema fields remain reserved: streaming enabled/port/bitrate, database WAL/timeout switches, snapshots paths, logging rotation configuration and password_hash_algorithm. Do not rely on reserved fields as enforced behavior.

## Optional detection

Set a profile's `object_detection_enabled` to true for built-in people filtering. Without a model path, OpenCV's bundled HOG people detector is used. For vehicle filtering, configure `motion.object_model_path` with a `.onnx` file inside `models/`. Models elsewhere are rejected. Supported adapters accept COCO YOLO outputs `[1,84,N]`, `[1,N,84]`, or 85-column objectness variants, with 640×640 NCHW input. The user supplies the model and its license. Incompatible models show a diagnostics error rather than downloading another model.

`motion.object_confidence` defaults to 0.5; `motion.object_min_interval` defaults to one second and cannot be below 0.5 seconds. Built-in HOG scores are detector scores, not calibrated probabilities. Optional detection can miss objects and is not a safety guarantee.

## Authentication and updates

Loopback binding is default. Configure a private admin password/hash before enabling authentication or network access. Werkzeug scrypt/pbkdf2 hashes are preferred; legacy strings are accepted. Use a random persistent session secret for stable sessions. Keys go in `X-API-Key`, never URLs. Keep secrets in private configuration/process environment rather than Git.

`web.check_updates` is false by default. Enable it in Diagnostics or private JSON to check GitHub on startup and once per day. The checker sends no footage or diagnostics and never runs downloaded programs. Saving this preference requires restart.
