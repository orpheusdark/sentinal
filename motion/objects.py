"""Optional local people detection, or COCO YOLO ONNX people/vehicle detection."""
from pathlib import Path
import time
import cv2
import numpy as np


class ObjectDetector:
    LABELS={0:'person',1:'bicycle',2:'car',3:'motorcycle',5:'bus',7:'truck'}

    def __init__(self, config):
        self.config=config
        self.last_run=-float('inf')
        self.cached=[]
        self.error=None
        self.net=None
        self.hog=None
        self.backend='built-in people detector'
        if config.object_model_path:
            self.backend='local ONNX people/vehicle detector'
            path=Path(config.object_model_path).resolve()
            if not path.is_relative_to(Path('models').resolve()) or path.suffix.lower()!='.onnx' or not path.is_file():
                self.error='Place a compatible COCO ONNX model inside the models directory'
                return
            try: self.net=cv2.dnn.readNetFromONNX(str(path))
            except cv2.error: self.error='Unable to load the configured ONNX model'
        else:
            self.hog=cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame, now=None):
        now=time.monotonic() if now is None else now
        if now-self.last_run < self.config.object_min_interval:
            return self.cached
        self.last_run=now
        if self.error:
            return []
        try:
            if self.net is None:
                height,width=frame.shape[:2]; scale=min(1,640/width)
                small=cv2.resize(frame,(max(64,int(width*scale)),max(128,int(height*scale))))
                boxes,weights=self.hog.detectMultiScale(small,winStride=(8,8),padding=(8,8),scale=1.05)
                self.cached=[{'label':'person','confidence':round(float(score),3),
                              'box':[int(x/scale),int(y/scale),int(w/scale),int(h/scale)]}
                             for (x,y,w,h),score in zip(boxes,weights) if float(score)>=self.config.object_confidence]
            else:
                self.cached=self._onnx(frame)
        except (cv2.error,ValueError,IndexError):
            self.error='Detection failed; verify the local model format and diagnostics'
            self.cached=[]
        return self.cached

    def _onnx(self, frame):
        height,width=frame.shape[:2]
        side=max(height,width)
        square=np.zeros((side,side,3),np.uint8);square[:height,:width]=frame
        self.net.setInput(cv2.dnn.blobFromImage(square,1/255,(640,640),swapRB=True,crop=False))
        output=np.asarray(self.net.forward()).squeeze()
        if output.ndim!=2: raise ValueError('Unsupported output')
        if output.shape[0] in (84,85): output=output.T
        if output.shape[1] not in (84,85): raise ValueError('Use a COCO YOLO detection model')
        boxes=[];scores=[];labels=[]
        for row in output:
            class_scores=row[5:] * row[4] if len(row)==85 else row[4:]
            category=int(np.argmax(class_scores));confidence=float(class_scores[category])
            if category not in self.LABELS or confidence<self.config.object_confidence: continue
            cx,cy,w,h=row[:4]*side/640
            boxes.append([int(cx-w/2),int(cy-h/2),int(w),int(h)])
            scores.append(confidence);labels.append(self.LABELS[category])
        keep=cv2.dnn.NMSBoxes(boxes,scores,self.config.object_confidence,0.45)
        return [{'label':labels[int(i)],'confidence':round(scores[int(i)],3),'box':boxes[int(i)]}
                for i in np.asarray(keep).reshape(-1)]

    def status(self):
        return {'backend':self.backend,'ready':not self.error,'error':self.error,
                'minimum_interval_seconds':self.config.object_min_interval}
