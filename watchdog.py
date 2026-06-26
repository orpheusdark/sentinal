"""
Watchdog Process for Project Sentinel

Responsibility: Monitor application health and restart components as needed.
Runs as a separate process to ensure application recovery.
Never requires user intervention.
"""

import subprocess
import time
import sys
import signal
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from utils import initialize_logging, get_logger
from utils.system import ResourceMonitor, SystemInfo


class ProcessMonitor:
    """Monitor and manage application processes."""
    
    def __init__(self, app_script: str = "app.py"):
        """
        Initialize ProcessMonitor.
        
        Args:
            app_script: Path to main application script
        """
        self.app_script = Path(app_script).resolve()
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.last_restart_time = 0
        self.restart_backoff = 5  # seconds
        self.max_restart_backoff = 300  # 5 minutes
    
    def is_running(self) -> bool:
        """Check if application process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def start(self) -> bool:
        """Start the application process."""
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(self.app_script)],
                cwd=self.app_script.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            logging.info(f"Started application process: PID {self.process.pid}")
            self.last_restart_time = time.time()
            return True
            
        except Exception as e:
            logging.error(f"Failed to start application process: {e}")
            return False
    
    def stop(self):
        """Stop the application process."""
        if self.process is None:
            return
        
        try:
            self.process.terminate()
            
            try:
                self.process.wait(timeout=10)
                logging.info("Application process terminated gracefully")
            except subprocess.TimeoutExpired:
                logging.warning("Process did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
                logging.info("Application process killed")
        
        except Exception as e:
            logging.error(f"Error stopping application process: {e}")
    
    def restart(self):
        """Restart the application process."""
        logging.warning("Restarting application process...")
        
        self.stop()
        time.sleep(self.restart_backoff)
        
        if self.start():
            self.restart_count += 1
            
            # Increase backoff for next restart
            self.restart_backoff = min(self.restart_backoff * 1.5, self.max_restart_backoff)
            logging.info(f"Application restarted (count: {self.restart_count})")
        else:
            logging.error("Failed to restart application")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current process status."""
        return {
            "running": self.is_running(),
            "pid": self.process.pid if self.process else None,
            "restart_count": self.restart_count,
            "last_restart_time": self.last_restart_time,
        }


class Watchdog:
    """
    Application Watchdog
    
    Monitors:
    - Application process health
    - System resources
    - Restart failures
    - Recovery procedures
    """
    
    def __init__(self, app_script: str = "app.py", check_interval: int = 30):
        """
        Initialize Watchdog.
        
        Args:
            app_script: Path to main application script
            check_interval: Health check interval in seconds
        """
        self.app_script = app_script
        self.check_interval = check_interval
        self.running = False
        self.monitor = ProcessMonitor(app_script)
        self.logger = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Watchdog received signal {signum}")
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize watchdog."""
        try:
            self.logger = self._setup_logging()
            self.logger.info("Watchdog initialized")
            return True
        except Exception as e:
            print(f"Failed to initialize watchdog: {e}")
            return False
    
    def _setup_logging(self) -> logging.Logger:
        """Setup watchdog logging."""
        log_dir = "logs"
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        initialize_logging(log_dir, "json")
        return get_logger("watchdog", level="INFO")
    
    def health_check(self) -> bool:
        """
        Perform health check.
        
        Returns:
            True if healthy, False if action needed
        """
        # Check if process is running
        if not self.monitor.is_running():
            self.logger.warning("Application process is not running")
            return False
        
        # Check system resources
        healthy, status = ResourceMonitor.full_health_check()
        if not healthy:
            self.logger.warning("System resource issues detected:")
            for key, value in status.items():
                self.logger.warning(f"  {key}: {value}")
            return False
        
        return True
    
    def run(self) -> int:
        """
        Run the watchdog.
        
        Returns:
            Exit code
        """
        if not self.initialize():
            return 1
        
        self.running = True
        self.logger.info("Watchdog started")
        
        # Log system info
        system_info = SystemInfo.get_system_info()
        self.logger.info(f"System: {system_info['platform']} on {system_info['architecture']}")
        
        try:
            # Start application
            if not self.monitor.start():
                self.logger.error("Failed to start application initially")
                return 1
            
            # Main watchdog loop
            while self.running:
                try:
                    # Perform health check
                    if not self.health_check():
                        self.logger.warning("Health check failed, attempting restart...")
                        self.monitor.restart()
                    
                    # Sleep before next check
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in watchdog loop: {e}", exc_info=True)
                    time.sleep(self.check_interval)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Fatal watchdog error: {e}", exc_info=True)
            return 1
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the watchdog."""
        self.logger.info("Watchdog shutdown initiated")
        
        try:
            self.monitor.stop()
            self.logger.info("Watchdog shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during watchdog shutdown: {e}")


def main():
    """Watchdog entry point."""
    app_script = PROJECT_ROOT / "app.py"
    watchdog = Watchdog(str(app_script), check_interval=30)
    exit_code = watchdog.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
