"""
Motion Detection Result Class

Responsibility: Hold the result of motion detection on a frame.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime
import numpy as np


@dataclass
class MotionResult:
    """
    Result of motion detection on a frame.
    
    Contains:
    - Whether motion was detected
    - Contours and their properties
    - Visualization data
    - Timing information
    """
    
    # Motion detection result
    motion_detected: bool = False
    
    # Frame information
    frame_timestamp: datetime = field(default_factory=datetime.utcnow)
    frame_shape: Tuple[int, int, int] = (0, 0, 3)  # (height, width, channels)
    
    # Contour information
    contour_count: int = 0
    contours: List[np.ndarray] = field(default_factory=list)
    max_contour_area: float = 0.0
    min_contour_area: float = float('inf')
    total_contour_area: float = 0.0
    
    # Background model
    background_age: int = 0  # Number of frames since background learned
    
    # Visualization
    frame_with_contours: np.ndarray = None  # Frame with drawn contours
    
    # Processing information
    processing_time_ms: float = 0.0
    
    def __post_init__(self):
        """Validate result data."""
        if self.frame_with_contours is None:
            # Create empty frame if not provided
            height, width, channels = self.frame_shape
            self.frame_with_contours = np.zeros((height, width, channels), dtype=np.uint8)
    
    def to_dict(self) -> dict:
        """
        Convert result to dictionary for logging/storage.
        
        Returns:
            Dictionary representation (without frame data)
        """
        return {
            "motion_detected": self.motion_detected,
            "timestamp": self.frame_timestamp.isoformat(),
            "frame_shape": self.frame_shape,
            "contour_count": self.contour_count,
            "max_contour_area": float(self.max_contour_area),
            "min_contour_area": float(self.min_contour_area) if self.min_contour_area != float('inf') else 0,
            "total_contour_area": float(self.total_contour_area),
            "background_age": self.background_age,
            "processing_time_ms": self.processing_time_ms,
        }
