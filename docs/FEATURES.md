# Features and use — 0.3 preview

## Camera wizard and independent feeds

Open **Cameras**, detect local devices, select a feed, capture a preview and choose resolution/FPS. Manual device indices are supported. Name each camera and set its motion threshold, recording mode, post-motion tail and maximum segment duration. Save, then restart Sentinel.

Each configured camera has independent detector, event, recording and preview state. Up to eight profiles can be configured; that is a configuration limit, not a promise that every computer can record eight feeds. Use Diagnostics to check observed FPS, processing time, stale frames, memory and errors. The Overview selector switches live feeds.

## Zones, schedules and optional object filtering

Draw rectangular motion zones or enter normalized coordinates using keyboard-accessible fields. No zones means the whole image. Add weekday/time windows for each camera; no windows means always active. Times use the host computer's local timezone and overnight windows are supported. Outside a schedule, live preview continues but events/recording stop.

Object filtering is off by default. The built-in HOG mode detects people. For people and vehicles, place a compatible COCO YOLO ONNX detection model under the private data directory's `models/` folder and set `motion.object_model_path`. No model is downloaded automatically. Detection is interval-limited and may lower capture FPS. See [Configuration](CONFIGURATION.md) for supported output format and [Testing](TESTING.md) for validation limits.

## Review and playback

The Review page combines a filtered event timeline and paginated archive. Timeline items link to finalized recordings when available. Cards show thumbnails, duration and size. Play/seek opens a keyboard-accessible dialog with pause, position slider and download controls. The server provides a 5 FPS JPEG review preview; download the original for full frame rate. No microphone/audio recording is implemented.

## Recording and alerts

Motion-triggered and continuous recording both support bounded file segments. Renewed motion resets the post-motion timer. Retention protects active videos, removes companion thumbnails and synchronizes the archive with deleted files. Optional Telegram messages are queued and retried outside camera processing. Diagnostics shows delivered, retried, failed and dropped counts.

## Diagnostics, updates and installation

Diagnostics reports per-camera processing/FPS/connectivity, process memory, disk space, database health and alert queue counters. Exported diagnostics omit credentials, hostnames, IP addresses and paths.

Update checks run in the background and only notify. Checks can be manual or explicitly enabled for startup/daily polling. They contact the public GitHub Releases API and never install software automatically. Windows signing hooks are available, but no signing certificate has been supplied. Current Windows/Linux preview packages lack distribution signing.

Use Sentinel for local DIY monitoring and development. Do not assume production security or 24/7 reliability from a passing test suite. [Efficiency](EFFICIENCY.md) explains measured performance and where further testing is needed.
