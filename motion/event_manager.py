"""Per-camera motion lifecycle with bounded history and throttled persistence."""
from collections import deque
from datetime import datetime,timedelta
import time
from database import get_db_session, MotionEvent


class MotionEventManager:
    def __init__(self):
        self.current_event_id=None
        self.current_event=None
        self.event_history=deque(maxlen=100)
        self.last_write=0

    def on_motion_detected(self,camera_id,result):
        if self.current_event_id is None:
            with get_db_session() as session:
                event=MotionEvent(camera_id=camera_id,start_time=result.frame_timestamp,
                    contour_count=result.contour_count,max_contour_area=int(result.max_contour_area),sensitivity_level=0)
                session.add(event); session.commit()
                self.current_event=event; self.current_event_id=event.id
            self.last_write=time.monotonic()
            return event
        self.current_event.contour_count=result.contour_count
        self.current_event.max_contour_area=max(self.current_event.max_contour_area,int(result.max_contour_area))
        if time.monotonic()-self.last_write>=1:
            with get_db_session() as session:
                session.merge(self.current_event);session.commit()
            self.last_write=time.monotonic()
        return None

    def on_motion_ended(self):
        if self.current_event_id is None:
            return None
        event=self.current_event;event.end_time=datetime.utcnow()
        with get_db_session() as session:
            session.merge(event);session.commit()
        self.event_history.append(event)
        self.current_event_id=None;self.current_event=None
        return event

    def get_recent_events(self,camera_id,hours=24):
        with get_db_session() as session:
            return session.query(MotionEvent).filter(MotionEvent.camera_id==camera_id,
                MotionEvent.start_time>=datetime.utcnow()-timedelta(hours=hours)).order_by(MotionEvent.start_time.desc()).all()

    def get_event_count(self,camera_id,hours=24):
        with get_db_session() as session:
            return session.query(MotionEvent).filter(MotionEvent.camera_id==camera_id,
                MotionEvent.start_time>=datetime.utcnow()-timedelta(hours=hours)).count()

    def get_statistics(self,camera_id,hours=24):
        events=self.get_recent_events(camera_id,hours)
        total=sum((event.end_time-event.start_time).total_seconds() for event in events if event.end_time)
        return {'event_count':len(events),'total_duration_seconds':total,
                'average_duration_seconds':total/len(events) if events else 0}
