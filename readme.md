# Project Sentinel - README

![Project Sentinel](https://img.shields.io/badge/Status-Development-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![License](https://img.shields.io/badge/License-MIT-blue)

A production-quality, self-hosted surveillance platform designed for continuous 24/7 operation on modest hardware.

## Overview

Project Sentinel transforms an old laptop into a reliable surveillance server. It's built from the ground up for stability, efficiency, and long-term autonomous operation.

**Key Features**:

- ✅ Modular architecture
- ✅ Lightweight (target <500MB RAM)
- ✅ Self-hosted (no cloud dependency)
- ✅ Automatic recovery (watchdog monitoring)
- ✅ Motion-triggered recording
- ✅ Multi-camera support (future)
- ✅ Modern web dashboard
- ✅ Structured logging
- ✅ SQLite database
- ⬜ AI-powered detection (framework ready)

## System Requirements

### Minimum Hardware

- **CPU**: Intel Core i3 or equivalent
- **RAM**: 4GB (8GB recommended)
- **Storage**: 500GB HDD
- **OS**: Windows 10 (Linux support future)
- **Internet**: Stable Wi-Fi or Ethernet

### Performance Targets

- Startup time: <15 seconds
- Idle CPU usage: <10%
- Recording CPU usage: <25%
- Memory usage: <500MB
- Motion detection latency: <500ms

## Installation

### Prerequisites

- Python 3.10 or later
- Windows 10 or later

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/orpheusdark/sentinal.git
cd sentinal
```

2. **Create virtual environment**

```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Initialize configuration**
   The system will auto-generate default configuration on first run.

```bash
python app.py
```

5. **Test the installation**

```bash
# In another terminal
curl http://localhost:5000
```

## Quick Start

### Run Application Directly

```bash
python app.py
```

The application will:

1. Initialize logging system
2. Load configuration
3. Create database
4. Check system health
5. Start main event loop

### Run with Watchdog (Recommended)

```bash
python watchdog.py
```

The watchdog will:

1. Start the main application
2. Monitor process health
3. Auto-restart on failure
4. Check system resources
5. Prevent crash loops

## Web Dashboard

Project Sentinel includes a modern, responsive web dashboard for monitoring and control.

### Accessing the Dashboard

Once the application is running, access the dashboard at:

```
http://localhost:5000
```

From another computer on the network:

```
http://<machine-ip>:5000
```

### Dashboard Features

**Dashboard Tab**:

- Live video stream from camera
- Real-time system metrics (CPU, memory, disk)
- Recording status
- Motion events from last 24 hours
- Health indicators for all components

**Recordings Tab**:

- Browse all recorded videos
- Filter by time period (1-30 days)
- Filter by camera
- Download video files
- View file metadata (duration, size, quality)

**Settings Tab**:

- Adjust camera FPS and resolution
- Fine-tune motion detection sensitivity
- Select recording quality
- Configure storage retention policy
- Set disk space thresholds

### API Endpoints

Full REST API available for custom integrations:

- `GET /api/system/info` - System information
- `GET /api/system/health` - Health status
- `GET /api/system/disk` - Disk usage
- `GET /api/recordings` - List recordings
- `GET /api/motion-events` - Recent motion events
- `GET /api/cameras` - Camera status
- `GET /api/config` - Current configuration
- `GET /api/recordings/<id>/download` - Download video file

See [PHASE4_COMPLETE.md](docs/PHASE4_COMPLETE.md) for complete API documentation.

## Configuration

Configuration is JSON-based and can be overridden with environment variables.

### Configuration Files

- `config/settings.json` - Main configuration
- `config/settings.py` - Configuration classes

### Default Configuration

```json
{
  "camera": {
    "fps": 15,
    "resolution": "720p",
    "auto_reconnect": true
  },
  "motion": {
    "enabled": true,
    "sensitivity": 40,
    "record_on_motion": true,
    "post_motion_seconds": 10
  },
  "recording": {
    "codec": "mp4v",
    "quality": "high"
  },
  "storage": {
    "retention_days": 30,
    "max_disk_usage_percent": 80
  }
}
```

### Environment Variable Overrides

```bash
set SENTINEL_MOTION_SENSITIVITY=50
set SENTINEL_CAMERA_FPS=20
python app.py
```

## Project Structure

```
ProjectSentinel/
├── app.py                 # Main application entry point
├── watchdog.py           # Health monitoring watchdog
├── requirements.txt      # Python dependencies
├── config/               # Configuration system
├── camera/               # Camera module (planned)
├── motion/               # Motion detection (planned)
├── recording/            # Recording service (planned)
├── streaming/            # Streaming service (planned)
├── web/                  # Web dashboard (planned)
├── database/             # Database layer
├── storage/              # Storage management (planned)
├── security/             # Security module (planned)
├── ai/                   # AI module (planned)
├── alerts/               # Alert system (planned)
├── scheduler/            # Task scheduling (planned)
├── utils/                # Common utilities
├── logs/                 # Application logs (created at runtime)
├── recordings/           # Video recordings (created at runtime)
├── snapshots/            # Thumbnail snapshots (created at runtime)
├── data/                 # Database files (created at runtime)
├── tests/                # Unit and integration tests
├── docs/                 # Documentation
└── README.md             # This file
```

## Logging

The application uses structured JSON logging with automatic rotation.

### Log Location

- Main logs: `logs/app.log`
- Error logs: `logs/error.log`
- Watchdog logs: `logs/watchdog.log`

### Log Format

JSON format enables easy parsing and analysis:

```json
{
  "timestamp": "2026-06-26T12:34:56.789123",
  "level": "INFO",
  "logger": "app",
  "module": "camera",
  "function": "connect",
  "line": 42,
  "message": "Camera connected successfully"
}
```

## Database

Project Sentinel uses SQLite for reliable, serverless data storage.

### Database Location

`data/sentinel.db`

### Schema

- **applications**: App state and heartbeat
- **cameras**: Camera configuration and status
- **motion_events**: Detected motion events
- **recordings**: Recording metadata
- **system_metrics**: Performance metrics
- **application_logs**: Structured event logs
- **settings**: Key-value configuration

## Development

### Code Standards

- ✅ Type hints on all functions
- ✅ Docstrings for all modules and classes
- ✅ No magic numbers
- ✅ Configurable via config system
- ✅ Comprehensive error handling
- ✅ Structured logging

### Running Tests

```bash
pytest tests/ -v
```

### Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Windows Deployment (Auto-Start)

Configure Windows Task Scheduler to auto-start the watchdog:

1. **Create Python script** (`start_sentinel.bat`):

```batch
cd C:\Path\To\ProjectSentinel
venv\Scripts\python.exe watchdog.py
```

2. **Create Task Scheduler task**:

- Trigger: At log on (any user)
- Action: Start program (start_sentinel.bat)
- Settings: Run with highest privileges

3. **Enable auto-login** (Windows Settings):

- Settings → Accounts → Sign-in options
- Enable "Automatically sign in" with a local account

## Roadmap

### Phase 1: Foundation ✅

- [x] Core architecture
- [x] Configuration system
- [x] Logging system
- [x] Database layer
- [x] Watchdog process
- [x] System monitoring

**Documentation**: [PHASE1_COMPLETE.md](docs/PHASE1_COMPLETE.md)

### Phase 2: Camera & Motion ✅

- [x] Camera abstraction layer
- [x] Builtin webcam driver
- [x] USB camera support
- [x] Motion detection engine (MOG2)
- [x] Motion event tracking

**Documentation**: [PHASE2_COMPLETE.md](docs/PHASE2_COMPLETE.md)

### Phase 3: Recording & Storage ✅

- [x] MP4 H.264 video recording
- [x] Motion-triggered recording
- [x] Storage manager with retention policy
- [x] Disk monitoring and emergency cleanup
- [x] Database persistence

**Documentation**: [PHASE3_COMPLETE.md](docs/PHASE3_COMPLETE.md)

### Phase 4: Web Dashboard ✅

- [x] Flask web server (port 5000)
- [x] REST API endpoints (8+)
- [x] WebSocket frame streaming
- [x] HTML dashboard templates (3 pages)
- [x] Real-time system monitoring
- [x] Recording browser with filters
- [x] Settings configuration page
- [x] Responsive design (desktop/tablet/mobile)
- [x] Comprehensive test suite

**Documentation**: [PHASE4_COMPLETE.md](docs/PHASE4_COMPLETE.md)

**Access Dashboard**: http://localhost:5000

### Phase 5: Advanced Features (Upcoming)

- [ ] Security/Authentication
- [ ] HTTPS/SSL encryption
- [ ] Alert system (Telegram, Discord, Email)
- [ ] Multi-camera web UI
- [ ] Remote access and tunneling
- [ ] AI/ML framework integration
- [ ] Cloud backup (optional)
- [ ] Mobile app

## Performance Monitoring

Monitor system performance in real-time:

```python
from utils.system import ResourceMonitor

healthy, status = ResourceMonitor.full_health_check()

if not healthy:
    print(f"CPU: {status['cpu_status']}")
    print(f"Memory: {status['memory_status']}")
    print(f"Disk: {status['disk_status']}")
```

## Troubleshooting

### Application won't start

1. Check logs: `type logs\error.log`
2. Verify Python version: `python --version` (requires 3.10+)
3. Verify dependencies: `pip list`

### High CPU/Memory usage

1. Check logs for errors
2. Reduce motion detection sensitivity
3. Lower camera FPS
4. Check disk space

### Camera not detected

1. Camera driver conflicts (Windows)
2. Camera already in use
3. Check device manager

### Database errors

1. Check `data/` directory exists and is writable
2. Delete `data/sentinel.db` to reset (warning: loses data)
3. Check logs for SQL errors

## Contributing

Project Sentinel is under active development. Contributions welcome!

## Support

For issues, questions, or suggestions:

- Open an issue on GitHub
- Check existing issues and documentation

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:

- Python 3.10+
- OpenCV for computer vision
- Flask for web interface
- SQLAlchemy for database ORM
- psutil for system monitoring

## Project Status

🟡 **In Development** - Core foundation complete, camera and motion modules in progress.

Last Updated: 2026-06-26
