"""
Abstract Recording Driver

Responsibility: Define the interface for all recording implementations.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np
from recording.result import RecordingResult


class RecorderDriver(ABC):
    """
    Abstract base class for all recording implementations.
    
    Defines the interface for recording video frames to disk.
    
    Implementations:
    - MP4RecorderDriver (H.264, H.265)
    - Future: MJPEG, custom codecs, cloud streaming
    """
    
    @abstractmethod
    def start_recording(self, video_path: str, fps: float, resolution: Tuple[int, int]) -> bool:
        """
        Start a new recording session.
        
        Args:
            video_path: Full path where video will be saved
            fps: Frames per second
            resolution: (width, height) tuple
            
        Returns:
            True if recording started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def write_frame(self, frame: np.ndarray) -> RecordingResult:
        """
        Write a frame to the current recording.
        
        Args:
            frame: BGR numpy array (height, width, 3)
            
        Returns:
            RecordingResult with success status and metadata
        """
        pass
    
    @abstractmethod
    def stop_recording(self) -> bool:
        """
        Stop the current recording and close the file.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def is_recording(self) -> bool:
        """
        Check if recording is currently active.
        
        Returns:
            True if recording is in progress, False otherwise
        """
        pass
    
    @abstractmethod
    def get_recording_info(self) -> dict:
        """
        Get information about the current recording.
        
        Returns:
            Dictionary with:
            - video_path: current file path
            - fps: frames per second
            - resolution: (width, height)
            - frames_written: number of frames written
            - duration_seconds: recording duration
            - file_size_bytes: current file size
        """
        pass
