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
            self.logger.info(f"Configuration loaded: {self.context.config.app_name} v{self.context.config.version}")

            if self.no_auth:
                self.context.config.security.enable_auth = False
                self.context.config.security.require_api_key = False
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
                self.logger.error("Failed to initialize camera manager")
                return False
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
            self.logger.info("Alert manager initialized")
            
            # Step 10: Initialize stream manager
            self.context.stream_manager = StreamManager(quality=75, target_fps=15)
            self.logger.info("Stream manager initialized")
            
            # Step 11: Initialize web server
            web_config = self.context.config.web
            self.context.web_server = WebServer(host=web_config.host, port=web_config.port, debug=self.context.config.debug)
            self.context.web_server.set_app_context(self.context)
            self.logger.info("Web server initialized")
            
            # Step 12: Start web server in background thread
            ssl_context = None
            if web_config.use_https:
                if web_config.ssl_cert_path and web_config.ssl_key_path:
                    ssl_context = (web_config.ssl_cert_path, web_config.ssl_key_path)
                else:
                    self.logger.warning("HTTPS enabled but SSL certificate/key path not configured")

            web_thread = threading.Thread(target=self.context.web_server.run, args=(True, ssl_context), daemon=True)
            web_thread.start()
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
    
    def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Exit code (0 = success, non-zero = failure)
        """
        # Initialize
        if not self.initialize():
            return 1
        
        self.context.running = True
        self.logger.info("Application started")
        
        try:
            # Main application loop
            health_check_counter = 0
            disk_check_counter = 0
            
            while self.context.running:
                try:
                    # Periodic health check (every 30 seconds)
                    health_check_counter += 1
                    disk_check_counter += 1
                    if health_check_counter >= 450:  # 15 FPS * 30 seconds
                        self.context.camera_manager.check_health()
                        health_check_counter = 0
                    
                    # Periodic disk check (every 60 seconds)
                    if disk_check_counter >= 900:  # 15 FPS * 60 seconds
                        disk_health = self.context.storage_manager.check_disk_health()
                        if disk_health['status'] == 'critical':
                            self.logger.warning(f"Disk critical: {disk_health['used_percent']}% full, triggering cleanup")
                            self.context.storage_manager.emergency_cleanup()
                        elif disk_health['status'] == 'warning':
                            self.logger.warning(f"Disk warning: {disk_health['used_percent']}% full, enforcing retention")
                            self.context.storage_manager.enforce_retention_policy()
                        disk_check_counter = 0
                    
                    # Get frame from camera
                    frame_data = self.context.camera_manager.get_frame()
                    
                    if frame_data is None:
                        time.sleep(0.1)
                        continue
                    
                    frame, timestamp, camera_id = frame_data
                    database_camera_id = self.context.camera_manager.get_camera_database_id(camera_id)
                    if database_camera_id is None:
                        database_camera_id = self.context.active_camera_db_id
                    if database_camera_id is None:
                        self.logger.warning(f"Skipping frame because camera database ID could not be resolved: {camera_id}")
                        time.sleep(1.0 / self.context.config.camera.fps)
                        continue
                    
                    # Detect motion
                    motion_result = self.context.motion_detector.process_frame(frame)
                    
                    # Handle motion events
                    if motion_result.motion_detected:
                        event = self.context.motion_event_manager.on_motion_detected(
                            camera_id=database_camera_id,
                            result=motion_result
                        )
                        
                        # Trigger recording on motion
                        self.context.recording_manager.on_motion_detected(
                            camera_id=database_camera_id,
                            motion_start_time=timestamp
                        )
                        
                        if event:
                            self.logger.info(
                                f"Motion detected: contours={motion_result.contour_count}, "
                                f"area={int(motion_result.max_contour_area)}"
                            )
                            if self.context.alert_manager and self.context.alert_manager.is_configured() and self.context.config.telegram.notify_motion:
                                camera_name = self.context.camera_manager.get_camera(camera_id).name if self.context.camera_manager.get_camera(camera_id) else f"Camera {camera_id}"
                                alert_result = self.context.alert_manager.send_motion_alert(
                                    camera_name=camera_name,
                                    camera_id=database_camera_id,
                                    timestamp=timestamp,
                                    contour_count=motion_result.contour_count,
                                    max_contour_area=int(motion_result.max_contour_area),
                                )
                                if not alert_result.success:
                                    self.logger.warning(f"Telegram motion alert failed: {alert_result.error_message}")
                    else:
                        # Check if motion event ended
                        if self.context.motion_event_manager.current_event_id is not None:
                            self.context.motion_event_manager.on_motion_ended()
                            # Trigger end of recording
                            self.context.recording_manager.on_motion_ended(timestamp)
                    
                    # Write frame to recording
                    recording_result = self.context.recording_manager.write_frame(
                        frame=frame,
                        frame_timestamp=timestamp,
                        camera_id=database_camera_id
                    )
                    
                    # Update stream with current frame
                    self.context.stream_manager.update_frame(frame)
                    
                    # Frame rate limiting (15 FPS default)
                    time.sleep(1.0 / self.context.config.camera.fps)
                    
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(1)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            return 1
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the application."""
        self.logger.info("Initiating application shutdown...")
        
        try:
            # Shutdown web server first
            if self.context.web_server:
                self.logger.info("Shutting down web server...")
                # Flask will stop in background thread
            
            # Shutdown recording
            if self.context.recording_manager:
                if self.context.recording_manager.is_recording:
                    self.context.recording_manager._stop_recording()

            if self.context.alert_manager and self.context.alert_manager.is_configured() and self.context.config.telegram.notify_shutdown:
                shutdown_result = self.context.alert_manager.send_shutdown_alert(self.context.config.app_name)
                if shutdown_result.success:
                    self.logger.info("Telegram shutdown alert sent")
            
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
