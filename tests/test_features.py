from datetime import datetime, timedelta
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import threading
import time
import numpy as np
import pytest
from config.settings import get_config, SentinelConfig, CameraConfig, MotionConfig
from config.profiles import CameraProfile, validate_profiles
from motion.policy import is_scheduled, zone_mask
from motion.result import MotionResult
from database.models import get_database, Camera, Recording, MotionEvent


@pytest.mark.parametrize('sources',[
    [{'index':0,'fps':0}], [{'index':0,'enabled':'true'}],
    [{'index':0,'zones':[[0.9,0,0.5,1]]}],
    [{'index':0,'schedule':[{'days':[7],'start':'09:00','end':'17:00'}]}],
    [{'index':0},{'index':0}], [{'index':0,'unknown':1}],
])
def test_profile_validation_rejects_invalid_configuration(sources):
    with pytest.raises(ValueError): validate_profiles(sources)


def test_overnight_schedule_and_boundaries():
    rules=[{'days':[0],'start':'22:00','end':'06:00'}]
    assert is_scheduled(rules,datetime(2026,11,9,22,0))
    assert is_scheduled(rules,datetime(2026,11,10,5,59))
    assert not is_scheduled(rules,datetime(2026,11,10,6,0))
    assert not is_scheduled(rules,datetime(2026,11,10,23,0))
    assert is_scheduled([],datetime(2026,11,10,23,0))


def test_motion_outside_zones_is_ignored():
    from motion.detector import MotionDetector
    cfg=MotionConfig(zones=[[0,0,0.5,1]],background_learning_frames=0,cooldown_seconds=0,min_contour_area=1,sensitivity=0)
    detector=MotionDetector(cfg)
    foreground=np.zeros((100,100),np.uint8);foreground[20:80,60:90]=255
    detector.bg_subtractor=Mock();detector.bg_subtractor.apply.return_value=foreground
    result=detector.process_frame(np.zeros((100,100,3),np.uint8))
    assert not result.motion_detected
    foreground[:]=0;foreground[20:80,10:40]=255
    assert detector.process_frame(np.zeros((100,100,3),np.uint8)).motion_detected


def test_alert_enqueue_never_waits_for_network_and_tracks_delivery():
    from alerts.queue import QueuedAlerts
    from alerts.telegram import TelegramAlertResult
    started=threading.Event();release=threading.Event()
    client=Mock();client.is_configured.return_value=True
    def send(**kwargs):
        started.set();release.wait(2);return TelegramAlertResult(True)
    client.send_motion_alert.side_effect=send
    alerts=QueuedAlerts(client,capacity=2,cooldown=0)
    try:
        assert alerts.send_motion_alert(camera_id=1).success
        assert started.wait(1)
        assert alerts.send_motion_alert(camera_id=2).success
        assert alerts.status()['accepted']==2
        assert alerts.status()['sent']==0
    finally:
        release.set();alerts.close(timeout=2)
    assert alerts.status()['sent']==2


def test_alert_queue_is_bounded():
    from alerts.queue import QueuedAlerts
    client=Mock();client.is_configured.return_value=True
    gate=threading.Event();started=threading.Event()
    def send(**kwargs): started.set();gate.wait(2);return SimpleNamespace(success=True)
    client.send_motion_alert.side_effect=send
    alerts=QueuedAlerts(client,capacity=1,cooldown=0)
    try:
        alerts.send_motion_alert(camera_id=1);assert started.wait(1)
        assert alerts.send_motion_alert(camera_id=2).success
        assert not alerts.send_motion_alert(camera_id=3).success
        assert alerts.status()['dropped']==1
    finally:
        gate.set();alerts.close(timeout=2)


def test_reconciliation_and_retention_remove_companions(tmp_path):
    from storage.manager import StorageManager
    import os
    cfg=get_config();cfg.storage.recordings_dir=str(tmp_path/'archive')
    storage=StorageManager()
    video=storage.recordings_path/'old.mp4';video.write_bytes(b'video')
    thumbnail=video.with_suffix('.jpg');thumbnail.write_bytes(b'image')
    browser=video.with_name('old.web.mp4');browser.write_bytes(b'playback')
    with get_database().get_session() as session:
        session.add(Recording(camera_id=1,filename=video.name,filepath=str(video),start_time=datetime.utcnow(),has_thumbnail=True,thumbnail_path=str(thumbnail)))
        session.commit()
    stamp=(datetime.utcnow()-timedelta(days=40)).timestamp();os.utime(video,(stamp,stamp))
    result=storage.enforce_retention_policy()
    assert result['deleted_count']==1
    assert not thumbnail.exists() and not browser.exists()
    with get_database().get_session() as session:
        assert session.query(Recording).one().deleted_at is not None


def test_per_camera_pipelines_have_independent_events_recordings_and_thumbnails(tmp_path):
    from camera.pipeline import CameraPipeline
    cfg=get_config();cfg.storage.recordings_dir=str(tmp_path/'videos')
    with get_database().get_session() as session:
        second=Camera(name='Second',camera_type='builtin');session.add(second);session.commit();second_id=second.id
    left=CameraPipeline('builtin_0',1,CameraProfile(name='Left'),cfg,Mock(),None)
    right=CameraPipeline('builtin_1',second_id,CameraProfile(index=1,name='Right'),cfg,Mock(),None)
    frame=np.zeros((48,64,3),np.uint8)
    def motion(active): return MotionResult(motion_detected=active,contour_count=1,max_contour_area=1000)
    left.detector.process_frame=Mock(return_value=motion(True))
    right.detector.process_frame=Mock(return_value=motion(False))
    try:
        assert left.process(frame)
        assert not right.process(frame)
        assert left.recorder.is_recording and not right.recorder.is_recording
        right.detector.process_frame.return_value=motion(True)
        assert right.process(frame)
        assert left.events.current_event_id != right.events.current_event_id
    finally:
        left.stop();right.stop()
    with get_database().get_session() as session:
        recordings=session.query(Recording).all()
        assert {r.camera_id for r in recordings}=={1,second_id}
        assert all(r.has_thumbnail and Path(r.thumbnail_path).is_file() for r in recordings)
        assert all(r.motion_event_id is not None for r in recordings)
        assert all(e.end_time for e in session.query(MotionEvent).all())


def test_onnx_person_and_vehicle_output_without_model_download():
    from motion.objects import ObjectDetector
    detector=ObjectDetector(MotionConfig())
    detector.net=Mock()
    output=np.zeros((1,84,2),np.float32)
    output[0,:4,0]=[100,100,50,50];output[0,4,0]=0.95
    output[0,:4,1]=[400,400,50,50];output[0,6,1]=0.9
    detector.net.forward.return_value=output
    results=detector.detect(np.zeros((640,640,3),np.uint8),now=10)
    assert {item['label'] for item in results}=={'person','car'}
    detector.detect(np.zeros((640,640,3),np.uint8),now=10.2)
    assert detector.net.forward.call_count==1


def test_global_recording_switch_disables_every_profile(tmp_path):
    from camera.pipeline import CameraPipeline
    cfg=get_config();cfg.recording.enabled=False
    pipeline=CameraPipeline('builtin_0',1,CameraProfile(recording_enabled=True),cfg,Mock(),None)
    assert not pipeline.recorder.config.enabled
    pipeline.stop()
