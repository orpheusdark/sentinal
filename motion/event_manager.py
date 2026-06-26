"""
Motion Event Manager for Project Sentinel

Responsibility: Manage motion events, trigger actions, and store to database.
"""

from datetime import datetime, timedelta
from typing import Optional, List
import logging

from database import get_db_session, MotionEvent, Camera
from .result import MotionResult

logger = logging.getLogger(__name__)


class MotionEventManager:
    """
    Manages motion detection events.
    
    Responsibilities:
    - Track motion events
    - Trigger recording on motion
    - Store events to database
    - Generate motion statistics
    """
    
    def __init__(self):
        """Initialize motion event manager."""
        self.current_event: Optional[MotionEvent] = None
        self.event_history: List[MotionEvent] = []
    
    def on_motion_detected(
        self,
        camera_id: int,
        result: MotionResult
    ) -> Optional[MotionEvent]:
        """
        Handle motion detection event.
        
        Args:
            camera_id: Camera database ID
            result: Motion detection result
        
        Returns:
            MotionEvent if event created/updated, None otherwise
        """
        try:
            session = get_db_session()
            
            # Check if already in active motion event
            if self.current_event is None or self.current_event.camera_id != camera_id:
                # Start new event
                event = MotionEvent(
                    camera_id=camera_id,
                    start_time=result.frame_timestamp,
                    contour_count=result.contour_count,
                    max_contour_area=int(result.max_contour_area),
                    sensitivity_level=0,  # Will be set from config
                )
                
                session.add(event)
                session.commit()
                
                self.current_event = event
                logger.info(
                    f"Motion event started: camera_id={camera_id}, "
                    f"contours={result.contour_count}, "
                    f"area={int(result.max_contour_area)}"
                )
                
                session.close()
                return event
            else:
                # Update existing event
                self.current_event.contour_count = result.contour_count
                self.current_event.max_contour_area = max(
                    self.current_event.max_contour_area,
                    int(result.max_contour_area)
                )
                
                session.merge(self.current_event)
                session.commit()
                session.close()
                
                return self.current_event
            
        except Exception as e:
            logger.error(f"Error recording motion event: {e}")
            return None
    
    def on_motion_ended(self) -> Optional[MotionEvent]:
        """
        Handle end of motion event.
        
        Returns:
            Completed MotionEvent or None
        """
        if self.current_event is None:
            return None
        
        try:
            session = get_db_session()
            
            # Update event with end time
            self.current_event.end_time = datetime.utcnow()
            
            session.merge(self.current_event)
            session.commit()
            
            event = self.current_event
            logger.info(
                f"Motion event ended: id={event.id}, "
                f"duration={(event.end_time - event.start_time).total_seconds():.1f}s"
            )
            
            self.event_history.append(event)
            self.current_event = None
            
            session.close()
            return event
            
        except Exception as e:
            logger.error(f"Error ending motion event: {e}")
            return None
    
    def get_recent_events(self, camera_id: int, hours: int = 24) -> List[MotionEvent]:
        """
        Get recent motion events for a camera.
        
        Args:
            camera_id: Camera database ID
            hours: Number of hours to look back
        
        Returns:
            List of motion events
        """
        try:
            session = get_db_session()
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            events = session.query(MotionEvent).filter(
                MotionEvent.camera_id == camera_id,
                MotionEvent.start_time >= cutoff_time
            ).order_by(MotionEvent.start_time.desc()).all()
            
            session.close()
            return events
            
        except Exception as e:
            logger.error(f"Error retrieving events: {e}")
            return []
    
    def get_event_count(self, camera_id: int, hours: int = 24) -> int:
        """
        Get count of motion events in time period.
        
        Args:
            camera_id: Camera database ID
            hours: Number of hours to look back
        
        Returns:
            Count of events
        """
        return len(self.get_recent_events(camera_id, hours))
    
    def get_statistics(self, camera_id: int, hours: int = 24) -> dict:
        """
        Get motion statistics for a camera.
        
        Args:
            camera_id: Camera database ID
            hours: Number of hours to look back
        
        Returns:
            Dictionary with statistics
        """
        events = self.get_recent_events(camera_id, hours)
        
        if not events:
            return {
                "event_count": 0,
                "total_duration_seconds": 0,
                "average_duration_seconds": 0,
            }
        
        total_duration = timedelta(0)
        for event in events:
            if event.end_time:
                total_duration += (event.end_time - event.start_time)
        
        return {
            "event_count": len(events),
            "total_duration_seconds": total_duration.total_seconds(),
            "average_duration_seconds": total_duration.total_seconds() / len(events),
        }
