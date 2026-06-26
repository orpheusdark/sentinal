"""
Built-in Camera Driver using OpenCV

Supports:
- Built-in webcam
- USB webcams
- Any camera supported by OpenCV on the platform
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import time
import logging

from ..base_driver import CameraDriver

logger = logging.getLogger(__name__)


class BuiltinCameraDriver(CameraDriver):
    """
    OpenCV-based camera driver for built-in and USB cameras.
    
    Features:
    - Automatic resolution and FPS configuration
    - Frame rate limiting
    - Error resilience
    - Resolution presets
    """
    
    # Resolution presets
    RESOLUTIONS = {
        "360p": (640, 360),
        "480p": (640, 480),
        "720p": (1280, 720),
        "1080p": (1920, 1080),
    }
    
    def __init__(self, camera_index: int = 0, name: str = "builtin", target_fps: int = 15, resolution: str = "720p"):
        """
        Initialize built-in camera driver.
        
        Args:
            camera_index: OpenCV camera index (0 for default)
            name: Human-readable camera name
            target_fps: Target frames per second
            resolution: Resolution preset (360p, 480p, 720p, 1080p)
        """
        super().__init__(f"builtin_{camera_index}", name)
        
        self.camera_index = camera_index
        self.target_fps = target_fps
        self.target_resolution = self.RESOLUTIONS.get(resolution, (1280, 720))
        
        self.cap = None
        self.last_frame_time = 0
        self.frame_interval = 1.0 / target_fps
    
    def connect(self) -> bool:
        """
        Connect to camera using OpenCV.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False
            
            # Configure camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # Try to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Verify connection
            if not self.is_alive():
                logger.error("Camera failed to respond")
                self.disconnect()
                return False
            
            self.is_connected = True
            logger.info(f"Camera connected: {self.name} at index {self.camera_index}")
            logger.info(f"  Resolution: {self.get_resolution()}")
            logger.info(f"  FPS: {self.get_fps()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to camera: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from camera.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.cap is not None:
                self.cap.release()
                self.is_connected = False
                logger.info(f"Camera disconnected: {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting camera: {e}")
            return False
    
    def is_alive(self) -> bool:
        """
        Check if camera is still responding.
        
        Returns:
            True if camera is alive, False otherwise
        """
        if self.cap is None or not self.cap.isOpened():
            return False
        
        try:
            ret, _ = self.cap.read()
            return ret
        except Exception:
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture and return a frame from the camera.
        
        Features:
        - Enforces target FPS
        - Handles frame read errors gracefully
        - Returns BGR format (OpenCV standard)
        
        Returns:
            Frame as numpy array (BGR, HxWx3) or None if failed
        """
        try:
            # Enforce target FPS
            time_since_last = time.time() - self.last_frame_time
            if time_since_last < self.frame_interval:
                time.sleep(self.frame_interval - time_since_last)
            
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                logger.warning(f"Failed to read frame from {self.name}")
                return None
            
            self.last_frame_time = time.time()
            return frame
            
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return None
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get current camera resolution.
        
        Returns:
            Tuple of (width, height)
        """
        if self.cap is None:
            return self.target_resolution
        
        try:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (width, height)
        except Exception:
            return self.target_resolution
    
    def get_fps(self) -> float:
        """
        Get current camera FPS.
        
        Returns:
            FPS as float
        """
        if self.cap is None:
            return float(self.target_fps)
        
        try:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            return float(fps) if fps > 0 else float(self.target_fps)
        except Exception:
            return float(self.target_fps)
    
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set camera resolution.
        
        Args:
            width: Frame width
            height: Frame height
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.cap is None or not self.cap.isOpened():
                return False
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.target_resolution = (width, height)
            
            actual = self.get_resolution()
            logger.info(f"Resolution set to {actual}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting resolution: {e}")
            return False
    
    def set_fps(self, fps: int) -> bool:
        """
        Set camera FPS.
        
        Args:
            fps: Target FPS
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.cap is None or not self.cap.isOpened():
                return False
            
            self.cap.set(cv2.CAP_PROP_FPS, fps)
            self.target_fps = fps
            self.frame_interval = 1.0 / fps
            
            actual = self.get_fps()
            logger.info(f"FPS set to {actual}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting FPS: {e}")
            return False
