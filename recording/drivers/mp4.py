"""
MP4 Recorder Driver

Responsibility: Implement H.264 video recording using OpenCV VideoWriter.
"""

import cv2
import numpy as np
import os
from datetime import datetime
from typing import Tuple, Optional
from pathlib import Path
import time

from recording.base_driver import RecorderDriver
from recording.result import RecordingResult
from utils.logger import get_logger


logger = get_logger(__name__)


class MP4RecorderDriver(RecorderDriver):
    """
    MP4 video recorder using OpenCV VideoWriter.
    
    Features:
    - H.264 codec (mp4v)
    - Configurable bitrate/quality
    - Error resilience
    - File size tracking
    """
    
    # Quality presets mapping to bitrate targets
    QUALITY_PRESETS = {
        'low': 1000,      # 1 Mbps - very compressed
        'medium': 2500,   # 2.5 Mbps - balanced (default)
        'high': 5000,     # 5 Mbps - high quality
    }
    
    # Codec fourcc codes
    CODEC_H264 = cv2.VideoWriter_fourcc(*'mp4v')
    CODEC_MJPEG = cv2.VideoWriter_fourcc(*'MJPG')
    
    def __init__(self, quality: str = 'medium', codec: str = 'h264'):
        """
        Initialize MP4 recorder.
        
        Args:
            quality: 'low', 'medium', or 'high' - affects file size
            codec: 'h264' or 'mjpeg'
        """
        self.quality = quality.lower()
        self.codec = codec.lower()
        
        if self.quality not in self.QUALITY_PRESETS:
            logger.warning(f"Unknown quality '{self.quality}', using 'medium'")
            self.quality = 'medium'
        
        self.bitrate = self.QUALITY_PRESETS[self.quality]
        
        # Recording state
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.video_path: Optional[str] = None
        self.fps: float = 15.0
        self.resolution: Tuple[int, int] = (1280, 720)
        self.frames_written: int = 0
        self.start_time: Optional[datetime] = None
        self.start_frame_time: Optional[float] = None
    
    def start_recording(self, video_path: str, fps: float, resolution: Tuple[int, int]) -> bool:
        """
        Start a new MP4 recording.
        
        Args:
            video_path: Full path where video will be saved (must end with .mp4)
            fps: Frames per second
            resolution: (width, height) tuple
            
        Returns:
            True if recording started successfully
        """
        try:
            # Stop any existing recording
            if self.video_writer is not None:
                self.stop_recording()
            
            # Validate path
            if not video_path.endswith('.mp4'):
                logger.warning(f"Video path should end with .mp4: {video_path}")
                video_path = video_path.rstrip('.') + '.mp4'
            
            # Create directory if needed
            video_dir = os.path.dirname(video_path)
            if video_dir and not os.path.exists(video_dir):
                Path(video_dir).mkdir(parents=True, exist_ok=True)
            
            # Set recording parameters
            self.video_path = video_path
            self.fps = fps
            self.resolution = resolution
            self.frames_written = 0
            self.start_time = datetime.utcnow()
            self.start_frame_time = time.time()
            
            # Create video writer
            if self.codec == 'h264':
                fourcc = self.CODEC_H264
            else:
                fourcc = self.CODEC_MJPEG
            
            self.video_writer = cv2.VideoWriter(
                video_path,
                fourcc,
                fps,
                resolution
            )
            
            if not self.video_writer.isOpened():
                logger.error(f"Failed to open video writer for {video_path}")
                self.video_writer = None
                return False
            
            logger.info(
                f"Recording started: {video_path} "
                f"({resolution[0]}x{resolution[1]} @ {fps} FPS, {self.quality} quality)"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.video_writer = None
            return False
    
    def write_frame(self, frame: np.ndarray) -> RecordingResult:
        """
        Write a frame to the current recording.
        
        Args:
            frame: BGR numpy array (height, width, 3)
            
        Returns:
            RecordingResult with write status
        """
        result = RecordingResult(
            timestamp=datetime.utcnow(),
            frame_number=self.frames_written
        )
        
        try:
            if self.video_writer is None:
                result.success = False
                result.error_message = "Recording not started"
                return result
            
            # Ensure frame is BGR and correct size
            if frame.shape[:2] != self.resolution[::-1]:
                # Resize frame to match recording resolution
                frame = cv2.resize(frame, self.resolution, interpolation=cv2.INTER_LINEAR)
            
            # Convert to BGR if needed (OpenCV uses BGR)
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                logger.warning(f"Frame has unexpected shape: {frame.shape}")
                result.success = False
                result.error_message = f"Invalid frame shape: {frame.shape}"
                return result
            
            write_start = time.time()
            self.video_writer.write(frame)
            result.write_time_ms = (time.time() - write_start) * 1000
            
            self.frames_written += 1
            result.frames_written = self.frames_written
            
            # Calculate duration
            if self.start_frame_time:
                elapsed = time.time() - self.start_frame_time
                result.duration_seconds = elapsed
            
            # Get file size
            if os.path.exists(self.video_path):
                result.file_size_bytes = os.path.getsize(self.video_path)
            
            result.success = True
            result.video_path = self.video_path
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to write frame: {e}")
            result.success = False
            result.error_message = str(e)
            return result
    
    def stop_recording(self) -> bool:
        """
        Stop recording and close the file.
        
        Returns:
            True if stopped successfully
        """
        try:
            if self.video_writer is None:
                return False
            
            # Release the writer
            self.video_writer.release()
            self.video_writer = None
            
            # Log summary
            if self.start_time and self.video_path:
                file_size_mb = 0
                if os.path.exists(self.video_path):
                    file_size_bytes = os.path.getsize(self.video_path)
                    file_size_mb = file_size_bytes / (1024 * 1024)
                
                duration = (datetime.utcnow() - self.start_time).total_seconds()
                
                logger.info(
                    f"Recording stopped: {self.video_path} "
                    f"({self.frames_written} frames, {duration:.1f}s, {file_size_mb:.1f} MB)"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            True if video writer is open
        """
        return self.video_writer is not None and self.video_writer.isOpened()
    
    def get_recording_info(self) -> dict:
        """
        Get information about current recording.
        
        Returns:
            Dictionary with recording metadata
        """
        info = {
            "video_path": self.video_path,
            "fps": self.fps,
            "resolution": self.resolution,
            "frames_written": self.frames_written,
            "quality": self.quality,
            "codec": self.codec,
            "duration_seconds": 0,
            "file_size_bytes": 0,
            "is_recording": self.is_recording(),
        }
        
        if self.start_frame_time:
            info["duration_seconds"] = time.time() - self.start_frame_time
        
        if self.video_path and os.path.exists(self.video_path):
            info["file_size_bytes"] = os.path.getsize(self.video_path)
        
        return info
