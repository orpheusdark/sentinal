"""
Main Application Launcher for Project Sentinel

Responsibility: Application initialization, startup sequence, and graceful shutdown.
Entry point for the surveillance system.
"""

import signal
import sys
import time
import threading
import argparse
from pathlib import Path
from typing import Optional
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import initialize_config
from utils import initialize_logging, get_logger
from database import initialize_database, get_db_session, Camera
from utils.system import SystemInfo, PathManager, ResourceMonitor
from camera import CameraManager
from motion import MotionDetector, MotionEventManager
from recording import RecordingManager
from storage import StorageManager
from alerts import TelegramAlertManager
from alerts.queue import QueuedAlerts
from camera.pipeline import CameraPipeline
import cv2
from web import WebServer, StreamManager


class ApplicationContext:
    """
    Holds application context and state.
    
    Manages:
    - Initialization
    - Shutdown coordination
    - Component lifecycle
    """
    
    def __init__(self):
        """Initialize application context."""
        self.running = False
        self.logger = None
        self.config = None
        self.db = None
        self.path_manager = None
        self.camera_manager = None
        self.motion_detector = None
        self.motion_event_manager = None
        self.recording_manager = None
        self.storage_manager = None
        self.web_server = None
        self.stream_manager = None
        self.alert_manager = None
        self.active_camera_db_id = None
        self.pipelines = {}
        self._shutdown_event = threading.Event()
    
    def shutdown(self):
        """Signal application shutdown."""
        self.running = False
        self._shutdown_event.set()


class Application:
    """
    Main Application Class
    
    Responsibilities:
    - System initialization
    - Component lifecycle management
    - Graceful shutdown
    - Health monitoring
    """
    
    def __init__(self, config_file: Optional[str] = None, no_auth: bool = False):
        """
        Initialize application.
        
        Args:
            config_file: Path to configuration file
        """
        self.context = ApplicationContext()
        self.config_file = config_file
        self.no_auth = no_auth
        self._initialize_signal_handlers()
    
    def _initialize_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.context.shutdown()
    
    def initialize(self) -> bool:
        """
        Initialize application systems.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Step 1: Initialize logging
            self.logger = self._initialize_logging()
            self.logger.info("Starting Project Sentinel initialization...")
            
            # Step 2: Initialize configuration
            self.context.config = initialize_config(self.config_file)
            cv2.setNumThreads(self.context.config.camera.opencv_threads)
            self.logger.info(f"Configuration loaded: {self.context.config.app_name} v{self.context.config.version}")

            if self.no_auth:
                self.context.config.security.enable_auth = False
                self.context.config.security.require_api_key = False
                self.context.config.web.host = '127.0.0.1'
                self.logger.info("Headless mode enabled: dashboard authentication disabled for unattended startup")
            
            # Step 3: Initialize path manager
            self.context.path_manager = PathManager(str(PROJECT_ROOT))
            self.logger.info("Path manager initialized")
            
            # Step 4: Initialize database
            db_path = self.context.config.database.path
            self.context.db = initialize_database(db_path, echo=False)
            self.logger.info(f"Database initialized at {db_path}")
            
            # Step 5: Initialize camera manager
            self.context.camera_manager = CameraManager(self.context.config.camera)
            if not self.context.camera_manager.initialize():
                self.logger.warning("Camera unavailable; dashboard will remain accessible")
            self.context.active_camera_db_id = self.context.camera_manager.get_camera_database_id()
            if self.context.active_camera_db_id is None:
                self.logger.warning("Unable to resolve active camera database ID during initialization")
            self.logger.info("Camera manager initialized")
            
            # Step 6: Initialize motion detector
            self.context.motion_detector = MotionDetector(self.context.config.motion)
            self.context.motion_event_manager = MotionEventManager()
            self.logger.info("Motion detector initialized")
            
            # Step 7: Initialize recording manager
            self.context.recording_manager = RecordingManager(self.context.config.recording)
            self.logger.info("Recording manager initialized")
            
            # Step 8: Initialize storage manager
            self.context.storage_manager = StorageManager(self.context.config.storage)
            self.context.storage_manager.active_recording_path = lambda: [
                pipeline.recorder.current_video_path for pipeline in self.context.pipelines.values()
                if pipeline.recorder.is_recording]
            self.context.storage_manager.reconcile_archive()
            self.logger.info("Storage manager initialized")

            # Step 9: Initialize Telegram alerts
            telegram_config = self.context.config.telegram
            self.context.alert_manager = TelegramAlertManager(
                bot_token=telegram_config.bot_token,
                chat_id=telegram_config.chat_id,
                enabled=telegram_config.enabled,
                parse_mode=telegram_config.parse_mode,
                bot_name=telegram_config.bot_name,
            )
            self.context.alert_manager = QueuedAlerts(self.context.alert_manager)
            self.logger.info("Alert queue initialized")
            
            # Step 10: Initialize stream manager
            stream = self.context.config.streaming
            self.context.stream_manager = StreamManager(
                quality={'low': 40, 'medium': 70, 'high': 90}[stream.quality], target_fps=stream.fps)
            self.logger.info("Stream manager initialized")
            
            self._setup_pipelines()

            # Step 11: Initialize web server
            web_config = self.context.config.web
            self.context.web_server = WebServer(host=web_config.host, port=web_config.port, debug=self.context.config.debug)
            self.context.web_server.set_app_context(self.context)
            if self.context.config.web.check_updates:
                self.context.web_server.updates.check()
            self.logger.info("Web server initialized")
            
            # Step 12: Start web server in background thread
            ssl_context = None
            if web_config.use_https:
                if web_config.ssl_cert_path and web_config.ssl_key_path:
                    ssl_context = (web_config.ssl_cert_path, web_config.ssl_key_path)
                else:
                    raise ValueError("HTTPS requires both certificate and key paths")

            self.context.web_server.start(threaded=True, ssl_context=ssl_context)
            scheme = 'https' if ssl_context else 'http'
            self.logger.info(f"Web server started on {scheme}://{web_config.host}:{web_config.port}")

            if self.context.alert_manager and self.context.alert_manager.is_configured() and self.context.config.telegram.notify_startup:
                startup_result = self.context.alert_manager.send_startup_alert(
                    app_name=self.context.config.app_name,
                    host=self.context.web_server.host,
                    port=self.context.web_server.port,
                )
                if startup_result.success:
                    self.logger.info("Telegram startup alert sent")
                else:
                    self.logger.warning(f"Telegram startup alert failed: {startup_result.error_message}")
            
            # Step 13: Log system information
            self._log_system_info()
            
            # Step 14: Perform health check
            healthy, health_status = ResourceMonitor.full_health_check()
            if not healthy:
                self.logger.warning("System health check warnings:")
                for key, status in health_status.items():
                    self.logger.warning(f"  {key}: {status}")
            
            self.logger.info("Application initialization complete")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize application: {e}", exc_info=True)
            else:
                print(f"FATAL: Failed to initialize application: {e}")
            return False
    
    def _initialize_logging(self) -> logging.Logger:
        """Initialize logging system."""
        log_dir = "logs"
        log_format = "json"
        
        # Create logs directory
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        initialize_logging(log_dir, log_format)
        return get_logger(__name__, level="INFO")
    
    def _log_system_info(self):
        """Log system information on startup."""
        system_info = SystemInfo.get_system_info()
        
        self.logger.info("=" * 80)
        self.logger.info("SYSTEM INFORMATION")
        self.logger.info("=" * 80)
        self.logger.info(f"Platform: {system_info['platform']} {system_info['platform_version']}")
        self.logger.info(f"Architecture: {system_info['architecture']}")
        self.logger.info(f"Hostname: {system_info['hostname']}")
        self.logger.info(f"Python: {system_info['python_version']}")
        self.logger.info("")
        self.logger.info(f"CPU: {system_info['cpu']['processor']}")
        self.logger.info(f"CPU Cores: {system_info['cpu']['cpu_count']} physical, {system_info['cpu']['cpu_count_logical']} logical")
        self.logger.info(f"Memory: {system_info['memory']['total_gb']:.1f} GB total")
        self.logger.info(f"Disk: {system_info['disk']['total_gb']:.1f} GB total")
        self.logger.info("=" * 80)
    
    def _setup_pipelines(self, start=False):
        manager=self.context.camera_manager
        for driver_id, profile in getattr(manager,'profiles',{}).items():
            db_id=manager.camera_db_ids.get(driver_id)
            if db_id is None: continue
            if db_id not in self.context.pipelines:
                self.context.pipelines[db_id]=CameraPipeline(driver_id,db_id,profile,self.context.config,
                                                            manager,self.context.alert_manager)
            if start: self.context.pipelines[db_id].start()
        if self.context.pipelines:
            first=next(iter(self.context.pipelines.values()))
            self.context.motion_detector=first.detector
            self.context.motion_event_manager=first.events
            self.context.recording_manager=first.recorder
            self.context.stream_manager=first.stream

    def run(self) -> int:
        if not self.initialize():
            self.shutdown(); return 1
        if self.context._shutdown_event.is_set():
            self.shutdown(); return 0
        self.context.running=True
        self._setup_pipelines(start=True)
        health=time.monotonic(); disk=health; retention=0; updates=health
        try:
            while not self.context._shutdown_event.wait(1):
                now=time.monotonic()
                if now-health>=30:
                    self.context.camera_manager.check_health()
                    self._setup_pipelines(start=True)
                    health=now
                if self.context.config.web.check_updates and now-updates>=86400:
                    self.context.web_server.updates.check(); updates=now
                if self.context.config.recording.auto_cleanup:
                    if now-disk>=60:
                        state=self.context.storage_manager.check_disk_health()
                        if state['status']=='critical': self.context.storage_manager.emergency_cleanup()
                        disk=now
                    if now-retention>=self.context.config.storage.cleanup_check_interval:
                        self.context.storage_manager.enforce_retention_policy(); retention=now
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception:
            self.logger.exception('Application coordinator failed'); return 1
        finally:
            self.context.running=False
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown the application."""
        self.logger.info("Initiating application shutdown...")
        
        try:
            # Shutdown web server first
            if self.context.web_server:
                self.logger.info("Shutting down web server...")
                self.context.web_server.stop()
            
            for pipeline in self.context.pipelines.values():
                pipeline.stop()

            # Shutdown recording
            if self.context.recording_manager:
                if self.context.recording_manager.is_recording:
                    self.context.recording_manager._stop_recording()

            if self.context.alert_manager and self.context.alert_manager.is_configured() and self.context.config.telegram.notify_shutdown:
                shutdown_result = self.context.alert_manager.send_shutdown_alert(self.context.config.app_name)
                if shutdown_result.success:
                    self.logger.info("Telegram shutdown alert sent")
            
            if self.context.alert_manager:
                self.context.alert_manager.close(timeout=2)

            # Shutdown camera
            if self.context.camera_manager:
                self.context.camera_manager.shutdown()
            
            # Close database
            if self.context.db:
                self.context.db.close()
            
            self.logger.info("Application shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)


def main():
    """Application entry point."""
    parser = argparse.ArgumentParser(description="Project Sentinel surveillance application")
    parser.add_argument("--no-auth", action="store_true", help="Start without dashboard authentication for unattended boot")
    parser.add_argument("--config", dest="config_file", default=None, help="Path to configuration file")
    args = parser.parse_args()

    app = Application(config_file=args.config_file, no_auth=args.no_auth)
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
