"""
WebSocket Stream Manager

Responsibility: Handle live video streaming to web clients via WebSocket.
"""

import cv2
import base64
import threading
from typing import Dict, Set, Optional
from datetime import datetime
import time

from utils.logger import get_logger


logger = get_logger(__name__)


class StreamManager:
    """
    Manage live video streaming to web clients.
    
    Features:
    - Real-time frame streaming
    - Multiple client support
    - Quality adjustment
    - Efficient JPEG encoding
    """
    
    def __init__(self, quality: int = 70, target_fps: int = 15):
        """
        Initialize stream manager.
        
        Args:
            quality: JPEG quality (1-100)
            target_fps: Target FPS for streaming
        """
        self.quality = quality
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        
        # Connected clients
        self.connected_clients: Set[str] = set()
        self.client_lock = threading.RLock()
        
        # Latest frame
        self.current_frame = None
        self.current_timestamp = None
        self.frame_lock = threading.RLock()
        
        logger.info(f"Stream manager initialized (quality: {quality}, fps: {target_fps})")
    
    def register_client(self, client_id: str):
        """
        Register a new streaming client.
        
        Args:
            client_id: Unique client identifier
        """
        with self.client_lock:
            self.connected_clients.add(client_id)
            logger.info(f"Client registered: {client_id} (total: {len(self.connected_clients)})")
    
    def unregister_client(self, client_id: str):
        """
        Unregister a streaming client.
        
        Args:
            client_id: Unique client identifier
        """
        with self.client_lock:
            self.connected_clients.discard(client_id)
            logger.info(f"Client unregistered: {client_id} (total: {len(self.connected_clients)})")
    
    def get_connected_clients(self) -> int:
        """Get number of connected clients."""
        with self.client_lock:
            return len(self.connected_clients)
    
    def update_frame(self, frame):
        """
        Update the current frame for streaming.
        
        Args:
            frame: BGR numpy array to stream
        """
        with self.frame_lock:
            self.current_frame = frame
            self.current_timestamp = datetime.utcnow()
    
    def get_frame_as_jpeg(self) -> Optional[str]:
        """
        Get current frame as JPEG base64 string.
        
        Returns:
            Base64 encoded JPEG frame, or None if no frame available
        """
        with self.frame_lock:
            if self.current_frame is None:
                return None
            
            try:
                # Encode frame as JPEG
                ret, jpeg_data = cv2.imencode('.jpg', self.current_frame, 
                                            [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                
                if not ret:
                    logger.warning("Failed to encode frame as JPEG")
                    return None
                
                # Convert to base64
                jpeg_base64 = base64.b64encode(jpeg_data).decode('utf-8')
                return jpeg_base64
            
            except Exception as e:
                logger.error(f"Error encoding frame: {e}")
                return None
    
    def get_frame_info(self) -> dict:
        """
        Get information about current frame.
        
        Returns:
            Dictionary with frame metadata
        """
        with self.frame_lock:
            info = {
                'timestamp': self.current_timestamp.isoformat() if self.current_timestamp else None,
                'has_frame': self.current_frame is not None,
            }
            
            if self.current_frame is not None:
                height, width = self.current_frame.shape[:2]
                info['width'] = width
                info['height'] = height
            
            return info
    
    def set_quality(self, quality: int):
        """
        Change streaming quality.
        
        Args:
            quality: JPEG quality (1-100)
        """
        if 1 <= quality <= 100:
            self.quality = quality
            logger.info(f"Stream quality changed to {quality}")
        else:
            logger.warning(f"Invalid quality value: {quality}")
    
    def set_fps(self, fps: int):
        """
        Change streaming FPS.
        
        Args:
            fps: Frames per second
        """
        if fps > 0:
            self.target_fps = fps
            self.frame_interval = 1.0 / fps
            logger.info(f"Stream FPS changed to {fps}")
        else:
            logger.warning(f"Invalid FPS value: {fps}")
    
    def get_status(self) -> dict:
        """
        Get stream manager status.
        
        Returns:
            Dictionary with status information
        """
        return {
            'connected_clients': self.get_connected_clients(),
            'quality': self.quality,
            'target_fps': self.target_fps,
            'frame_info': self.get_frame_info(),
        }
