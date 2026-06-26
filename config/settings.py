"""
Configuration Management System for Project Sentinel

Responsibility: Centralized configuration loading and validation.
Supports JSON-based configuration with environment variable overrides.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera configuration."""
    
    enabled: bool = True
    fps: int = 15
    resolution: str = "720p"
    auto_reconnect: bool = True
    reconnect_interval: int = 5  # seconds


@dataclass
class MotionConfig:
    """Motion detection configuration."""
    
    enabled: bool = True
    sensitivity: int = 30  # 0-100 (lower = more sensitive)
    min_contour_area: int = 300  # pixels (lower = detects smaller movements)
    morph_kernel_size: int = 5
    cooldown_seconds: int = 2
    background_learning_frames: int = 30


@dataclass
class RecordingConfig:
    """Recording configuration."""
    
    enabled: bool = True
    record_on_motion: bool = True
    post_motion_seconds: int = 10
    codec: str = "mp4v"
    quality: str = "high"  # low, medium, high
    auto_cleanup: bool = True


@dataclass
class StorageConfig:
    """Storage configuration."""
    
    recordings_dir: str = "recordings"
    snapshots_dir: str = "snapshots"
    logs_dir: str = "logs"
    max_disk_usage_percent: int = 80
    retention_days: int = 30
    cleanup_check_interval: int = 3600  # seconds


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    path: str = "data/sentinel.db"
    enable_wal: bool = True
    timeout: int = 30
    check_same_thread: bool = False


@dataclass
class SecurityConfig:
    """Security configuration."""
    
    enable_auth: bool = True
    password_hash_algorithm: str = "bcrypt"
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


@dataclass
class StreamingConfig:
    """Streaming configuration."""
    
    enabled: bool = True
    port: int = 5000
    quality: str = "medium"  # low, medium, high
    fps: int = 15
    bitrate_kbps: int = 2000


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "json"  # json, standard
    max_file_size_mb: int = 10
    backup_count: int = 5
    log_to_console: bool = True
    log_to_file: bool = True


@dataclass
class SentinelConfig:
    """Main application configuration."""
    
    app_name: str = "Project Sentinel"
    version: str = "0.1.0"
    debug: bool = False
    auto_start: bool = True
    
    # Sub-configurations with defaults
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if self.motion.sensitivity < 0 or self.motion.sensitivity > 100:
            raise ValueError("Motion sensitivity must be between 0 and 100")
        
        if self.storage.max_disk_usage_percent < 50 or self.storage.max_disk_usage_percent > 100:
            raise ValueError("Disk usage percent must be between 50 and 100")
        
        if self.storage.retention_days < 1:
            raise ValueError("Retention days must be at least 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def get_nested(self, path: str, default: Any = None) -> Any:
        """
        Get nested config value using dot notation.
        
        Example: config.get_nested("camera.fps")
        """
        keys = path.split(".")
        value = self
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = getattr(value, key, None)
            
            if value is None:
                return default
        
        return value


class ConfigManager:
    """
    Manages application configuration.
    
    Loads configuration from JSON file and environment variables.
    Environment variables override JSON configuration.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_file: Path to JSON configuration file.
                        Defaults to 'config/settings.json'
        """
        if config_file is None:
            config_file = Path(__file__).parent / "settings.json"
        
        self.config_file = Path(config_file)
        self.config: SentinelConfig = self._load_config()
    
    def _load_config(self) -> SentinelConfig:
        """Load configuration from file and environment."""
        # Load defaults
        config_dict = self._get_default_config()
        
        # Merge from JSON file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    config_dict = self._deep_merge(config_dict, file_config)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file {self.config_file}: {e}")
        
        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)
        
        # Create configuration object
        return self._dict_to_config(config_dict)
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app_name": "Project Sentinel",
            "version": "0.1.0",
            "debug": False,
            "auto_start": True,
            "camera": asdict(CameraConfig()),
            "motion": asdict(MotionConfig()),
            "recording": asdict(RecordingConfig()),
            "storage": asdict(StorageConfig()),
            "database": asdict(DatabaseConfig()),
            "security": asdict(SecurityConfig()),
            "streaming": asdict(StreamingConfig()),
            "logging": asdict(LoggingConfig()),
        }
    
    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Deep merge override dict into base dict."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        env_prefix = "SENTINEL_"
        
        for key in os.environ:
            if key.startswith(env_prefix):
                # Convert SENTINEL_CAMERA_FPS to camera.fps
                config_path = key[len(env_prefix):].lower()
                value = os.environ[key]
                
                # Try to parse as number
                try:
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except (ValueError, AttributeError):
                    pass  # Keep as string
                
                ConfigManager._set_nested(config, config_path, value)
        
        return config
    
    @staticmethod
    def _set_nested(data: Dict, path: str, value: Any):
        """Set nested value using dot notation."""
        keys = path.split("_")
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    @staticmethod
    def _dict_to_config(config_dict: Dict[str, Any]) -> SentinelConfig:
        """Convert dictionary to SentinelConfig object."""
        return SentinelConfig(
            app_name=config_dict.get("app_name", "Project Sentinel"),
            version=config_dict.get("version", "0.1.0"),
            debug=config_dict.get("debug", False),
            auto_start=config_dict.get("auto_start", True),
            camera=CameraConfig(**config_dict.get("camera", {})),
            motion=MotionConfig(**config_dict.get("motion", {})),
            recording=RecordingConfig(**config_dict.get("recording", {})),
            storage=StorageConfig(**config_dict.get("storage", {})),
            database=DatabaseConfig(**config_dict.get("database", {})),
            security=SecurityConfig(**config_dict.get("security", {})),
            streaming=StreamingConfig(**config_dict.get("streaming", {})),
            logging=LoggingConfig(**config_dict.get("logging", {})),
        )
    
    def save_config(self, filepath: Optional[str] = None):
        """Save current configuration to JSON file."""
        filepath = filepath or self.config_file
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
        
        logger.info(f"Configuration saved to {filepath}")
    
    def reload_config(self):
        """Reload configuration from file."""
        self.config = self._load_config()
        logger.info("Configuration reloaded")


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> SentinelConfig:
    """Get global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config


def initialize_config(config_file: Optional[str] = None) -> SentinelConfig:
    """Initialize global configuration."""
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager.config
