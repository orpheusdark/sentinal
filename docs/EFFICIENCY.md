# Efficiency and practical value

Sentinel is useful as a customizable, local DIY recorder for a room, workshop or other limited camera setup. Its main benefits are local video storage, no required cloud account, inspectable code, independent camera policies and a lightweight browser interface. It is not yet a certified NVR or a proven replacement for a critical unattended security system.

## Measured component benchmark

Measured on the available Windows machine with Python 3.11.9 and 12 logical CPUs. Each resolution used 60 generated frames, MOG2 motion processing and JPEG encoding, followed by a separate 60-frame MPEG-4 writer test. This excludes live capture, browser/network traffic, database writes, disk pressure and optional object inference. It is a short synthetic component benchmark, not a full-app capacity test.

| Resolution | Default OpenCV processing FPS | One-thread processing FPS | One-thread p95 processing time | Benchmark process RSS at that step |
|---|---:|---:|---:|---:|
| 640×480 | 137.70 | 141.74 | 8.50 ms | 108 MB |
| 1280×720 | 40.78 | 49.35 | 21.82 ms | 170.8 MB |
| 1920×1080 | 18.22 | 18.44 | 85.87 ms | 289.3 MB |

At 720p, the estimated CPU time needed for a 15-FPS motion/JPEG workload dropped from about 2.16 logical-core equivalents to 0.30 when OpenCV used one internal thread. This reflects reduced thread-pool overhead in this test. It is not a guaranteed whole-machine CPU percentage. At 1080p, processing alone leaves little 15-FPS headroom for capture, recording and inference.

Raw results are in [the benchmark record](benchmarks/components-2026-11-10.json) and the release report. RSS was observed during one process stepping through resolutions; allocator caching affects it, so these numbers are not a per-camera memory formula. The zero/small CPU snapshots on an idle Diagnostics screen also do not describe an active recording workload.

## Recommended starting point

Start with one camera at 720p/15 FPS, OpenCV threads=1 and object filtering off. Verify a complete day of recording, downloads, restart, camera disconnect/reconnect and cleanup in a disposable archive before relying on it. Add cameras one at a time and watch processing time, observed FPS, stale frames, errors, queue drops and disk growth. Reduce FPS/resolution when work approaches the frame interval (66.7 ms at 15 FPS).

Independent workers prevent one network alert or camera lock from serializing other feeds, but they share CPU, memory and disk. Eight configurable profiles do not imply eight-camera capacity. Optional HOG/ONNX detection is more expensive and must be measured separately. JPEG review preview is limited to five FPS; original downloads retain capture FPS.

## Is it worth continuing?

Yes, if the goal is learning, customization, local privacy and a low-cost recorder that you can maintain. Prioritize real-device soak testing, false-positive measurements, update/install acceptance and signed Windows releases over adding more visual effects. If the goal is dependable security immediately, keep an established recorder in service while validating Sentinel alongside it. Do not make Sentinel the only recorder until its failure/recovery behavior has been proven for your devices and environment.
