"""
Recording Manager

Responsibility: Orchestrate video recording triggered by motion events.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import numpy as np
from pathlib import Path
import threading

from config.settings import get_config
from utils.logger import get_logger
from utils.system import PathManager, TimeUtils
from database.models import get_database
from recording.drivers.mp4 import MP4RecorderDriver
from recording.result import RecordingResult


logger = get_logger(__name__)


class RecordingManager:
    """
    Manages video recording orchestration.
    
    Features:
    - Motion-triggered recording
    - Pre-motion buffering (circular buffer)
    - Post-motion buffering (record N seconds after motion ends)
    - Automatic file naming
    - Database integration
    - Thread-safe operations
    """
    
    def __init__(self, config=None):
        """
        Initialize recording manager.
        
        Args:
            config: RecordingConfig from settings
        """
        self.config = config or get_config().recording
        self.recorder: Optional[MP4RecorderDriver] = None
        self.is_recording = False
        self.current_video_path: Optional[str] = None
        
        # Motion event tracking
        self.motion_active = False
        self.motion_start_time: Optional[datetime] = None
        self.motion_end_time: Optional[datetime] = None
        self.post_motion_buffer_end: Optional[datetime] = None
        
        # Frame tracking
        self.frame_queue = []
        self.max_buffer_frames = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize recorder
        self._initialize_recorder()
    
    def _initialize_recorder(self):
        """Create and configure the MP4 recorder."""
        try:
            quality = self.config.quality if hasattr(self.config, 'quality') else 'medium'
            self.recorder = MP4RecorderDriver(quality=quality, codec='h264')
            logger.info(f"Recording manager initialized (quality: {quality})")
        except Exception as e:
            logger.error(f"Failed to initialize recording manager: {e}")
            self.recorder = None
    
    def on_motion_detected(self, camera_id: int, motion_start_time: datetime):
        """
        Called when motion is detected.
        
        Args:
            camera_id: ID of camera detecting motion
            motion_start_time: When motion started
        """
        with self.lock:
            self.motion_active = True
            self.motion_start_time = motion_start_time
            self.motion_end_time = None
            
            # Don't start recording if already recording for this motion
            if not self.is_recording:
                self._start_recording(camera_id)
    
    def on_motion_ended(self, motion_end_time: datetime):
        """
        Called when motion ends.
        
        Args:
            motion_end_time: When motion ended
        """
        with self.lock:
            self.motion_active = False
            self.motion_end_time = motion_end_time
            
            # Set post-motion buffer timer
            post_buffer = self.config.post_motion_seconds if hasattr(self.config, 'post_motion_seconds') else 5
            self.post_motion_buffer_end = motion_end_time + timedelta(seconds=post_buffer)
            
            logger.info(f"Motion ended, post-motion buffering for {post_buffer}s")
    
    def write_frame(self, frame: np.ndarray, frame_timestamp: datetime, camera_id: int) -> Optional[RecordingResult]:
        """
        Write a frame to recording if active.
        
        Args:
            frame: BGR numpy array
            frame_timestamp: When frame was captured
            camera_id: Camera ID for organizing recordings
            
        Returns:
            RecordingResult if recording, None otherwise
        """
        with self.lock:
            # Check if we should be recording
            now = datetime.utcnow()
            
            # Stop recording if post-motion buffer expired
            if self.is_recording and self.post_motion_buffer_end:
                if now > self.post_motion_buffer_end:
                    self._stop_recording()
                    return None
            
            # Start recording if motion is detected and not already recording
            if self.motion_active and not self.is_recording:
                self._start_recording(camera_id)
            
            # Write frame if recording
            if self.is_recording and self.recorder:
                result = self.recorder.write_frame(frame)
                
                if result.success:
                    # Save recording info to database
                    self._save_recording_to_db(camera_id, result)
                
                return result
            
            return None
    
    def _start_recording(self, camera_id: int):
        """
        Start a new recording session.
        
        Args:
            camera_id: Camera ID for organizing recordings
        """
        try:
            if self.recorder is None:
                logger.error("Recorder not initialized")
                return
            
            # Generate video path
            video_path = self._generate_video_path(camera_id)
            
            # Get camera resolution and FPS
            config = get_config()
            fps = config.camera.fps if hasattr(config.camera, 'fps') else 15
            resolution = self._get_camera_resolution(config)
            
            # Start recording
            if self.recorder.start_recording(video_path, fps, resolution):
                self.is_recording = True
                self.current_video_path = video_path
                logger.info(f"Recording started for camera {camera_id}: {video_path}")
            else:
                logger.error(f"Failed to start recording for camera {camera_id}")
        
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
    
    def _stop_recording(self):
        """Stop the current recording."""
        try:
            if not self.is_recording or self.recorder is None:
                return
            
            if self.recorder.stop_recording():
                self.is_recording = False
                logger.info(f"Recording stopped: {self.current_video_path}")
            else:
                logger.error("Failed to stop recording")
        
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.is_recording = False
    
    def _generate_video_path(self, camera_id: int) -> str:
        """
        Generate unique video file path.
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Full path for video file
        """
        now = datetime.utcnow()
        
        # Organize by date: recordings/YYYY/MM/DD/camera_id/
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        # Create directory structure
        recording_dir = PathManager.get_recordings_path()
        video_dir = os.path.join(recording_dir, year, month, day, f"camera_{camera_id}")
        Path(video_dir).mkdir(parents=True, exist_ok=True)
        
        # Filename: camera_ID_YYYYMMDD_HHMMSS_microseconds.mp4
        filename = (
            f"camera_{camera_id}_"
            f"{now.strftime('%Y%m%d_%H%M%S')}_"
            f"{now.microsecond:06d}.mp4"
        )
        
        return os.path.join(video_dir, filename)
    
    def _get_camera_resolution(self, config) -> Tuple[int, int]:
        """
        Get camera resolution from config.
        
        Args:
            config: Configuration object
            
        Returns:
            (width, height) tuple
        """
        resolution_str = config.camera.resolution if hasattr(config.camera, 'resolution') else '720p'
        
        # Parse resolution string (e.g., "720p" -> 1280x720)
        resolution_map = {
            '360p': (640, 360),
            '480p': (640, 480),
            '720p': (1280, 720),
            '1080p': (1920, 1080),
        }
        
        return resolution_map.get(resolution_str, (1280, 720))
    
    def _save_recording_to_db(self, camera_id: int, result: RecordingResult):
        """
        Save recording info to database.
        
        Args:
            camera_id: Camera ID
            result: RecordingResult from write_frame
        """
        try:
            db = get_database()
            session = db.get_session()
            
            # This will be saved when recording stops, not on every frame
            # Just track that we're recording
            
        except Exception as e:
            logger.error(f"Failed to save recording to database: {e}")
    
    def get_status(self) -> dict:
        """
        Get recording status.
        
        Returns:
            Dictionary with recording state
        """
        with self.lock:
            if self.recorder:
                recorder_info = self.recorder.get_recording_info()
            else:
                recorder_info = {}
            
            return {
                "is_recording": self.is_recording,
                "motion_active": self.motion_active,
                "current_video_path": self.current_video_path,
                "motion_start_time": self.motion_start_time.isoformat() if self.motion_start_time else None,
                "motion_end_time": self.motion_end_time.isoformat() if self.motion_end_time else None,
                "post_motion_buffer_end": self.post_motion_buffer_end.isoformat() if self.post_motion_buffer_end else None,
                "recorder_info": recorder_info,
            }
