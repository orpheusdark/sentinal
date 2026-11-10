"""Regression tests for security, persistence, encoding, storage and packaging."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import os

import numpy as np
import pytest

from config.settings import ConfigManager, get_config
from database.models import get_database, Recording
from web.server import WebServer


def server_with_database():
    server = WebServer()
    server.set_app_context(SimpleNamespace(db=get_database()))
    return server


def add_recording(path, **kwargs):
    with get_database().get_session() as session:
        row = Recording(camera_id=1, filename=Path(path).name, filepath=str(path),
                        start_time=datetime.utcnow(), **kwargs)
        session.add(row)
        session.commit()
        return row.id


@pytest.mark.parametrize(('name', 'value', 'section', 'field', 'expected'), [
    ('SENTINEL_CAMERA_FPS', '20', 'camera', 'fps', 20),
    ('SENTINEL_MOTION_MIN_CONTOUR_AREA', '700', 'motion', 'min_contour_area', 700),
    ('SENTINEL_SECURITY_ADMIN_PASSWORD', 'a-private-test-password', 'security', 'admin_password', 'a-private-test-password'),
    ('SENTINEL_WEB_USE_HTTPS', 'true', 'web', 'use_https', True),
    ('SENTINEL_SECURITY_ADMIN_PASSWORD', '1234567890', 'security', 'admin_password', '1234567890'),
])
def test_environment_fields_with_underscores(monkeypatch, tmp_path, name, value, section, field, expected):
    monkeypatch.setenv(name, value)
    config = ConfigManager(str(tmp_path / 'missing.json')).config
    assert getattr(getattr(config, section), field) == expected


def test_invalid_file_does_not_silently_use_defaults(tmp_path):
    path = tmp_path / 'invalid.json'
    path.write_text('not json')
    with pytest.raises(ValueError):
        ConfigManager(path)


def test_new_database_and_health():
    assert get_database().health_check()
    assert {'cameras', 'recordings', 'motion_events'} <= set(__import__('sqlalchemy').inspect(get_database().engine).get_table_names())


def test_login_rejects_external_redirect_and_protects_system_info():
    cfg = get_config()
    cfg.security.enable_auth = True
    cfg.security.admin_password = 'test-only-private-password'
    server = WebServer()
    client = server.app.test_client()
    assert client.get('/api/system/info').status_code == 401
    response = client.post('/login', data={'username': 'admin', 'password': cfg.security.admin_password, 'next': '//evil.example'})
    assert response.status_code == 302 and response.location == '/'
    assert client.get('/api/config').status_code == 200
    assert 'HttpOnly' in response.headers['Set-Cookie']


def test_unicode_password_and_secret_is_unique():
    cfg = get_config(); cfg.security.admin_password = 'private-你好'
    from config.settings import SecurityConfig
    first = WebServer()
    assert first._verify_credentials('admin', 'private-你好')
    assert SecurityConfig().session_secret != SecurityConfig().session_secret


def test_api_key_covers_reads_and_cannot_use_query_string():
    cfg = get_config(); cfg.security.require_api_key = True; cfg.security.api_key = 'test-api-key'
    client = WebServer().app.test_client()
    assert client.get('/api/config').status_code == 401
    assert client.get('/api/config?api_key=test-api-key').status_code == 401
    assert client.get('/api/config', headers={'X-API-Key': 'test-api-key'}).status_code == 200
    assert client.get('/api/health').status_code == 200


def test_cross_origin_write_and_missing_custom_header():
    client = WebServer().app.test_client()
    assert client.put('/api/config', json={'camera': {'fps': 20}}, headers={'Origin': 'https://evil.example', 'X-Sentinel-Request': 'dashboard'}).status_code == 403
    assert client.put('/api/config', json={'camera': {'fps': 20}}).status_code == 403


@pytest.mark.parametrize('patch', [
    {'camera': {'fps': 0}}, {'camera': {'fps': True}},
    {'motion': {'sensitivity': 101}}, {'security': {'enable_auth': False}},
    {'recording': {'enabled': 'yes'}}, {'storage': {'retention_days': 0}},
    {'recording': {'quality': 'invalid'}}, {'storage': {'critical_disk_percent': 50}},
])
def test_settings_reject_invalid_patch(patch):
    client = WebServer().app.test_client()
    response = client.put('/api/config', json=patch, headers={'X-Sentinel-Request': 'dashboard'})
    assert response.status_code == 400


def test_settings_persist_without_environment_secret(monkeypatch):
    from config import settings
    settings._config_manager.config.security.admin_password = 'never-save-this-secret'
    response = WebServer().app.test_client().put('/api/config', json={'camera': {'fps': 25}}, headers={'X-Sentinel-Request': 'dashboard'})
    assert response.status_code == 200 and response.json['restart_required']
    content = settings._config_manager.config_file.read_text()
    assert json.loads(content)['camera']['fps'] == 25
    assert 'never-save-this-secret' not in content


def test_recordings_list_download_bounds_and_missing_files(tmp_path):
    base = tmp_path / 'recordings'; base.mkdir()
    path = base / 'test.mp4'; path.write_bytes(b'video-test')
    get_config().storage.recordings_dir = str(base)
    row_id = add_recording(path)
    client = server_with_database().app.test_client()
    response = client.get('/api/recordings?limit=1')
    assert response.status_code == 200 and response.json['data']['total'] == 1
    download = client.get(f'/api/recordings/{row_id}/download')
    assert download.status_code == 200 and download.data == b'video-test'
    download.close()
    assert client.get('/api/recordings?limit=1&offset=1').json['data']['count'] == 0
    outside = tmp_path / 'private.txt'; outside.write_text('private')
    row_id = add_recording(outside)
    assert client.get(f'/api/recordings/{row_id}/download').status_code == 403
    path.unlink()
    assert client.get('/api/recordings/1/download').status_code == 404


def test_finalized_recording_persists_once_and_motion_resets_tail(tmp_path):
    from recording.manager import RecordingManager
    manager = RecordingManager()
    manager.current_camera_id = 1
    manager.current_video_path = str(tmp_path / 'video.mp4')
    Path(manager.current_video_path).write_bytes(b'finalized')
    manager.recording_start_time = datetime.utcnow()
    manager.recorder = Mock(frames_written=30, fps=15)
    manager.recorder.stop_recording.return_value = True
    manager.is_recording = True
    manager.post_motion_buffer_end = datetime.utcnow() - timedelta(seconds=1)
    manager.on_motion_detected(1, datetime.utcnow())
    assert manager.post_motion_buffer_end is None
    manager._stop_recording(); manager._stop_recording()
    with get_database().get_session() as session:
        assert session.query(Recording).count() == 1
        assert session.query(Recording).first().duration_seconds == 2


def test_recording_disabled_does_not_start():
    from recording.manager import RecordingManager
    get_config().recording.enabled = False
    manager = RecordingManager(); manager._start_recording = Mock()
    manager.on_motion_detected(1, datetime.utcnow())
    manager._start_recording.assert_not_called()


def test_jpeg_cached_and_frame_ownership(monkeypatch):
    import web.stream as stream
    manager = stream.StreamManager()
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    manager.update_frame(frame)
    frame[:] = 255
    assert manager.current_frame.max() == 0
    encode = Mock(wraps=stream.cv2.imencode); monkeypatch.setattr(stream.cv2, 'imencode', encode)
    manager.get_frame_as_jpeg(); manager.get_frame_as_jpeg()
    assert encode.call_count == 1
    manager.set_quality(50); manager.get_frame_as_jpeg()
    assert encode.call_count == 2


def test_retention_only_removes_old_video(tmp_path):
    from storage.manager import StorageManager
    get_config().storage.recordings_dir = str(tmp_path / 'archive')
    manager = StorageManager()
    old = manager.recordings_path / 'old.mp4'; old.write_bytes(b'old')
    other = manager.recordings_path / 'keep.txt'; other.write_text('keep')
    stamp = (datetime.utcnow() - timedelta(days=40)).timestamp(); os.utime(old, (stamp, stamp))
    result = manager.enforce_retention_policy()
    assert result['deleted_count'] == 1 and result['error'] is None
    assert other.exists()


def test_desktop_data_outside_install(tmp_path):
    from desktop import prepare_runtime
    target = tmp_path / 'user-data'
    config = prepare_runtime(target)
    assert config.is_file() and Path.cwd() == target
    config.write_text('{"custom": true}')
    assert prepare_runtime(target).read_text() == '{"custom": true}'


def test_loopback_rejects_untrusted_hosts():
    assert WebServer().app.test_client().get('/api/config', headers={'Host': 'evil.example'}).status_code == 400


def test_grouped_analytics():
    add_recording('example.mp4', file_size_bytes=1024)
    response = server_with_database().app.test_client().get('/api/analytics')
    assert response.status_code == 200
    data = response.json['data']
    assert data['totals']['recording_count'] == 1
    assert data['cameras'][0]['recording_count'] == 1


def test_retention_preserves_active_recording(tmp_path):
    from storage.manager import StorageManager
    get_config().storage.recordings_dir = str(tmp_path / 'archive')
    manager = StorageManager()
    path = manager.recordings_path / 'active.mp4'; path.write_bytes(b'active')
    stamp = (datetime.utcnow() - timedelta(days=40)).timestamp(); os.utime(path, (stamp, stamp))
    manager.active_recording_path = lambda: str(path)
    assert manager.enforce_retention_policy()['deleted_count'] == 0
    assert path.exists()


def test_synthetic_video_round_trip(tmp_path, monkeypatch):
    import cv2
    from recording.manager import RecordingManager
    get_config().storage.recordings_dir = str(tmp_path / 'recordings')
    manager = RecordingManager()
    monkeypatch.setattr(manager, '_get_camera_resolution', lambda config: (64, 48))
    manager.on_motion_detected(1, datetime.utcnow())
    assert manager.is_recording
    for index in range(8):
        result = manager.write_frame(np.full((48, 64, 3), index * 20, dtype=np.uint8), datetime.utcnow(), 1)
        assert result.success
    manager._stop_recording()
    capture = cv2.VideoCapture(manager.current_video_path)
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 8
        assert capture.read()[0]
    finally:
        capture.release()
    with get_database().get_session() as session:
        row = session.query(Recording).one()
        assert row.file_size_bytes > 0 and row.duration_seconds > 0


def test_application_degraded_startup_and_shutdown(tmp_path, monkeypatch):
    from app import Application
    monkeypatch.setattr(WebServer, 'start', Mock())
    monkeypatch.setattr(Application, '_initialize_signal_handlers', Mock())
    path = tmp_path / 'app-settings.json'
    path.write_text('{"camera":{"enabled":false}}')
    application = Application(config_file=str(path))
    try:
        assert application.initialize()
        assert application.context.db.health_check()
        assert application.context.camera_manager.cameras == {}
        assert application.context.web_server is not None
    finally:
        application.shutdown()


@pytest.mark.skipif(os.name != 'nt', reason='Windows installer only')
def test_windows_installer_preserves_existing_data(tmp_path, monkeypatch):
    import zipfile
    import scripts.windows_setup as setup
    import sys
    bundle = tmp_path / 'bundle'; bundle.mkdir()
    with zipfile.ZipFile(bundle / 'sentinel-payload.zip', 'w') as archive:
        archive.writestr('Sentinel.exe', b'test-executable')
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle), raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'roaming'))
    monkeypatch.setattr(setup.subprocess, 'run', Mock())
    data = tmp_path / 'local' / 'Sentinel'; data.mkdir(parents=True)
    config = data / 'settings.json'; config.write_text('keep')
    exe = setup.install()
    assert exe.read_bytes() == b'test-executable'
    assert config.read_text() == 'keep'
