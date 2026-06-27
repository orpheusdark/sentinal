"""
Common Utilities for Project Sentinel

Responsibility: Helper functions and utilities used across modules.
"""

import psutil
import platform
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SystemInfo:
    """Gather and report system information."""
    
    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """Get CPU information."""
        return {
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
        }
    
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """Get memory information."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024**3),
            "used_gb": mem.used / (1024**3),
            "available_gb": mem.available / (1024**3),
            "percent": mem.percent,
        }
    
    @staticmethod
    def get_disk_info(path: str = "/") -> Dict[str, Any]:
        """Get disk information."""
        disk = shutil.disk_usage(path)
        used_percent = (disk.used / disk.total) * 100
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "total_gb": disk.total / (1024**3),
            "used_gb": disk.used / (1024**3),
            "free_gb": disk.free / (1024**3),
            "used_percent": used_percent,
            "free_percent": 100 - used_percent,
            "percent": used_percent,
        }
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get complete system information."""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu": SystemInfo.get_cpu_info(),
            "memory": SystemInfo.get_memory_info(),
            "disk": SystemInfo.get_disk_info(),
        }
    
    @staticmethod
    def get_current_metrics() -> Dict[str, Any]:
        """Get current system metrics."""
        mem = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": mem.percent,
            "memory_used_mb": mem.used / (1024**2),
            "memory_available_mb": mem.available / (1024**2),
            "disk_used_gb": disk.used / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
            "disk_percent": (disk.used / disk.total) * 100,
        }


class PathManager:
    """Manage application paths."""
    
    def __init__(self, base_path: str = "."):
        """Initialize PathManager with base path."""
        self.base_path = Path(base_path).resolve()
    
    def get_path(self, relative_path: str) -> Path:
        """Get absolute path from relative path."""
        return (self.base_path / relative_path).resolve()
    
    def ensure_dir(self, relative_path: str) -> Path:
        """Ensure directory exists and return its path."""
        path = self.get_path(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_recording_path(self, camera_name: str, timestamp: datetime) -> Path:
        """Get organized recording path."""
        # recordings/YYYY/MM/DD/camera_name/
        path = self.ensure_dir(
            f"recordings/{timestamp.year:04d}/{timestamp.month:02d}/{timestamp.day:02d}/{camera_name}"
        )
        return path
    
    def get_snapshot_path(self, camera_name: str) -> Path:
        """Get snapshot directory path."""
        return self.ensure_dir(f"snapshots/{camera_name}")
    
    def get_log_path(self) -> Path:
        """Get logs directory path."""
        return self.ensure_dir("logs")
    
    def get_config_path(self) -> Path:
        """Get config directory path."""
        return self.ensure_dir("config")
    
    def get_database_path(self) -> Path:
        """Get database directory path."""
        return self.ensure_dir("data")


class ResourceMonitor:
    """Monitor system resources and enforce limits."""
    
    # Performance thresholds
    IDLE_CPU_THRESHOLD = 10  # percent
    RECORDING_CPU_THRESHOLD = 25  # percent
    WARNING_MEMORY_PERCENT = 80  # percent
    CRITICAL_MEMORY_PERCENT = 90  # percent
    CRITICAL_DISK_PERCENT = 95  # percent
    
    @staticmethod
    def check_cpu_health() -> Tuple[bool, str]:
        """Check if CPU usage is within acceptable limits."""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > ResourceMonitor.RECORDING_CPU_THRESHOLD:
            return False, f"High CPU usage: {cpu_percent:.1f}%"
        
        return True, f"CPU usage: {cpu_percent:.1f}%"
    
    @staticmethod
    def check_memory_health() -> Tuple[bool, str]:
        """Check if memory usage is within acceptable limits."""
        mem = psutil.virtual_memory()
        
        if mem.percent >= ResourceMonitor.CRITICAL_MEMORY_PERCENT:
            return False, f"Critical memory usage: {mem.percent:.1f}%"
        
        if mem.percent >= ResourceMonitor.WARNING_MEMORY_PERCENT:
            logger.warning(f"High memory usage: {mem.percent:.1f}%")
        
        return True, f"Memory usage: {mem.percent:.1f}%"
    
    @staticmethod
    def check_disk_health() -> Tuple[bool, str]:
        """Check if disk usage is within acceptable limits."""
        disk = shutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent >= ResourceMonitor.CRITICAL_DISK_PERCENT:
            return False, f"Critical disk usage: {disk_percent:.1f}%"
        
        return True, f"Disk usage: {disk_percent:.1f}%"
    
    @staticmethod
    def full_health_check() -> Tuple[bool, Dict[str, Any]]:
        """Perform full system health check."""
        results = {
            "cpu": ResourceMonitor.check_cpu_health(),
            "memory": ResourceMonitor.check_memory_health(),
            "disk": ResourceMonitor.check_disk_health(),
        }
        
        healthy = all(result[0] for result in results.values())
        
        return healthy, {
            "cpu_status": results["cpu"][1],
            "memory_status": results["memory"][1],
            "disk_status": results["disk"][1],
        }


class TimeUtils:
    """Time utility functions."""
    
    @staticmethod
    def now() -> datetime:
        """Get current UTC datetime."""
        return datetime.utcnow()
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}m"
        
        hours = minutes / 60
        if hours < 24:
            return f"{hours:.1f}h"
        
        days = hours / 24
        return f"{days:.1f}d"
    
    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """Format bytes into human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        
        return f"{bytes_size:.1f} PB"
