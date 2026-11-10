"""Motion zones and host-local weekly schedules."""
from datetime import datetime, timedelta
import cv2
import numpy as np


def is_scheduled(schedule, now=None):
    if not schedule:
        return True
    now=now or datetime.now().astimezone()
    minute=now.hour*60+now.minute
    for rule in schedule:
        start=sum(int(v)*m for v,m in zip(rule['start'].split(':'),(60,1)))
        end=sum(int(v)*m for v,m in zip(rule['end'].split(':'),(60,1)))
        if start<end and now.weekday() in rule['days'] and start<=minute<end:
            return True
        if start>end and ((now.weekday() in rule['days'] and minute>=start) or
                          ((now-timedelta(days=1)).weekday() in rule['days'] and minute<end)):
            return True
    return False


def zone_mask(shape, zones):
    height,width=shape[:2]
    mask=np.zeros((height,width),np.uint8)
    for x,y,w,h in zones:
        left,top=int(x*width),int(y*height)
        right,bottom=min(width,int((x+w)*width)),min(height,int((y+h)*height))
        mask[top:bottom,left:right]=255
    return mask
