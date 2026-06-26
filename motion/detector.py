"""
Motion Detection Engine for Project Sentinel

Responsibility: Lightweight motion detection using background subtraction.
Target: <5% CPU usage at 720p 15FPS.
"""

import cv2
import numpy as np
from datetime import datetime
import time
import logging

from config import MotionConfig
from .result import MotionResult

logger = logging.getLogger(__name__)


class MotionDetector:
    """
    Lightweight motion detection using background subtraction.
    
    Algorithm:
    - MOG2 (Mixture of Gaussians) for background modeling
    - Morphological operations for noise reduction
    - Contour detection and filtering
    
    Target CPU usage: <5% (compared to 25% for ML models)
    """
    
    def __init__(self, config: MotionConfig):
        """
        Initialize motion detector.
        
        Args:
            config: Motion detection configuration
        """
        self.config = config
        
        # Background subtractor (MOG2)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True
        )
        
        # Morphological operations
        self.kernel_open = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.config.morph_kernel_size, self.config.morph_kernel_size)
        )
        self.kernel_close = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.config.morph_kernel_size * 2, self.config.morph_kernel_size * 2)
        )
        
        # State tracking
        self.frame_count = 0
        self.motion_cooldown = 0
        
        logger.info(f"Motion detector initialized")
        logger.info(f"  Sensitivity: {config.sensitivity}")
        logger.info(f"  Min contour area: {config.min_contour_area} pixels")
        logger.info(f"  Cooldown: {config.cooldown_seconds} seconds")
    
    def process_frame(self, frame: np.ndarray) -> MotionResult:
        """
        Process a frame and detect motion.
        
        Args:
            frame: Input frame (BGR format)
        
        Returns:
            MotionResult with detection results
        """
        start_time = time.time()
        
        result = MotionResult()
        result.frame_timestamp = datetime.utcnow()
        result.frame_shape = frame.shape
        
        try:
            self.frame_count += 1
            
            # Update background model
            fg_mask = self.bg_subtractor.apply(frame)
            result.background_age = self.frame_count
            
            # Noise reduction: morphological operations
            # Remove small noise (opening)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel_open)
            
            # Fill small holes (closing)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel_close)
            
            # Find contours
            contours, _ = cv2.findContours(
                fg_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Filter contours by area and sensitivity
            valid_contours = []
            total_area = 0
            max_area = 0
            min_area = float('inf')
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Check if area meets threshold
                if area >= self.config.min_contour_area:
                    valid_contours.append(contour)
                    total_area += area
                    max_area = max(max_area, area)
                    min_area = min(min_area, area)
            
            # Store results
            result.contour_count = len(valid_contours)
            result.contours = valid_contours
            result.max_contour_area = max_area
            result.min_contour_area = min_area if min_area != float('inf') else 0
            result.total_contour_area = total_area
            
            # Determine motion detection based on sensitivity
            motion_detected = self._evaluate_motion(result)
            
            # Apply cooldown
            if motion_detected:
                result.motion_detected = True
                self.motion_cooldown = int(self.config.cooldown_seconds * 30)  # Assuming 30 FPS base
            elif self.motion_cooldown > 0:
                result.motion_detected = True
                self.motion_cooldown -= 1
            else:
                result.motion_detected = False
            
            # Draw contours for visualization
            result.frame_with_contours = frame.copy()
            if result.contours:
                cv2.drawContours(
                    result.frame_with_contours,
                    result.contours,
                    -1,  # Draw all contours
                    (0, 255, 0),  # Green
                    2  # Line thickness
                )
            
            # Add status text
            text = f"Motion: {result.motion_detected} | Contours: {result.contour_count} | Area: {int(total_area)}"
            cv2.putText(
                result.frame_with_contours,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
            
            # Calculate processing time
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Log periodically
            if self.frame_count % 150 == 0:  # Every 5 seconds at 30 FPS
                logger.debug(
                    f"Motion detection: {result.motion_detected}, "
                    f"Contours: {result.contour_count}, "
                    f"Area: {int(total_area)}, "
                    f"Time: {result.processing_time_ms:.1f}ms"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            result.motion_detected = False
            result.frame_with_contours = frame.copy()
            return result
    
    def _evaluate_motion(self, result: MotionResult) -> bool:
        """
        Evaluate if motion is present based on contours and sensitivity.
        
        Sensitivity scale (0-100):
        - 0-20: Very sensitive (any movement triggers)
        - 20-40: Sensitive (small movements)
        - 40-60: Normal (medium movements) <- Default: 40
        - 60-80: Less sensitive (larger movements)
        - 80-100: Very insensitive (only large movements)
        
        Args:
            result: Motion detection result
        
        Returns:
            True if motion detected, False otherwise
        """
        if result.contour_count == 0:
            return False
        
        # Convert sensitivity to area threshold
        # Sensitivity 0-100 -> min_area multiplier 0.1x to 10x
        sensitivity_multiplier = (100 - self.config.sensitivity) / 10.0
        effective_min_area = self.config.min_contour_area * sensitivity_multiplier
        
        # Motion detected if max contour exceeds threshold
        return result.max_contour_area >= effective_min_area
    
    def reset(self):
        """Reset background model."""
        logger.info("Resetting background model...")
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True
        )
        self.frame_count = 0
        self.motion_cooldown = 0
    
    def get_statistics(self) -> dict:
        """
        Get motion detector statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "frame_count": self.frame_count,
            "sensitivity": self.config.sensitivity,
            "min_contour_area": self.config.min_contour_area,
            "cooldown_seconds": self.config.cooldown_seconds,
        }
