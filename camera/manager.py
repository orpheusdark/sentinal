"""
Camera Manager for Project Sentinel

Responsibility: Manage camera connections, auto-detection, reconnection, and frame streaming.
Provides unified interface to multiple cameras.
"""

from typing import Dict, Optional, List, Tuple
import time
import logging
from datetime import datetime, timedelta
import threading

from config import CameraConfig
from database import get_db_session, Camera
from .base_driver import CameraDriver
from .drivers.builtin import BuiltinCameraDriver

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages camera connections and frame streaming.
    
    Features:
    - Auto-detection of cameras
    - Multi-camera support
    - Automatic reconnection with backoff
    - Frame caching
    - Health monitoring
    """
    
    def __init__(self, config: CameraConfig):
        """
        Initialize CameraManager.
        
        Args:
            config: Camera configuration
        """
        self.config = config
        self.cameras: Dict[str, CameraDriver] = {}
        self.camera_health: Dict[str, dict] = {}
        self.reconnect_intervals: Dict[str, int] = {}
        self.last_reconnect_attempt: Dict[str, float] = {}
        self.frame_cache: Dict[str, Optional[tuple]] = {}  # (frame, timestamp)
        self._lock = threading.RLock()
        self._running = False
    
    def initialize(self) -> bool:
        """
        Initialize and connect to cameras.
        
        Returns:
            True if at least one camera connected, False otherwise
        """
        try:
            logger.info("Initializing camera manager...")
            
            if not self.config.enabled:
                logger.info("Camera system disabled in configuration")
                return False
            
            # Auto-detect built-in camera
            if self._detect_and_connect_builtin():
                self._running = True
                logger.info(f"Camera manager initialized with {len(self.cameras)} camera(s)")
                return True
            
            logger.warning("No cameras available")
            return False
            
        except Exception as e:
            logger.error(f"Error initializing camera manager: {e}")
            return False
    
    def _detect_and_connect_builtin(self) -> bool:
        """
        Detect and connect to built-in camera.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Detecting built-in camera...")
            
            # Try to open built-in camera
            driver = BuiltinCameraDriver(
                camera_index=0,
                name="builtin",
                target_fps=self.config.fps,
                resolution="720p"
            )
            
            if driver.connect():
                camera_id = driver.camera_id
                self.cameras[camera_id] = driver
                self.camera_health[camera_id] = {
                    "connected": True,
                    "last_frame_time": datetime.utcnow(),
                    "frame_count": 0,
                    "error_count": 0,
                }
                self.reconnect_intervals[camera_id] = self.config.reconnect_interval
                
                # Save to database
                self._save_camera_to_db(driver)
                
                logger.info(f"Built-in camera detected and connected: {camera_id}")
                return True
            
            logger.warning("Failed to connect to built-in camera")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting built-in camera: {e}")
            return False
    
    def _save_camera_to_db(self, driver: CameraDriver):
        """Save camera info to database."""
        try:
            session = get_db_session()
            
            # Check if already exists
            existing = session.query(Camera).filter_by(
                name=driver.name,
                camera_type="builtin"
            ).first()
            
            if existing:
                session.close()
                return
            
            # Create new camera record
            camera = Camera(
                name=driver.name,
                camera_type="builtin",
                enabled=True,
                connection_status="connected",
            )
            
            session.add(camera)
            session.commit()
            session.close()
            
            logger.info(f"Camera saved to database: {driver.name}")
            
        except Exception as e:
            logger.error(f"Error saving camera to database: {e}")
    
    def get_camera(self, camera_id: Optional[str] = None) -> Optional[CameraDriver]:
        """
        Get a camera by ID or return the first connected camera.
        
        Args:
            camera_id: Camera ID (if None, returns first camera)
        
        Returns:
            CameraDriver or None if not found
        """
        with self._lock:
            if camera_id:
                return self.cameras.get(camera_id)
            
            # Return first connected camera
            for driver in self.cameras.values():
                if driver.is_connected:
                    return driver
            
            return None
    
    def get_frame(self, camera_id: Optional[str] = None) -> Optional[tuple]:
        """
        Get a frame from camera.
        
        Args:
            camera_id: Camera ID (if None, uses first connected camera)
        
        Returns:
            Tuple of (frame, timestamp, camera_id) or None if failed
        """
        with self._lock:
            driver = self.get_camera(camera_id)
            
            if driver is None:
                return None
            
            try:
                frame = driver.get_frame()
                
                if frame is None:
                    self.camera_health[driver.camera_id]["error_count"] += 1
                    return None
                
                # Update health
                health = self.camera_health[driver.camera_id]
                health["last_frame_time"] = datetime.utcnow()
                health["frame_count"] += 1
                
                # Cache frame
                self.frame_cache[driver.camera_id] = (frame, datetime.utcnow(), driver.camera_id)
                
                return (frame, datetime.utcnow(), driver.camera_id)
                
            except Exception as e:
                logger.error(f"Error getting frame from {driver.name}: {e}")
                self.camera_health[driver.camera_id]["error_count"] += 1
                return None
    
    def check_health(self):
        """
        Check camera health and attempt reconnection if needed.
        
        This should be called periodically (e.g., every 30 seconds).
        """
        with self._lock:
            for camera_id, driver in list(self.cameras.items()):
                try:
                    if not driver.is_alive():
                        logger.warning(f"Camera {driver.name} is not responding")
                        self._attempt_reconnect(camera_id, driver)
                    else:
                        # Update health
                        self.camera_health[camera_id]["connected"] = True
                        self.reconnect_intervals[camera_id] = self.config.reconnect_interval
                
                except Exception as e:
                    logger.error(f"Error checking camera health: {e}")
    
    def _attempt_reconnect(self, camera_id: str, driver: CameraDriver):
        """
        Attempt to reconnect to a camera with exponential backoff.
        
        Args:
            camera_id: Camera ID
            driver: Camera driver instance
        """
        try:
            current_time = time.time()
            last_attempt = self.last_reconnect_attempt.get(camera_id, 0)
            interval = self.reconnect_intervals.get(camera_id, self.config.reconnect_interval)
            
            # Check if enough time has passed since last attempt
            if current_time - last_attempt < interval:
                return
            
            logger.info(f"Attempting to reconnect to {driver.name}...")
            
            # Disconnect
            driver.disconnect()
            
            # Reconnect
            if driver.connect():
                logger.info(f"Successfully reconnected to {driver.name}")
                self.camera_health[camera_id]["connected"] = True
                self.reconnect_intervals[camera_id] = self.config.reconnect_interval
            else:
                logger.warning(f"Failed to reconnect to {driver.name}")
                self.camera_health[camera_id]["connected"] = False
                
                # Increase backoff interval (max 5 minutes)
                self.reconnect_intervals[camera_id] = min(interval * 2, 300)
            
            self.last_reconnect_attempt[camera_id] = current_time
            
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
    
    def get_status(self) -> dict:
        """
        Get status of all cameras.
        
        Returns:
            Dictionary with camera status information
        """
        with self._lock:
            status = {}
            
            for camera_id, driver in self.cameras.items():
                health = self.camera_health.get(camera_id, {})
                status[camera_id] = {
                    "name": driver.name,
                    "connected": driver.is_connected,
                    "alive": driver.is_alive(),
                    "resolution": driver.get_resolution(),
                    "fps": driver.get_fps(),
                    "frame_count": health.get("frame_count", 0),
                    "error_count": health.get("error_count", 0),
                    "last_frame_time": health.get("last_frame_time"),
                }
            
            return status
    
    def shutdown(self):
        """Shutdown camera manager and disconnect all cameras."""
        with self._lock:
            logger.info("Shutting down camera manager...")
            
            self._running = False
            
            for driver in self.cameras.values():
                try:
                    driver.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting camera: {e}")
            
            self.cameras.clear()
            logger.info("Camera manager shutdown complete")
