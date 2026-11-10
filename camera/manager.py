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
        self.camera_db_ids: Dict[str, int] = {}
        self.camera_health: Dict[str, dict] = {}
        self.reconnect_intervals: Dict[str, int] = {}
        self.last_reconnect_attempt: Dict[str, float] = {}
        self.frame_cache: Dict[str, Optional[tuple]] = {}  # (frame, timestamp)
        self._lock = threading.RLock()
        self._running = False
    
    def initialize(self) -> bool:
        from config.settings import get_config
        from config.profiles import profiles_from_config
        from types import SimpleNamespace
        settings=get_config()
        profiles=profiles_from_config(SimpleNamespace(camera=self.config,motion=settings.motion,recording=settings.recording))
        self.profiles={}
        if not self.config.enabled:
            return False
        for profile in profiles:
            if not profile.enabled:
                continue
            driver=BuiltinCameraDriver(profile.index,profile.name,profile.fps,profile.resolution)
            connected=driver.connect()
            camera_id=driver.camera_id
            self.cameras[camera_id]=driver
            self.profiles[camera_id]=profile
            db_id=self._save_camera_to_db(driver)
            if db_id is not None:
                self.camera_db_ids[camera_id]=db_id
            self.camera_health[camera_id]={'connected':connected,'last_frame_time':None,'frame_count':0,'error_count':0}
            self.reconnect_intervals[camera_id]=self.config.reconnect_interval
        self._running=True
        return any(driver.is_connected for driver in self.cameras.values())

    def discover(self, max_devices=8):
        """Bounded local-device discovery; never opens a second handle to an active feed."""
        found=[]
        for index in range(min(max_devices,16)):
            current=self.cameras.get(f'builtin_{index}')
            if current and current.is_connected:
                found.append({'index':index,'name':current.name,'connected':True,
                              'resolution':current.get_resolution(),'fps':current.get_fps()})
                continue
            candidate=BuiltinCameraDriver(index,f'Camera {index+1}')
            try:
                if candidate.connect():
                    found.append({'index':index,'name':candidate.name,'connected':True,
                                  'resolution':candidate.get_resolution(),'fps':candidate.get_fps()})
            finally:
                candidate.disconnect()
        return found

    def _save_camera_to_db(self, driver):
        try:
            with get_db_session() as session:
                address=f'device:{driver.camera_index}'
                camera=session.query(Camera).filter(Camera.url==address).first()
                if camera is None:
                    camera=session.query(Camera).filter(Camera.name==driver.name).first()
                if camera is None:
                    camera=Camera(name=driver.name,camera_type='builtin')
                    session.add(camera)
                camera.name=driver.name
                camera.url=address
                camera.enabled=True
                camera.connection_status='connected' if driver.is_connected else 'disconnected'
                session.commit()
                return camera.id
        except Exception:
            logger.exception('Unable to save camera metadata')
            return None

    def get_camera_database_id(self, camera_id: Optional[str] = None) -> Optional[int]:
        """
        Get the database camera ID for a driver camera ID.

        Args:
            camera_id: Driver camera ID (if None, resolves the first connected camera)

        Returns:
            Database camera ID or None if it cannot be resolved
        """
        with self._lock:
            driver = self.get_camera(camera_id)
            if driver is None:
                return None

            db_id = self.camera_db_ids.get(driver.camera_id)
            if db_id is not None:
                return db_id

            try:
                session = get_db_session()
                camera = session.query(Camera).filter_by(
                    name=driver.name,
                    camera_type="builtin"
                ).first()
                session.close()

                if camera:
                    self.camera_db_ids[driver.camera_id] = camera.id
                    return camera.id
            except Exception as e:
                logger.error(f"Error resolving camera database ID: {e}")

            return None
    
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
    
    def get_frame(self, camera_id=None):
        # Capture outside the manager lock so a slow feed cannot serialize other cameras.
        driver=self.get_camera(camera_id)
        if driver is None or not driver.is_connected:
            return None
        frame=driver.get_frame()
        timestamp=datetime.utcnow()
        with self._lock:
            health=self.camera_health[driver.camera_id]
            if frame is None:
                health['error_count']+=1
                return None
            health['last_frame_time']=timestamp
            health['frame_count']+=1
            self.frame_cache[driver.camera_id]=(frame,timestamp,driver.camera_id)
        return frame,timestamp,driver.camera_id

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
                        if self.config.auto_reconnect:
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
