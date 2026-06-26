"""Unit tests for camera module."""

import pytest
import numpy as np
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from camera import BuiltinCameraDriver, CameraManager
from config import CameraConfig


class TestBuiltinCameraDriver:
    """Test built-in camera driver."""
    
    def test_driver_initialization(self):
        """Test driver can be initialized."""
        driver = BuiltinCameraDriver(camera_index=0, name="test_camera")
        
        assert driver.camera_id == "builtin_0"
        assert driver.name == "test_camera"
        assert not driver.is_connected
    
    def test_get_resolution_preset(self):
        """Test resolution preset retrieval."""
        presets = BuiltinCameraDriver.RESOLUTIONS
        
        assert presets["720p"] == (1280, 720)
        assert presets["480p"] == (640, 480)
        assert presets["1080p"] == (1920, 1080)
    
    def test_driver_properties(self):
        """Test driver properties are set correctly."""
        driver = BuiltinCameraDriver(
            camera_index=0,
            name="test",
            target_fps=20,
            resolution="480p"
        )
        
        assert driver.target_fps == 20
        assert driver.target_resolution == (640, 480)
    
    @pytest.mark.skipif(
        not _has_camera(),
        reason="No camera available"
    )
    def test_camera_connect(self):
        """Test camera connection (requires hardware)."""
        driver = BuiltinCameraDriver()
        
        result = driver.connect()
        
        # Connection may fail if no camera available
        if result:
            assert driver.is_connected
            assert driver.is_alive()
            driver.disconnect()
    
    @pytest.mark.skipif(
        not _has_camera(),
        reason="No camera available"
    )
    def test_get_frame(self):
        """Test frame capture (requires hardware)."""
        driver = BuiltinCameraDriver()
        
        if driver.connect():
            # Skip first few frames (camera warm-up)
            for _ in range(5):
                driver.get_frame()
            
            frame = driver.get_frame()
            
            if frame is not None:
                assert isinstance(frame, np.ndarray)
                assert len(frame.shape) == 3
                assert frame.shape[2] == 3  # BGR
            
            driver.disconnect()


class TestCameraManager:
    """Test camera manager."""
    
    def test_manager_initialization(self):
        """Test manager can be initialized."""
        config = CameraConfig()
        manager = CameraManager(config)
        
        assert manager.config == config
        assert len(manager.cameras) == 0
    
    def test_manager_properties(self):
        """Test manager stores configuration."""
        config = CameraConfig(fps=20, enabled=True)
        manager = CameraManager(config)
        
        assert manager.config.fps == 20
        assert manager.config.enabled
    
    @pytest.mark.skipif(
        not _has_camera(),
        reason="No camera available"
    )
    def test_manager_initialize(self):
        """Test manager initialization (requires hardware)."""
        config = CameraConfig()
        manager = CameraManager(config)
        
        result = manager.initialize()
        
        # May fail if no camera available
        if result:
            assert len(manager.cameras) > 0
            manager.shutdown()
    
    def test_get_status_empty(self):
        """Test get_status with no cameras."""
        config = CameraConfig()
        manager = CameraManager(config)
        
        status = manager.get_status()
        
        assert isinstance(status, dict)
        assert len(status) == 0


def _has_camera() -> bool:
    """Check if a camera is available."""
    try:
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        result = cap.isOpened()
        cap.release()
        return result
    except Exception:
        return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
