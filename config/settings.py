"""
Configuration Management System for Project Sentinel

Responsibility: Centralized configuration loading and validation.
Supports JSON-based configuration with environment variable overrides.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict, field, fields
import logging
import secrets

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
    warning_disk_percent: int = 80
    critical_disk_percent: int = 95
    target_free_percent: int = 60
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
    
    enable_auth: bool = False
    admin_username: str = "admin"
    admin_password: str = "sentinel"
    session_secret: Optional[str] = field(default_factory=lambda: secrets.token_hex(32))
    require_api_key: bool = False
    api_key: Optional[str] = None
    password_hash_algorithm: str = "bcrypt"
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15


@dataclass
class TelegramConfig:
    """Telegram alerting configuration."""

    enabled: bool = False
    bot_name: Optional[str] = None
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    parse_mode: str = "HTML"
    notify_motion: bool = True
    notify_startup: bool = True
    notify_shutdown: bool = False


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
class WebConfig:
    """Web server configuration."""
    
    host: str = "127.0.0.1"
    port: int = 5000
    use_https: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


@dataclass
class SentinelConfig:
    """Main application configuration."""
    
    app_name: str = "Project Sentinel"
    version: str = "0.2.0"
    debug: bool = False
    auto_start: bool = True
    
    # Sub-configurations with defaults
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    web: WebConfig = field(default_factory=WebConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        for section_name in ('camera', 'motion', 'recording', 'storage', 'database',
                             'security', 'telegram', 'streaming', 'web', 'logging'):
            section = getattr(self, section_name)
            for item in fields(section):
                if item.type in (bool, int, str) and type(getattr(section, item.name)) is not item.type:
                    raise ValueError(f'Invalid type for {section_name}.{item.name}')
        if self.security.max_login_attempts < 1 or self.security.session_timeout_minutes < 1 or self.security.lockout_duration_minutes < 1:
            raise ValueError('Security timeouts and attempt limits must be positive')
        if self.storage.cleanup_check_interval < 1:
            raise ValueError('Cleanup interval must be positive')
        for section in (self.camera, self.streaming):
            if type(section.fps) is not int or not 1 <= section.fps <= 60:
                raise ValueError("FPS must be an integer between 1 and 60")
        if self.camera.resolution not in ('360p', '480p', '720p', '1080p'):
            raise ValueError("Unsupported camera resolution")
        if self.recording.quality not in ('low', 'medium', 'high'):
            raise ValueError("Unsupported recording quality")
        if type(self.recording.enabled) is not bool:
            raise ValueError("Recording enabled must be a boolean")
        if not 0 <= self.recording.post_motion_seconds <= 300:
            raise ValueError("Post motion seconds must be between 0 and 300")
        if self.motion.min_contour_area < 1 or self.motion.morph_kernel_size < 1:
            raise ValueError("Motion area and kernel size must be positive")
        if not 0 < self.storage.warning_disk_percent < self.storage.critical_disk_percent <= 100:
            raise ValueError("Storage warning must be below critical threshold")
        if not 1 <= self.storage.target_free_percent <= 90:
            raise ValueError("Target free space must be between 1 and 90")
        if self.security.require_api_key and not self.security.api_key:
            raise ValueError("API key enforcement requires an API key")
        if self.security.enable_auth and self.security.admin_password == 'sentinel':
            raise ValueError("Set a private admin password before enabling authentication")
        if not 1 <= self.web.port <= 65535:
            raise ValueError("Web port must be between 1 and 65535")
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
            except (OSError, ValueError) as e:
                raise ValueError(f"Unable to load configuration: {self.config_file}") from e
        
        # Override with environment variables
        config_dict = self._apply_env_overrides(config_dict)
        
        # Create configuration object
        return self._dict_to_config(config_dict)
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "app_name": "Project Sentinel",
            "version": "0.2.0",
            "debug": False,
            "auto_start": True,
            "camera": asdict(CameraConfig()),
            "motion": asdict(MotionConfig()),
            "recording": asdict(RecordingConfig()),
            "storage": asdict(StorageConfig()),
            "database": asdict(DatabaseConfig()),
            "security": asdict(SecurityConfig()),
            "telegram": asdict(TelegramConfig()),
            "streaming": asdict(StreamingConfig()),
            "web": asdict(WebConfig()),
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
                if key == "SENTINEL_TELEGRAM_BOT_TOKEN":
                    config.setdefault("telegram", {})["bot_token"] = os.environ[key]
                    continue

                if key == "SENTINEL_TELEGRAM_BOT_NAME":
                    config.setdefault("telegram", {})["bot_name"] = os.environ[key]
                    continue

                if key == "SENTINEL_TELEGRAM_CHAT_ID":
                    config.setdefault("telegram", {})["chat_id"] = os.environ[key]
                    continue

                # Convert SENTINEL_CAMERA_FPS to camera.fps
                config_path = key[len(env_prefix):].lower()
                value = os.environ[key]
                section, _, field_name = config_path.partition('_')
                existing = config.get(config_path) if config_path in config else config.get(section, {}).get(field_name)
                if isinstance(existing, str) or existing is None:
                    ConfigManager._set_nested(config, config_path, value)
                    continue
                
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
        # Match existing keys, preserving underscores within field names.
        if path in data and not isinstance(data[path], dict):
            data[path] = value
            return
        section, _, field_name = path.partition('_')
        if section in data and isinstance(data[section], dict) and field_name in data[section]:
            data[section][field_name] = value
            return
        raise ValueError(f"Unknown configuration override: {path}")
    
    @staticmethod
    def _dict_to_config(config_dict: Dict[str, Any]) -> SentinelConfig:
        """Convert dictionary to SentinelConfig object."""
        return SentinelConfig(
            app_name=config_dict.get("app_name", "Project Sentinel"),
            version=config_dict.get("version", "0.2.0"),
            debug=config_dict.get("debug", False),
            auto_start=config_dict.get("auto_start", True),
            camera=CameraConfig(**config_dict.get("camera", {})),
            motion=MotionConfig(**config_dict.get("motion", {})),
            recording=RecordingConfig(**config_dict.get("recording", {})),
            storage=StorageConfig(**config_dict.get("storage", {})),
            database=DatabaseConfig(**config_dict.get("database", {})),
            security=SecurityConfig(**config_dict.get("security", {})),
            telegram=TelegramConfig(**config_dict.get("telegram", {})),
            streaming=StreamingConfig(**config_dict.get("streaming", {})),
            web=WebConfig(**config_dict.get("web", {})),
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

    def save_public_patch(self, patch):
        """Validate and atomically persist editable settings; apply on restart."""
        allowed = {
            'camera': {'fps', 'resolution'},
            'motion': {'sensitivity', 'min_contour_area'},
            'recording': {'enabled', 'quality', 'post_motion_seconds'},
            'storage': {'retention_days', 'critical_disk_percent', 'target_free_percent'},
        }
        if not isinstance(patch, dict) or not patch:
            raise ValueError('Settings must be a non-empty object')
        for section, values in patch.items():
            if section not in allowed or not isinstance(values, dict) or set(values) - allowed[section]:
                raise ValueError('Unsupported settings field')
            for key, value in values.items():
                expected = type(getattr(getattr(self.config, section), key))
                if type(value) is not expected:
                    raise ValueError(f'Invalid type for {section}.{key}')
        candidate = self._deep_merge(self.config.to_dict(), patch)
        self._dict_to_config(candidate)
        # Start from the disk file so environment secrets are never written.
        disk = json.loads(self.config_file.read_text()) if self.config_file.exists() else {}
        disk = self._deep_merge(disk, patch)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.config_file.parent,
                                         delete=False, suffix='.tmp') as stream:
            temp_path = Path(stream.name)
            json.dump(disk, stream, indent=2)
        try:
            os.replace(temp_path, self.config_file)
        finally:
            temp_path.unlink(missing_ok=True)


def save_public_settings(patch):
    get_config()
    _config_manager.save_public_patch(patch)


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
