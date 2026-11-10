"""Bounded local-file decoders for codec-independent, seekable JPEG playback."""
from collections import OrderedDict
import threading
import time
import cv2


class Playback:
    def __init__(self, capacity=4):
        self.capacity=capacity
        self.lock=threading.RLock()
        self.captures=OrderedDict()

    def _get(self, path):
        now=time.monotonic()
        for key, entry in list(self.captures.items()):
            if now-entry['used']>120:
                entry['capture'].release();del self.captures[key]
        key=str(path)
        if key not in self.captures:
            while len(self.captures)>=self.capacity:
                _, entry=self.captures.popitem(last=False);entry['capture'].release()
            capture=cv2.VideoCapture(key)
            if not capture.isOpened():
                capture.release();raise ValueError('Video cannot be decoded')
            self.captures[key]={'capture':capture,'used':now}
        self.captures.move_to_end(key)
        self.captures[key]['used']=now
        return self.captures[key]['capture']

    def metadata(self, path):
        with self.lock:
            cap=self._get(path)
            fps=cap.get(cv2.CAP_PROP_FPS) or 15
            frames=cap.get(cv2.CAP_PROP_FRAME_COUNT)
            return {'fps':fps,'frames':int(frames),'duration':max(0,frames/fps),
                    'width':int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),'height':int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'preview_fps':5,'has_audio':False}

    def frame(self, path, seconds=0, width=960):
        with self.lock:
            cap=self._get(path)
            fps=cap.get(cv2.CAP_PROP_FPS) or 15
            count=max(1,int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            position=min(count-1,max(0,int(seconds*fps)))
            current=int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current!=position: cap.set(cv2.CAP_PROP_POS_FRAMES,position)
            ok, frame=cap.read()
            if not ok: raise ValueError('Video frame is unavailable')
            height,original_width=frame.shape[:2]
            if original_width>width:
                frame=cv2.resize(frame,(width,max(1,round(height*width/original_width))))
            ok,data=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,80])
            if not ok: raise ValueError('Unable to encode playback preview')
            return data.tobytes()

    def close(self):
        with self.lock:
            for entry in self.captures.values(): entry['capture'].release()
            self.captures.clear()
