# Project Sentinel - Phase 2 Implementation Guide

## Overview

Phase 1 (Foundation) is complete. Phase 2 will implement the Camera & Motion Detection systems - the core surveillance functionality.

## Phase 2 Modules

### 1. Camera Module (`camera/`)

#### Responsibility

- Provide abstract interface to cameras
- Support multiple camera types
- Auto-detect cameras
- Automatic reconnection
- Provide frames to motion detection
- Never crash the application

#### Architecture

```python
# camera/base_driver.py
class CameraDriver(ABC):
    """Abstract base class for camera drivers."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to camera."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from camera."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame (BGR format)."""
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Get (width, height)."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Get frames per second."""
        pass


# camera/drivers/builtin.py
class BuiltinCameraDriver(CameraDriver):
    """Driver for built-in/USB cameras using OpenCV."""
    pass


# camera/manager.py
class CameraManager:
    """Manages camera connections and frame streaming."""
    pass
```

#### Implementation Order

1. `camera/base_driver.py` - Abstract interface
2. `camera/drivers/builtin.py` - OpenCV driver
3. `camera/manager.py` - Camera manager
4. `camera/detector.py` - Camera auto-detection

### 2. Motion Detection Module (`motion/`)

#### Responsibility

- Detect motion in frames
- Generate motion events
- Trigger recording
- Minimize CPU usage

#### Architecture

```python
# motion/detector.py
class MotionDetector:
    """Detects motion in video frames."""

    def __init__(self, config: MotionConfig):
        pass

    def process_frame(self, frame: np.ndarray) -> MotionResult:
        """
        Process frame and detect motion.

        Returns:
            MotionResult with motion_detected, contours, etc.
        """
        pass

    def reset(self):
        """Reset background model."""
        pass


# motion/result.py
class MotionResult:
    """Result of motion detection on a frame."""

    motion_detected: bool
    contour_count: int
    max_contour_area: int
    frame_with_contours: np.ndarray
```

#### Implementation Order

1. `motion/result.py` - Motion result dataclass
2. `motion/detector.py` - Motion detection engine
3. `motion/event_manager.py` - Event tracking

### 3. Recording Service (partially in Phase 2)

#### Framework Created

- Database models for recordings
- Config system for recording settings
- File path organization
- Metadata storage

#### Still Needed for Phase 3

- Actual video encoding
- Stream writing
- Thumbnail generation

## Database Integration

All models already defined:

- `Camera` - Camera configuration and status
- `MotionEvent` - Motion events with timestamp and contours
- `Recording` - Recording metadata

Add to motion detection:

```python
# Save motion event to database
motion_event = MotionEvent(
    camera_id=camera.id,
    start_time=datetime.utcnow(),
    contour_count=result.contour_count,
    max_contour_area=result.max_contour_area,
    sensitivity_level=config.motion.sensitivity,
)
session.add(motion_event)
session.commit()
```

## Configuration Integration

Motion and camera config already defined in:

- `config/settings.py` - Configuration classes
- `config/settings.json` - Default values

Example usage:

```python
from config import get_config

config = get_config()
camera_fps = config.camera.fps
motion_sensitivity = config.motion.sensitivity
```

## Logging Integration

All modules already have logging:

```python
from utils import get_logger

logger = get_logger(__name__)
logger.info("Camera connected")
logger.error("Failed to read frame", exc_info=True)
```

## Performance Targets for Phase 2

| Operation             | Target  | Notes                |
| --------------------- | ------- | -------------------- |
| Frame capture         | 15 FPS  | At 720p              |
| Motion detection      | <5% CPU | Idle system          |
| Frame latency         | <100ms  | Capture to detection |
| Motion event DB write | <50ms   | Per event            |
| Camera reconnect      | <5s     | After disconnect     |

## Testing Strategy

### Unit Tests (`tests/camera/`, `tests/motion/`)

```python
# tests/camera/test_builtin_driver.py
def test_builtin_driver_connect():
    """Test camera connection."""
    driver = BuiltinCameraDriver()
    assert driver.connect()


def test_get_frame():
    """Test frame capture."""
    driver = BuiltinCameraDriver()
    frame = driver.get_frame()
    assert frame is not None
    assert frame.shape == (720, 1280, 3)


# tests/motion/test_detector.py
def test_motion_detection():
    """Test motion detection on frame."""
    detector = MotionDetector(config)

    # Create two frames (one static, one with motion)
    frame1 = create_test_frame(static=True)
    frame2 = create_test_frame(static=False)

    result1 = detector.process_frame(frame1)
    assert not result1.motion_detected

    result2 = detector.process_frame(frame2)
    assert result2.motion_detected
```

### Integration Tests

```python
def test_camera_to_motion_pipeline():
    """Test complete camera → motion detection pipeline."""
    camera = CameraManager()
    detector = MotionDetector(config)

    frame = camera.get_frame()
    result = detector.process_frame(frame)

    assert frame is not None
    assert isinstance(result, MotionResult)
```

## Error Handling Requirements

### Camera Failures

- Connection failure → Retry with backoff
- Frame read failure → Skip frame, continue
- Disconnection → Attempt auto-reconnect
- Persistent failure → Log error, don't crash app

### Motion Detection Failures

- Invalid frame → Skip, continue
- Processing error → Log, continue
- Memory pressure → Reduce resolution, continue

## Database Queries Needed

### Query 1: Get current camera

```python
camera = session.query(Camera).filter_by(name="builtin").first()
```

### Query 2: Create motion event

```python
event = MotionEvent(
    camera_id=camera.id,
    start_time=datetime.utcnow(),
    contour_count=10,
    max_contour_area=5000,
    sensitivity_level=config.motion.sensitivity,
)
session.add(event)
session.commit()
```

### Query 3: Get recent motion events

```python
events = session.query(MotionEvent).filter(
    MotionEvent.camera_id == camera.id,
    MotionEvent.start_time > datetime.utcnow() - timedelta(hours=1)
).all()
```

## Files to Create (Order)

### Phase 2a: Camera Module

1. `camera/base_driver.py` - Abstract interface
2. `camera/drivers/__init__.py` - Drivers package
3. `camera/drivers/builtin.py` - OpenCV driver
4. `camera/manager.py` - Camera manager
5. `camera/detector.py` - Camera detection
6. `camera/__init__.py` - Update exports

### Phase 2b: Motion Detection

1. `motion/result.py` - Motion result class
2. `motion/detector.py` - Motion detector
3. `motion/event_manager.py` - Event tracking
4. `motion/__init__.py` - Update exports

### Phase 2c: Tests

1. `tests/camera/__init__.py`
2. `tests/camera/test_builtin_driver.py`
3. `tests/motion/__init__.py`
4. `tests/motion/test_detector.py`
5. `tests/motion/test_integration.py`

## Integration Points

### With Application

```python
# In app.py
from camera import CameraManager
from motion import MotionDetector

class Application:
    def initialize(self):
        # ... existing code ...

        # Initialize camera
        self.camera_manager = CameraManager(self.context.config)
        if not self.camera_manager.connect():
            logger.error("Failed to connect camera")
            return False

        # Initialize motion detector
        self.motion_detector = MotionDetector(self.context.config.motion)

        return True

    def main_loop(self):
        while self.context.running:
            # Get frame
            frame = self.camera_manager.get_frame()
            if frame is None:
                continue

            # Detect motion
            result = self.motion_detector.process_frame(frame)

            if result.motion_detected:
                logger.info(f"Motion detected: {result.contour_count} contours")
                # Trigger recording (Phase 3)

            time.sleep(1/15)  # 15 FPS
```

### With Database

- Save motion events to `motion_events` table
- Update camera status in `cameras` table
- Create recording entries in `recordings` table (Phase 3)

### With Configuration

- Get camera FPS: `config.camera.fps`
- Get motion sensitivity: `config.motion.sensitivity`
- Get post-motion buffer: `config.recording.post_motion_seconds`

## Success Criteria for Phase 2

- [ ] All camera drivers implemented
- [ ] Motion detection working at <5% CPU
- [ ] Camera auto-detection working
- [ ] Automatic reconnection working
- [ ] Motion events saved to database
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Performance targets met
- [ ] Zero unhandled exceptions
- [ ] Comprehensive logging in place

## Next Phase (Phase 3)

Once Phase 2 complete:

1. Recording service (actual video encoding)
2. Storage manager (disk cleanup)
3. Web dashboard (basic streaming)
4. Thumbnail generation
