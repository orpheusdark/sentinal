"""Validated per-device capture, motion and recording preferences."""
from dataclasses import dataclass, field, asdict
from datetime import time
import math


@dataclass
class CameraProfile:
    index: int = 0
    name: str = 'Camera 1'
    enabled: bool = True
    fps: int = 15
    resolution: str = '720p'
    motion_enabled: bool = True
    sensitivity: int = 30
    min_contour_area: int = 300
    recording_enabled: bool = True
    record_on_motion: bool = True
    post_motion_seconds: int = 10
    max_duration_seconds: int = 300
    zones: list = field(default_factory=list)
    schedule: list = field(default_factory=list)
    object_detection_enabled: bool = False

    def validate(self):
        for name in ('enabled', 'motion_enabled', 'recording_enabled', 'record_on_motion', 'object_detection_enabled'):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f'{name} must be a boolean')
        for name, low, high in [('index',0,15),('fps',1,60),('sensitivity',0,100),('min_contour_area',1,10000000),('post_motion_seconds',0,300),('max_duration_seconds',1,3600)]:
            value=getattr(self,name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{name} must be an integer between {low} and {high}')
        if not isinstance(self.name,str) or not self.name.strip() or len(self.name)>80:
            raise ValueError('Camera name must contain 1–80 characters')
        if self.resolution not in ('360p','480p','720p','1080p'):
            raise ValueError('Unsupported camera resolution')
        validate_policy(self.zones,self.schedule)
        return self


def validate_policy(zones, schedule):
    if not isinstance(zones,list) or len(zones)>12:
        raise ValueError('Use up to 12 motion zones')
    for zone in zones:
        if not isinstance(zone,list) or len(zone)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in zone):
            raise ValueError('Zones must be normalized [x,y,width,height] rectangles')
        x,y,w,h=zone
        if min(x,y)<0 or min(w,h)<=0 or x+w>1.000001 or y+h>1.000001:
            raise ValueError('Motion zones must stay inside the image')
    if not isinstance(schedule,list) or len(schedule)>28:
        raise ValueError('Use up to 28 schedule windows')
    for rule in schedule:
        if not isinstance(rule,dict) or set(rule)!={'days','start','end'}:
            raise ValueError('Schedule windows require days, start and end')
        if not isinstance(rule['days'],list) or not rule['days'] or any(type(d) is not int or not 0<=d<=6 for d in rule['days']):
            raise ValueError('Schedule days use Monday=0 through Sunday=6')
        for key in ('start','end'):
            value=rule[key]
            if not isinstance(value,str) or len(value)!=5 or value[2]!=':':
                raise ValueError('Schedule times must use HH:MM')
            try: time.fromisoformat(value)
            except ValueError as error: raise ValueError('Invalid schedule time') from error
        if rule['start']==rule['end']:
            raise ValueError('Schedule start and end must differ')


def profiles_from_config(config):
    if not config.camera.enabled and not config.camera.sources:
        return []
    if config.camera.sources:
        return [CameraProfile(**source).validate() for source in config.camera.sources]
    return [CameraProfile(index=0,name='builtin',fps=config.camera.fps,resolution=config.camera.resolution,
        motion_enabled=config.motion.enabled,sensitivity=config.motion.sensitivity,
        min_contour_area=config.motion.min_contour_area,recording_enabled=config.recording.enabled,
        record_on_motion=config.recording.record_on_motion,post_motion_seconds=config.recording.post_motion_seconds,
        max_duration_seconds=config.recording.max_duration_seconds,
        zones=config.motion.zones,schedule=config.motion.schedule,object_detection_enabled=config.motion.object_detection_enabled)]


def validate_profiles(sources):
    if not isinstance(sources,list) or len(sources)>8:
        raise ValueError('Configure up to eight cameras')
    try: profiles=[CameraProfile(**source).validate() for source in sources]
    except TypeError as error: raise ValueError('Unsupported camera profile field') from error
    if len({p.index for p in profiles})!=len(profiles) or len({p.name for p in profiles})!=len(profiles):
        raise ValueError('Camera indices and names must be unique')
    return [asdict(profile) for profile in profiles]
