"""
Storage Manager

Responsibility: Monitor disk usage and manage recording storage cleanup.
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional
import threading

from config.settings import get_config
from utils.logger import get_logger
from utils.system import PathManager, SystemInfo, TimeUtils


logger = get_logger(__name__)


class StorageManager:
    """
    Manages video recording storage.
    
    Features:
    - Monitor disk usage
    - Enforce retention policy (days)
    - Emergency cleanup when disk full
    - Organized file structure
    - Thread-safe operations
    """
    
    def __init__(self, config=None):
        """
        Initialize storage manager.
        
        Args:
            config: StorageConfig from settings
        """
        self.config = config or get_config().storage
        self.lock = threading.RLock()
        
        # Retention policy (days)
        self.retention_days = self.config.retention_days if hasattr(self.config, 'retention_days') else 30
        
        # Disk thresholds
        self.critical_disk_percent = self.config.critical_disk_percent if hasattr(self.config, 'critical_disk_percent') else 95
        self.warning_disk_percent = self.config.warning_disk_percent if hasattr(self.config, 'warning_disk_percent') else 80
        
        # Cleanup targets
        self.target_free_percent = self.config.target_free_percent if hasattr(self.config, 'target_free_percent') else 60
        
        logger.info(
            f"Storage manager initialized "
            f"(retention: {self.retention_days}d, warning: {self.warning_disk_percent}%, critical: {self.critical_disk_percent}%)"
        )
    
    def check_disk_health(self) -> dict:
        """
        Check disk health and return status.
        
        Returns:
            Dictionary with disk info
        """
        with self.lock:
            disk_info = SystemInfo.get_disk_info()
            
            used_percent = disk_info['used_percent']
            status = 'healthy'
            
            if used_percent >= self.critical_disk_percent:
                status = 'critical'
                logger.critical(f"CRITICAL: Disk usage at {used_percent}%")
            elif used_percent >= self.warning_disk_percent:
                status = 'warning'
                logger.warning(f"WARNING: Disk usage at {used_percent}%")
            
            return {
                'total_bytes': disk_info['total'],
                'used_bytes': disk_info['used'],
                'free_bytes': disk_info['free'],
                'used_percent': used_percent,
                'status': status,
            }
    
    def enforce_retention_policy(self) -> dict:
        """
        Enforce retention policy by deleting old recordings.
        
        Returns:
            Dictionary with cleanup results
        """
        with self.lock:
            try:
                recordings_path = PathManager.get_recordings_path()
                
                if not os.path.exists(recordings_path):
                    return {
                        'deleted_count': 0,
                        'freed_bytes': 0,
                        'error': None,
                    }
                
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
                
                logger.info(f"Enforcing retention policy: deleting files older than {cutoff_date}")
                
                deleted_count = 0
                freed_bytes = 0
                
                # Walk through recording directory structure (YYYY/MM/DD/camera_id/)
                for root, dirs, files in os.walk(recordings_path):
                    for file in files:
                        if not file.endswith('.mp4'):
                            continue
                        
                        file_path = os.path.join(root, file)
                        
                        try:
                            # Get file modification time
                            mod_time = datetime.utcfromtimestamp(os.path.getmtime(file_path))
                            
                            if mod_time < cutoff_date:
                                # Delete old file
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                deleted_count += 1
                                freed_bytes += file_size
                                logger.debug(f"Deleted old recording: {file_path}")
                        
                        except Exception as e:
                            logger.error(f"Failed to delete {file_path}: {e}")
                
                # Clean up empty directories
                self._cleanup_empty_dirs(recordings_path)
                
                logger.info(
                    f"Retention policy cleanup complete: "
                    f"deleted {deleted_count} files, freed {TimeUtils.format_size(freed_bytes)}"
                )
                
                return {
                    'deleted_count': deleted_count,
                    'freed_bytes': freed_bytes,
                    'error': None,
                }
            
            except Exception as e:
                logger.error(f"Error enforcing retention policy: {e}")
                return {
                    'deleted_count': 0,
                    'freed_bytes': 0,
                    'error': str(e),
                }
    
    def emergency_cleanup(self, target_percent: Optional[int] = None) -> dict:
        """
        Emergency cleanup to free disk space.
        
        Deletes oldest recordings first until target free space reached.
        
        Args:
            target_percent: Target free percentage (default: configured value)
            
        Returns:
            Dictionary with cleanup results
        """
        with self.lock:
            if target_percent is None:
                target_percent = self.target_free_percent
            
            try:
                logger.warning(f"Starting emergency cleanup to reach {target_percent}% free space")
                
                disk_info = SystemInfo.get_disk_info()
                current_used_percent = disk_info['used_percent']
                
                if current_used_percent <= (100 - target_percent):
                    logger.info("Disk already has sufficient free space")
                    return {
                        'deleted_count': 0,
                        'freed_bytes': 0,
                        'current_free_percent': 100 - current_used_percent,
                        'error': None,
                    }
                
                # Get all video files sorted by modification time (oldest first)
                recordings_path = PathManager.get_recordings_path()
                video_files = self._get_video_files_by_age(recordings_path)
                
                if not video_files:
                    logger.warning("No video files found for cleanup")
                    return {
                        'deleted_count': 0,
                        'freed_bytes': 0,
                        'error': 'No video files found',
                    }
                
                deleted_count = 0
                freed_bytes = 0
                
                # Delete oldest files until target reached
                for file_path, file_size in video_files:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        freed_bytes += file_size
                        logger.debug(f"Emergency deleted: {file_path}")
                        
                        # Check if we've freed enough space
                        disk_info = SystemInfo.get_disk_info()
                        if disk_info['used_percent'] <= (100 - target_percent):
                            break
                    
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                
                # Clean up empty directories
                self._cleanup_empty_dirs(recordings_path)
                
                # Get final disk status
                disk_info = SystemInfo.get_disk_info()
                
                logger.warning(
                    f"Emergency cleanup complete: "
                    f"deleted {deleted_count} files, freed {TimeUtils.format_size(freed_bytes)}, "
                    f"disk now at {disk_info['used_percent']}% usage"
                )
                
                return {
                    'deleted_count': deleted_count,
                    'freed_bytes': freed_bytes,
                    'current_free_percent': 100 - disk_info['used_percent'],
                    'error': None,
                }
            
            except Exception as e:
                logger.error(f"Error during emergency cleanup: {e}")
                return {
                    'deleted_count': 0,
                    'freed_bytes': 0,
                    'error': str(e),
                }
    
    def _get_video_files_by_age(self, recordings_path: str) -> List[Tuple[str, int]]:
        """
        Get all video files sorted by modification time (oldest first).
        
        Args:
            recordings_path: Root recordings directory
            
        Returns:
            List of (file_path, file_size) tuples, sorted oldest first
        """
        video_files = []
        
        try:
            for root, dirs, files in os.walk(recordings_path):
                for file in files:
                    if file.endswith('.mp4'):
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            mod_time = os.path.getmtime(file_path)
                            video_files.append((file_path, file_size, mod_time))
                        except Exception as e:
                            logger.debug(f"Failed to stat {file_path}: {e}")
            
            # Sort by modification time (oldest first)
            video_files.sort(key=lambda x: x[2])
            
            # Return as list of (path, size) tuples
            return [(path, size) for path, size, _ in video_files]
        
        except Exception as e:
            logger.error(f"Error getting video files: {e}")
            return []
    
    def _cleanup_empty_dirs(self, recordings_path: str):
        """
        Remove empty directories from recordings path.
        
        Args:
            recordings_path: Root recordings directory
        """
        try:
            for root, dirs, files in os.walk(recordings_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Empty directory
                            os.rmdir(dir_path)
                            logger.debug(f"Removed empty directory: {dir_path}")
                    except Exception as e:
                        logger.debug(f"Failed to remove directory {dir_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error cleaning up empty directories: {e}")
    
    def get_storage_info(self) -> dict:
        """
        Get comprehensive storage information.
        
        Returns:
            Dictionary with storage stats
        """
        with self.lock:
            try:
                recordings_path = PathManager.get_recordings_path()
                
                # Calculate recordings directory size
                total_recordings_bytes = 0
                recording_count = 0
                oldest_recording = None
                newest_recording = None
                
                for root, dirs, files in os.walk(recordings_path):
                    for file in files:
                        if file.endswith('.mp4'):
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                mod_time = os.path.getmtime(file_path)
                                
                                total_recordings_bytes += file_size
                                recording_count += 1
                                
                                if oldest_recording is None or mod_time < oldest_recording[1]:
                                    oldest_recording = (file_path, mod_time)
                                if newest_recording is None or mod_time > newest_recording[1]:
                                    newest_recording = (file_path, mod_time)
                            
                            except Exception as e:
                                logger.debug(f"Failed to stat {file_path}: {e}")
                
                disk_info = SystemInfo.get_disk_info()
                
                return {
                    'total_recordings_bytes': total_recordings_bytes,
                    'recording_count': recording_count,
                    'oldest_recording': oldest_recording[0] if oldest_recording else None,
                    'newest_recording': newest_recording[0] if newest_recording else None,
                    'retention_days': self.retention_days,
                    'disk_used_percent': disk_info['used_percent'],
                    'disk_total_bytes': disk_info['total'],
                    'disk_free_bytes': disk_info['free'],
                }
            
            except Exception as e:
                logger.error(f"Error getting storage info: {e}")
                return {
                    'error': str(e),
                }
