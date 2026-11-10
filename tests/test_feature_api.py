from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import cv2
import numpy as np
import pytest
from config.settings import get_config
from database.models import get_database, Recording, MotionEvent
from web.server import WebServer

HEADERS={'X-Sentinel-Request':'dashboard'}


def app_with_db():
    server=WebServer()
    server.set_app_context(SimpleNamespace(db=get_database(),pipelines={}))
    return server


def synthetic_recording(tmp_path):
    root=tmp_path/'recordings';root.mkdir()
    get_config().storage.recordings_dir=str(root)
    path=root/'review.mp4'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),10,(64,48))
    assert writer.isOpened()
    for index in range(10): writer.write(np.full((48,64,3),index*20,np.uint8))
    writer.release()
    with get_database().get_session() as session:
        event=MotionEvent(camera_id=1,start_time=datetime.utcnow(),contour_count=1,max_contour_area=100,sensitivity_level=30)
        session.add(event);session.flush()
        row=Recording(camera_id=1,motion_event_id=event.id,filename=path.name,filepath=str(path),start_time=datetime.utcnow(),duration_seconds=1)
        session.add(row);session.commit();return row.id


def test_playback_metadata_seek_thumbnail_and_time_validation(tmp_path):
    row=synthetic_recording(tmp_path)
    server=app_with_db();client=server.app.test_client()
    try:
        result=client.get(f'/api/recordings/{row}/playback')
        assert result.status_code==200 and result.json['data']['frames']==10
        frame=client.get(f'/api/recordings/{row}/frame?time=0.5')
        assert frame.status_code==200 and frame.mimetype=='image/jpeg'
        assert "img-src 'self' data: blob:" in frame.headers['Content-Security-Policy']
        decoded=cv2.imdecode(np.frombuffer(frame.data,np.uint8),cv2.IMREAD_COLOR)
        assert decoded.shape[:2]==(48,64)
        assert decoded.mean()>70
        assert client.get(f'/api/recordings/{row}/thumbnail').mimetype=='image/jpeg'
        assert client.get(f'/api/recordings/{row}/frame?time=nan').status_code==400
        assert client.get(f'/api/recordings/{row}/frame?time=-1').status_code==400
    finally: server.playback.close()


def test_timeline_links_event_to_recording(tmp_path):
    row=synthetic_recording(tmp_path)
    result=app_with_db().app.test_client().get('/api/timeline?camera_id=1')
    assert result.status_code==200
    assert result.json['data']['events'][0]['recording_id']==row


def test_setup_validates_and_persists_per_camera_settings():
    server=app_with_db();client=server.app.test_client()
    assert client.get('/api/camera-setup').json['data']['max_cameras']==8
    profiles=[{'index':0,'name':'Entrance','fps':10,'zones':[[0.1,0.1,0.8,0.8]],
               'schedule':[{'days':[0,1,2,3,4],'start':'09:00','end':'17:00'}]}]
    result=client.put('/api/camera-setup',json={'profiles':profiles},headers=HEADERS)
    assert result.status_code==200 and result.json['restart_required']
    from config import settings
    saved=json.loads(settings._config_manager.config_file.read_text())
    assert saved['camera']['sources'][0]['name']=='Entrance'
    assert client.put('/api/camera-setup',json={'profiles':[{'index':99}]},headers=HEADERS).status_code==400


def test_camera_discovery_is_bounded_and_guarded():
    server=app_with_db()
    server.app_context.camera_manager=SimpleNamespace(discover=Mock(return_value=[{'index':2,'name':'USB'}]),camera_db_ids={})
    client=server.app.test_client()
    result=client.post('/api/camera-setup/discover',json={},headers=HEADERS)
    assert result.status_code==200 and result.json['data']['devices'][0]['index']==2
    server.scan_lock.acquire()
    try: assert client.post('/api/camera-setup/discover',json={},headers=HEADERS).status_code==409
    finally: server.scan_lock.release()


def test_diagnostics_do_not_expose_credentials_or_paths(tmp_path):
    cfg=get_config();cfg.security.admin_password='private-password-example';cfg.telegram.bot_token='private-token-example'
    server=app_with_db();result=server.app.test_client().get('/api/diagnostics')
    assert result.status_code==200
    text=result.get_data(as_text=True)
    assert 'private-password-example' not in text and 'private-token-example' not in text
    assert str(tmp_path) not in text
    assert result.json['data']['database_healthy']


def test_release_version_ordering():
    from web.updates import version_key
    assert version_key('v0.3.0-preview.2')>version_key('v0.3.0-preview.1')
    assert version_key('0.3.0rc1')==version_key('v0.3.0-preview.1')
    assert version_key('v0.3.0')>version_key('v0.3.0-preview.10')
    assert version_key('v0.2.0')<version_key('v0.3.0-preview.1')
    assert version_key('not-a-version') is None


def test_update_checker_sanitizes_external_release_urls(monkeypatch):
    import web.updates as updates
    from io import BytesIO
    data=[{'tag_name':'v0.4.0','html_url':'https://evil.example/download','draft':False}]
    monkeypatch.setattr(updates,'urlopen',lambda *a,**k:BytesIO(json.dumps(data).encode()))
    checker=updates.UpdateChecker('0.3.0-preview.1');checker._run()
    assert checker.status()['available']
    assert checker.status()['url']=='https://github.com/orpheusdark/sentinal/releases'


def test_feature_routes_require_authentication():
    cfg=get_config();cfg.security.enable_auth=True;cfg.security.admin_password='private-test-password'
    client=WebServer().app.test_client()
    for path in ['/api/diagnostics','/api/timeline','/api/camera-setup','/api/recordings/1/frame','/api/updates']:
        assert client.get(path).status_code==401


def test_new_pages_and_resources_render_without_camera_hardware():
    client=WebServer().app.test_client()
    for path in ['/cameras/setup','/diagnostics','/static/css/features.css','/static/js/camera_setup.js','/static/js/diagnostics.js']:
        assert client.get(path).status_code==200
