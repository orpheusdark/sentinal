# Features and use

## Overview

The command overview combines a local live preview, camera/recording status, CPU/memory/disk telemetry, archive totals and a motion timeline. A dark navy/cyan interface uses local Bahnschrift/Trebuchet system font fallbacks, responsive card grids, visible focus states, labeled controls, skip navigation, live status text and reduced-motion styling. No external fonts or image services are required.

Preview controls change canvas size and the browser's polling rate. Pause affects only that browser preview; surveillance and recording continue. Missing camera and telemetry errors show explicit unavailable/stale states. Metrics refresh every five seconds. JPEG quality is configured at the host.

## Recordings

Filter by period and connected camera. Browse pages of 30 records, then download a finalized video. Duration and size come from metadata written after finalization. MP4 uses MPEG-4 Part 2 (`mp4v`); the legacy `h264` label selects that same implementation and is not a promise of an H.264 encoder. Codec availability and browser playback depend on the platform. Playback is via a downloaded file. The previously inert Delete button is removed; automatic retention remains supported.

## Motion and retention

MOG2 background subtraction and contour filtering trigger events and recordings. Motion returning during the post-motion tail cancels its pending stop timer. Disabling recording prevents recording starts. Setting record_on_motion=false records continuously while frames are received. Tail and retention settings apply after restart. Automatic cleanup can be disabled through recording.auto_cleanup.

## Alerts and scope

Telegram can send startup, shutdown and motion metadata with an explicit opt-in token/chat ID. It does not upload video. Alert delivery currently occurs synchronously and may delay the frame loop during network problems. No person/object recognition, pre-motion buffering, cloud backup, multi-user roles, native phone application or production WebSocket transport is implemented.
