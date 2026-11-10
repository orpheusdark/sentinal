"""One independently paced processing worker and state machine per camera."""
from dataclasses import replace
from datetime import datetime
import logging
import threading
import time
import cv2
from motion import MotionDetector, MotionEventManager
from motion.policy import is_scheduled
from motion.objects import ObjectDetector
from recording import RecordingManager
from web.stream import StreamManager

logger=logging.getLogger(__name__)


class CameraPipeline:
    def __init__(self, camera_id, db_id, profile, config, camera_manager, alerts):
        self.camera_id=camera_id;self.db_id=db_id;self.profile=profile
        self.camera_manager=camera_manager;self.alerts=alerts
        motion=replace(config.motion,enabled=config.motion.enabled and profile.motion_enabled,sensitivity=profile.sensitivity,
                       min_contour_area=profile.min_contour_area,zones=profile.zones,schedule=profile.schedule)
        recording=replace(config.recording,enabled=config.recording.enabled and profile.recording_enabled,record_on_motion=profile.record_on_motion,
                          post_motion_seconds=profile.post_motion_seconds,max_duration_seconds=profile.max_duration_seconds)
        self.detector=MotionDetector(motion)
        self.events=MotionEventManager()
        self.recorder=RecordingManager(recording)
        self.recorder.capture_fps=profile.fps
        self.stream=StreamManager(quality={'low':40,'medium':70,'high':90}[config.streaming.quality],target_fps=profile.fps)
        self.objects=ObjectDetector(motion) if profile.object_detection_enabled else None
        self.object_results=[]
        self.stop_event=threading.Event();self.worker=None
        self.frames=0;self.errors=0;self.last_frame=None;self.processing_ms=0;self.scheduled=True
        self.started=time.monotonic()

    def process(self, frame, timestamp=None):
        timestamp=timestamp or datetime.utcnow()
        before=time.perf_counter()
        self.scheduled=is_scheduled(self.profile.schedule)
        result=self.detector.process_frame(frame)
        detected=result.motion_detected and self.scheduled
        if self.objects and detected:
            self.object_results=self.objects.detect(frame)
            if self.profile.zones:
                height,width=frame.shape[:2]
                self.object_results=[item for item in self.object_results if any(
                    x <= (item['box'][0]+item['box'][2]/2)/width <= x+w and
                    y <= (item['box'][1]+item['box'][3]/2)/height <= y+h
                    for x,y,w,h in self.profile.zones)]
            detected=bool(self.object_results)
        elif not detected:
            self.object_results=[]
        if detected:
            event=self.events.on_motion_detected(self.db_id,result)
            if self.events.current_event_id is not None:
                self.recorder.motion_event_id=self.events.current_event_id
            self.recorder.capture_resolution=(frame.shape[1],frame.shape[0])
            self.recorder.on_motion_detected(self.db_id,timestamp)
            if event and self.alerts and self.alerts.is_configured():
                self.alerts.send_motion_alert(camera_name=self.profile.name,camera_id=self.db_id,
                    timestamp=timestamp,contour_count=result.contour_count,max_contour_area=int(result.max_contour_area))
        elif self.events.current_event_id is not None:
            self.events.on_motion_ended();self.recorder.on_motion_ended(timestamp)
        if self.scheduled:
            self.recorder.capture_resolution=(frame.shape[1],frame.shape[0])
            self.recorder.write_frame(frame,timestamp,self.db_id)
        elif self.recorder.is_recording:
            self.recorder._stop_recording()
        preview=frame.copy()
        for x,y,w,h in self.profile.zones:
            height,width=frame.shape[:2]
            cv2.rectangle(preview,(int(x*width),int(y*height)),(int((x+w)*width),int((y+h)*height)),(213,239,104),2)
        for item in self.object_results:
            x,y,w,h=item['box'];cv2.rectangle(preview,(x,y),(x+w,y+h),(128,255,128),2)
            cv2.putText(preview,item['label'],(max(0,x),max(16,y-4)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(128,255,128),1)
        self.stream.update_frame(preview)
        self.frames+=1;self.last_frame=timestamp
        self.processing_ms=(time.perf_counter()-before)*1000
        return detected

    def _run(self):
        while not self.stop_event.is_set():
            started=time.monotonic()
            try:
                data=self.camera_manager.get_frame(self.camera_id)
                if data is not None: self.process(data[0],data[1])
            except Exception:
                self.errors+=1;logger.exception('Camera processing failed: %s',self.camera_id)
            self.stop_event.wait(max(0.005,1/self.profile.fps-(time.monotonic()-started)))
        self.finalize()

    def start(self):
        if self.worker and self.worker.is_alive(): return
        self.worker=threading.Thread(target=self._run,name=f'sentinel-{self.camera_id}',daemon=True)
        self.worker.start()

    def finalize(self):
        self.events.on_motion_ended()
        self.recorder._stop_recording()

    def stop(self):
        self.stop_event.set()
        if self.worker: self.worker.join(timeout=3)
        else: self.finalize()

    def status(self):
        health=getattr(self.camera_manager,'camera_health',{})
        health=health.get(self.camera_id,{}) if isinstance(health,dict) else {}
        return {'camera_id':self.db_id,'driver_id':self.camera_id,'name':self.profile.name,
            'frames':self.frames,'errors':self.errors+health.get('error_count',0),'connected':bool(health.get('connected',False)),
            'last_frame':self.last_frame.isoformat() if self.last_frame else None,
            'frame_age_seconds':round((datetime.utcnow()-self.last_frame).total_seconds(),1) if self.last_frame else None,
            'processing_ms':round(self.processing_ms,2),'observed_fps':round(self.frames/max(1,time.monotonic()-self.started),2),
            'target_fps':self.profile.fps,'scheduled':self.scheduled,'recording':self.recorder.is_recording,
            'worker_alive':bool(self.worker and self.worker.is_alive()),'objects':self.object_results,
            'object_detector':self.objects.status() if self.objects else {'ready':False,'backend':'disabled'}}
