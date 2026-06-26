"""
Recording Module Tests

Tests for MP4RecorderDriver, RecordingManager, and StorageManager
"""

import pytest
import tempfile
import os
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from recording.result import RecordingResult
from recording.drivers.mp4 import MP4RecorderDriver
from recording.manager import RecordingManager
from storage.manager import StorageManager
from config.settings import ConfigManager, RecordingConfig, StorageConfig


class TestRecordingResult:
    """Test RecordingResult dataclass."""
    
    def test_result_initialization(self):
        """Test result creation and defaults."""
        result = RecordingResult()
        assert result.success is False
        assert result.timestamp is not None
        assert result.error_message is None
        assert result.frames_written == 0
    
    def test_result_to_dict(self):
        """Test serialization to dictionary."""
        result = RecordingResult(
            success=True,
            video_path="/path/to/video.mp4",
            frames_written=100,
            write_time_ms=10.5
        )
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['video_path'] == "/path/to/video.mp4"
        assert result_dict['frames_written'] == 100
        assert result_dict['write_time_ms'] == 10.5


class TestMP4RecorderDriver:
    """Test MP4RecorderDriver."""
    
    def test_driver_initialization(self):
        """Test driver creation."""
        driver = MP4RecorderDriver(quality='medium')
        assert driver.quality == 'medium'
        assert driver.is_recording() is False
    
    def test_quality_presets(self):
        """Test quality preset values."""
        assert MP4RecorderDriver.QUALITY_PRESETS['low'] == 1000
        assert MP4RecorderDriver.QUALITY_PRESETS['medium'] == 2500
        assert MP4RecorderDriver.QUALITY_PRESETS['high'] == 5000
    
    def test_invalid_quality_defaults_to_medium(self):
        """Test that invalid quality defaults to medium."""
        driver = MP4RecorderDriver(quality='invalid')
        assert driver.quality == 'medium'
        assert driver.bitrate == 2500
    
    def test_recording_info_when_not_recording(self):
        """Test getting recording info when no recording active."""
        driver = MP4RecorderDriver()
        info = driver.get_recording_info()
        
        assert info['is_recording'] is False
        assert info['frames_written'] == 0
        assert info['video_path'] is None
    
    def test_start_recording_with_valid_path(self):
        """Test starting a recording with valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, 'test_video.mp4')
            driver = MP4RecorderDriver()
            
            result = driver.start_recording(video_path, fps=15, resolution=(1280, 720))
            assert result is True
            assert driver.is_recording() is True
            assert driver.video_path == video_path
            
            # Cleanup
            driver.stop_recording()
    
    def test_write_frame_when_not_recording(self):
        """Test writing frame when recording not active."""
        driver = MP4RecorderDriver()
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        result = driver.write_frame(frame)
        assert result.success is False
        assert "not started" in result.error_message.lower()
    
    def test_recording_stops_correctly(self):
        """Test stopping a recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, 'test_video.mp4')
            driver = MP4RecorderDriver()
            
            # Start recording
            driver.start_recording(video_path, fps=15, resolution=(1280, 720))
            assert driver.is_recording() is True
            
            # Stop recording
            result = driver.stop_recording()
            assert result is True
            assert driver.is_recording() is False


class TestRecordingManager:
    """Test RecordingManager."""
    
    def test_manager_initialization(self):
        """Test manager creation."""
        config = RecordingConfig(
            enabled=True,
            quality='medium',
            post_motion_seconds=5
        )
        manager = RecordingManager(config)
        
        assert manager.is_recording is False
        assert manager.motion_active is False
    
    def test_motion_detection_triggers_recording(self):
        """Test that motion detection starts recording."""
        config = RecordingConfig(
            enabled=True,
            quality='medium',
            post_motion_seconds=5
        )
        manager = RecordingManager(config)
        
        # Mock recording start
        now = datetime.utcnow()
        manager.on_motion_detected(camera_id=1, motion_start_time=now)
        
        assert manager.motion_active is True
        assert manager.motion_start_time == now
    
    def test_motion_ending_starts_post_buffer(self):
        """Test that motion ending starts post-motion buffer."""
        config = RecordingConfig(
            enabled=True,
            quality='medium',
            post_motion_seconds=5
        )
        manager = RecordingManager(config)
        
        # Start motion
        start_time = datetime.utcnow()
        manager.on_motion_detected(camera_id=1, motion_start_time=start_time)
        
        # End motion
        end_time = datetime.utcnow()
        manager.on_motion_ended(end_time)
        
        assert manager.motion_active is False
        assert manager.motion_end_time == end_time
        assert manager.post_motion_buffer_end is not None
        assert (manager.post_motion_buffer_end - end_time).total_seconds() >= 4.9
    
    def test_get_status_returns_dict(self):
        """Test getting manager status."""
        config = RecordingConfig(
            enabled=True,
            quality='medium',
            post_motion_seconds=5
        )
        manager = RecordingManager(config)
        
        status = manager.get_status()
        assert isinstance(status, dict)
        assert 'is_recording' in status
        assert 'motion_active' in status
        assert 'current_video_path' in status


class TestStorageManager:
    """Test StorageManager."""
    
    def test_manager_initialization(self):
        """Test manager creation."""
        config = StorageConfig(
            retention_days=30,
            warning_disk_percent=80,
            critical_disk_percent=95,
            target_free_percent=60
        )
        manager = StorageManager(config)
        
        assert manager.retention_days == 30
        assert manager.warning_disk_percent == 80
        assert manager.critical_disk_percent == 95
    
    def test_check_disk_health(self):
        """Test disk health check."""
        config = StorageConfig(
            retention_days=30,
            warning_disk_percent=80,
            critical_disk_percent=95,
            target_free_percent=60
        )
        manager = StorageManager(config)
        
        health = manager.check_disk_health()
        assert 'total_bytes' in health
        assert 'used_bytes' in health
        assert 'free_bytes' in health
        assert 'used_percent' in health
        assert 'status' in health
        assert health['status'] in ['healthy', 'warning', 'critical']
    
    def test_retention_policy_returns_dict(self):
        """Test retention policy returns results."""
        config = StorageConfig(
            retention_days=30,
            warning_disk_percent=80,
            critical_disk_percent=95,
            target_free_percent=60
        )
        manager = StorageManager(config)
        
        result = manager.enforce_retention_policy()
        assert isinstance(result, dict)
        assert 'deleted_count' in result
        assert 'freed_bytes' in result
    
    def test_get_storage_info(self):
        """Test getting storage information."""
        config = StorageConfig(
            retention_days=30,
            warning_disk_percent=80,
            critical_disk_percent=95,
            target_free_percent=60
        )
        manager = StorageManager(config)
        
        info = manager.get_storage_info()
        assert isinstance(info, dict)
        assert 'total_recordings_bytes' in info
        assert 'recording_count' in info
        assert 'retention_days' in info


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
