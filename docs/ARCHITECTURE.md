# Project Sentinel - Architecture Documentation

## Overview

Project Sentinel is a production-quality, self-hosted surveillance platform designed to run continuously on modest hardware. This document describes the system architecture, module responsibilities, and design patterns.

## Core Principles

1. **Reliability First**: The system must run unattended for months without intervention
2. **Modularity**: Each component has a single responsibility
3. **Graceful Degradation**: If one module fails, others continue operating
4. **Resource Efficiency**: Minimal CPU, memory, and disk usage
5. **Testability**: All modules independently testable

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Dashboard (Flask)                    │
│                  Local Browser Interface                     │
└─────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
│  Streaming   │       │  Recording  │       │  Security   │
│   Service    │       │   Service   │       │   Service   │
└────────┬─────┘       └──────┬──────┘       └──────┬──────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Motion Detection  │
                    │   & Analytics      │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Camera Module     │
                    │  (Multi-driver)    │
                    └─────────┬──────────┘
                              │
                        ┌─────▼─────┐
                        │  Hardware  │
                        └────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Foundation Layer (Logging, Config, Database, Utils)        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Watchdog Process (Health Monitoring & Auto-Recovery)       │
└──────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### Configuration (`config/`)

**Purpose**: Centralized configuration management

**Responsibilities**:

- Load configuration from JSON
- Support environment variable overrides
- Validate configuration values
- Provide type-safe access

**Key Classes**:

- `ConfigManager`: Configuration loader and validator
- `SentinelConfig`: Main configuration dataclass
- Sub-configs: `CameraConfig`, `MotionConfig`, `RecordingConfig`, etc.

### Logging (`utils/logger.py`)

**Purpose**: Structured, rotated logging throughout the application

**Responsibilities**:

- JSON and standard text formatting
- Rotating file handlers
- Console output with colors
- Separate error logs
- Crash reporting

**Key Classes**:

- `LoggerManager`: Logging system manager
- `JSONFormatter`: Custom JSON formatter
- `StandardFormatter`: Text formatter with colors

### Database (`database/`)

**Purpose**: Persistent data storage and retrieval

**Responsibilities**:

- SQLite database management
- Schema initialization
- Session management
- WAL mode for reliability

**Key Models**:

- `Application`: App state and metadata
- `Camera`: Camera configuration and status
- `MotionEvent`: Motion detection events
- `Recording`: Recording metadata
- `SystemMetric`: Performance metrics
- `ApplicationLog`: Event logging
- `Setting`: Key-value configuration storage

### Utils (`utils/system.py`)

**Purpose**: Common utilities and system information

**Responsibilities**:

- System information gathering
- Path management
- Resource monitoring and limits
- Time utilities

**Key Classes**:

- `SystemInfo`: CPU, memory, disk information
- `PathManager`: Organized path management
- `ResourceMonitor`: Resource usage tracking
- `TimeUtils`: Time and formatting utilities

### Camera Module (`camera/`)

**Purpose**: Abstract camera interface and drivers

**Planned Responsibilities**:

- Auto-detect available cameras
- Support multiple camera types (builtin, USB, RTSP, IP, etc.)
- Automatic reconnection
- Frame capture and streaming
- Error isolation (camera failure doesn't crash app)

**Design Pattern**: Abstract driver factory pattern

### Motion Detection (`motion/`)

**Purpose**: Detect motion in video frames

**Planned Responsibilities**:

- Background subtraction
- Frame differencing
- Morphological operations
- Contour detection
- Configurable sensitivity
- False positive reduction

**Performance Target**: <5% CPU during recording

### Recording (`recording/`)

**Purpose**: Capture and save video recordings

**Planned Responsibilities**:

- Record on motion detection
- Post-motion buffering
- MP4 codec optimization
- Organized file structure
- Thumbnail generation
- Metadata storage

### Storage Manager (`storage/`)

**Purpose**: Manage disk usage and retention

**Planned Responsibilities**:

- Monitor disk usage
- Automatic deletion of old recordings
- Retention policy enforcement
- Prevent disk from filling

### Streaming (`streaming/`)

**Purpose**: Local real-time video streaming

**Planned Responsibilities**:

- WebSocket video feed
- Quality scaling
- Bandwidth efficiency
- Browser compatibility

### Web Dashboard (`web/`)

**Purpose**: User interface for monitoring and configuration

**Planned Responsibilities**:

- Live stream viewing
- Recording playback
- System metrics display
- Configuration editing
- Event timeline
- Modern responsive UI

### Security (`security/`)

**Purpose**: Authentication and authorization

**Planned Responsibilities**:

- User authentication
- Password hashing
- Session management
- CSRF protection
- Input validation

### Watchdog (`watchdog.py`)

**Purpose**: Health monitoring and automatic recovery

**Responsibilities**:

- Monitor main application process
- Restart on failure
- Check system resources
- Prevent crash loops
- Report health status

**Design**: Separate process for resilience

### Main Application (`app.py`)

**Purpose**: Application initialization and orchestration

**Responsibilities**:

- Initialize all subsystems
- Manage component lifecycle
- Graceful shutdown
- Signal handling
- Main event loop

## Data Flow

### Motion Detection & Recording Flow

```
Camera Frame
    │
    ├─► Motion Detector
    │       │
    │       ├─► No Motion ──────┐
    │       │                   │
    │       └─► Motion Detected │
    │               │           │
    │               ├─► Record ─┼─► Recording Service ──► Storage
    │               │           │
    │               └─► Update DB
    │                           │
    └───────────────────────────┴─► Web Stream
```

### System Health Check Flow

```
Watchdog
    │
    ├─► Check App Process ──► Dead? ──► Restart
    │
    ├─► Check CPU Usage ──► High? ──► Pause Recording
    │
    ├─► Check Memory ──► Critical? ──► Cleanup
    │
    └─► Check Disk ──► Filling? ──► Delete Old Recordings
```

## Configuration Hierarchy

1. **Defaults** (built-in)
2. **JSON Configuration** (`config/settings.json`)
3. **Environment Variables** (prefix: `SENTINEL_`)

Example environment override:

```bash
SENTINEL_MOTION_SENSITIVITY=50
SENTINEL_CAMERA_FPS=20
```

## Database Schema

The database stores:

- **Application State**: Version, start time, health
- **Camera Configuration**: Connected cameras, settings, status
- **Motion Events**: Timestamp, contour data, triggering frame
- **Recordings**: File path, duration, size, thumbnail
- **System Metrics**: CPU, memory, disk usage over time
- **Application Logs**: Structured event logs
- **Settings**: Key-value configuration

## Error Handling Strategy

```
Error Occurs
    │
    ├─► Recoverable?
    │   ├─► Yes ──► Retry with exponential backoff
    │   └─► No  ──► Isolate component, continue operation
    │
    ├─► Critical?
    │   ├─► Yes ──► Log, notify watchdog for restart
    │   └─► No  ──► Log, continue
    │
    └─► Notify User via Web Dashboard
```

## Performance Targets

| Metric                   | Target | Current |
| ------------------------ | ------ | ------- |
| Startup Time             | <15s   | -       |
| Idle CPU                 | <10%   | -       |
| Recording CPU            | <25%   | -       |
| Memory Usage             | <500MB | -       |
| Motion Detection Latency | <500ms | -       |
| Recording Latency        | <2s    | -       |
| Stream Latency           | <1s    | -       |

## Future Expansion Points

### Camera Layer

- Add new camera drivers by implementing `CameraDriver` interface
- Support authentication-required cameras
- Camera health monitoring per-device

### Motion Detection

- Add ML-based detection (YOLOv8, etc.)
- Multi-zone detection
- Sensitivity by zone
- Time-based sensitivity schedules

### Recording

- Multiple codec support
- Adaptive bitrate
- Multi-camera synchronized recording
- Cloud backup (optional)

### Alerts

- Telegram notifications
- Discord webhooks
- Email alerts
- SMS (future)

### Storage

- Network storage support
- Cloud storage (optional, secondary)
- Local network backup

### Analytics

- Daily/weekly/monthly reports
- Event frequency analysis
- Peak activity times
- Storage trends

## Testing Strategy

- **Unit Tests**: Individual module testing
- **Integration Tests**: Module interactions
- **System Tests**: Full system workflows
- **Performance Tests**: Resource usage verification
- **Stability Tests**: Long-running application tests

## Deployment

### Windows 10 Deployment

1. Install Python 3.10+
2. Create virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Configure Windows Task Scheduler to run watchdog on login
5. Watchdog auto-starts main application

### Auto-Recovery

```
System Reboots
    │
    └─► Windows Auto-Login (configured)
        │
        └─► Task Scheduler ──► Watchdog
                │
                └─► Main Application
```

## Monitoring Checklist

- [ ] Application process running
- [ ] Camera connected and streaming
- [ ] Motion detection responding
- [ ] Recordings being saved
- [ ] Database healthy
- [ ] Disk space available
- [ ] CPU usage acceptable
- [ ] Memory usage acceptable
- [ ] No unhandled exceptions in logs

## Next Steps

1. ✅ Core initialization and architecture
2. ⬜ Camera module with multiple drivers
3. ⬜ Motion detection engine
4. ⬜ Recording service
5. ⬜ Storage manager
6. ⬜ Web dashboard
7. ⬜ Streaming service
8. ⬜ Security and authentication
9. ⬜ Alert system
10. ⬜ AI/ML integration framework
