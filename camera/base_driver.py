"""
Abstract Camera Driver Interface for Project Sentinel

Responsibility: Define the contract that all camera drivers must implement.
Enables support for multiple camera types without coupling.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class CameraDriver(ABC):
    """
    Abstract base class for camera drivers.
    
    All camera implementations must inherit from this class and implement
    the required methods. This enables support for multiple camera types:
    - Built-in/USB webcams (OpenCV)
    - RTSP streams
    - MJPEG streams
    - IP cameras
    - Raspberry Pi cameras
    - ESP32-CAM
    - Android phone cameras
    """
    
    def __init__(self, camera_id: str, name: str):
        """
        Initialize camera driver.
        
        Args:
            camera_id: Unique identifier for camera
            name: Human-readable name
        """
        self.camera_id = camera_id
        self.name = name
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the camera.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the camera.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_alive(self) -> bool:
        """
        Check if camera is still connected and responding.
        
        Returns:
            True if camera is alive, False otherwise
        """
        pass
    
    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture a frame from the camera.
        
        Returns:
            Frame as numpy array (BGR format, shape HxWx3) or None if failed
            
        Raises:
            Nothing - should handle errors gracefully and return None
        """
        pass
    
    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get camera resolution.
        
        Returns:
            Tuple of (width, height) in pixels
        """
        pass
    
    @abstractmethod
    def get_fps(self) -> float:
        """
        Get camera frames per second.
        
        Returns:
            FPS as float
        """
        pass
    
    @abstractmethod
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set camera resolution.
        
        Args:
            width: Frame width in pixels
            height: Frame height in pixels
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_fps(self, fps: int) -> bool:
        """
        Set camera frames per second.
        
        Args:
            fps: Target FPS
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    def get_status(self) -> dict:
        """
        Get camera status.
        
        Returns:
            Dictionary with camera status information
        """
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "connected": self.is_connected,
            "alive": self.is_alive(),
            "resolution": self.get_resolution(),
            "fps": self.get_fps(),
        }
