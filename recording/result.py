"""
Recording Result Class

Responsibility: Hold the result of a recording write operation.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class RecordingResult:
    """
    Result of a recording write operation.
    
    Contains:
    - Whether the frame was successfully written
    - Timing information
    - Error details if failed
    - Recording metadata
    """
    
    # Write result
    success: bool = False
    
    # Timing
    timestamp: datetime = None
    write_time_ms: float = 0.0
    
    # Frame information
    frame_number: int = 0
    
    # Error information
    error_message: Optional[str] = None
    
    # Recording information
    video_path: Optional[str] = None
    frames_written: int = 0
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    
    def __post_init__(self):
        """Set default timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """
        Convert result to dictionary for logging/storage.
        
        Returns:
            Dictionary representation
        """
        return {
            "success": self.success,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "write_time_ms": self.write_time_ms,
            "frame_number": self.frame_number,
            "error": self.error_message,
            "video_path": self.video_path,
            "frames_written": self.frames_written,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
        }
