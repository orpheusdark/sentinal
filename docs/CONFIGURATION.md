# Configuration

Configuration loads in this order: dataclass defaults, JSON file, then `SENTINEL_` environment overrides. Invalid JSON fails startup rather than silently reverting. Source defaults are `config/settings.json`; select a private file with `python app.py --config config/local.json`. The desktop launcher copies its bundled defaults into the user's data directory once, then uses that copy. Relative runtime paths resolve against the working directory (desktop: user data directory; CLI: launch directory).

Environment keys match the section followed by the complete field name. Underscores inside fields are preserved: `SENTINEL_MOTION_MIN_CONTOUR_AREA=700`, `SENTINEL_CAMERA_FPS=20`, `SENTINEL_SECURITY_ENABLE_AUTH=true`. Unknown overrides fail clearly. Overrides preserve the type of each schema field, including numeric-looking credential strings. Boolean and numeric fields are parsed. Telegram token/name/chat ID overrides are always strings. `.env` loading is not implemented.

| Section | Principal fields | Behavior |
|---|---|---|
| camera | enabled, fps, resolution, auto_reconnect, reconnect_interval | FPS 1–60; resolution 360p/480p/720p/1080p |
| motion | enabled, sensitivity, min_contour_area, morph_kernel_size, cooldown_seconds | Sensitivity 0–100; positive area/kernel |
| recording | enabled, record_on_motion, post_motion_seconds, codec, quality, auto_cleanup | Tail 0–300 seconds; low/medium/high labels |
| storage | recordings_dir, retention_days, warning_disk_percent, critical_disk_percent, target_free_percent, cleanup_check_interval | Positive retention; warning below critical; target free 1–90% |
| database | path | SQLite database location; WAL is initialized |
| web | host, port, use_https, ssl_cert_path, ssl_key_path | Loopback default; port 1–65535; HTTPS needs both files |
| security | enable_auth, admin_username, admin_password, session_secret, require_api_key, api_key | Set a private password before enabling auth |
| streaming | enabled, quality, fps | JPEG preset and configured stream status |
| telegram | enabled, bot_token, chat_id, notify_motion/startup/shutdown | Optional external metadata alerts |
| logging | level, format, logs/rotation options | Legacy fields; launcher still initializes JSON logging to logs |

Some legacy schema fields are reserved or not fully wired: streaming enabled/port/bitrate, database WAL/timeout switches, snapshot paths, logging rotation options and password_hash_algorithm. Do not rely on them as enforced behavior.

## Settings page

The UI edits only camera FPS/resolution, motion sensitivity/area, recording enabled/quality/tail and retention/critical disk/target free thresholds. Save writes only those whitelisted fields to the selected file; environment secrets are never copied into it. Restart Sentinel to apply. Environment values continue to override the file. The restore button fills the form; save is required to persist.

## Credentials

Use a private JSON config or process environment, never a committed secret. `admin_password` accepts a Werkzeug `scrypt:` or `pbkdf2:` password hash, or a legacy plain string. Prefer a hash. Generate one interactively with `werkzeug.security.generate_password_hash`; do not paste real secrets into tickets, URLs or shell history. With an unset session secret, restart invalidates sessions. For stable sessions, configure a random secret of at least 32 random bytes. API keys belong only in the `X-API-Key` header.
