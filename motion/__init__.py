"""Motion detection module for Project Sentinel."""

from .result import MotionResult
from .detector import MotionDetector
from .event_manager import MotionEventManager

__all__ = [
    "MotionResult",
    "MotionDetector",
    "MotionEventManager",
]
