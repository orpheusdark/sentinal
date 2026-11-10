from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
from config.settings import get_config
from recording.manager import RecordingManager
from database.models import get_database,Recording


def test_continuous_video_rotates_and_finalizes_each_segment(tmp_path):
    config=get_config();config.storage.recordings_dir=str(tmp_path/'videos')
    config.recording.record_on_motion=False;config.recording.max_duration_seconds=1
    manager=RecordingManager();manager.capture_resolution=(64,48)
    frame=np.zeros((48,64,3),np.uint8)
    now=datetime.utcnow()
    manager.write_frame(frame,now,1)
    first=manager.current_video_path
    manager.write_frame(frame,now+timedelta(seconds=2),1)
    assert manager.is_recording and manager.current_video_path!=first
    manager._stop_recording()
    with get_database().get_session() as session:
        recordings=session.query(Recording).all()
        assert len(recordings)==2
        assert all(Path(row.filepath).is_file() and row.end_time for row in recordings)
