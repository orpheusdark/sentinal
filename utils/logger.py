"""
Structured Logging System for Project Sentinel

Responsibility: Centralized, structured logging with rotation and crash reporting.
Supports both JSON and standard formats.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


class StandardFormatter(logging.Formatter):
    """Standard text formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    FORMAT = (
        '%(asctime)s - %(name)s - %(levelname)s - '
        '[%(filename)s:%(lineno)d] - %(message)s'
    )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if outputting to console."""
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f'{color}{record.levelname}{reset}'
        
        formatter = logging.Formatter(self.FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


class LoggerManager:
    """
    Manages application logging.
    
    Features:
    - Structured JSON logging
    - Rotating file handlers
    - Console output with colors
    - Separate error log
    - Crash reporting
    """
    
    def __init__(self, log_dir: str = "logs", log_format: str = "json"):
        """
        Initialize LoggerManager.
        
        Args:
            log_dir: Directory for log files
            log_format: "json" or "standard"
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_format = log_format
        self._configured_loggers: set = set()
    
    def get_logger(self, name: str, level: str = "INFO") -> logging.Logger:
        """
        Get or create a configured logger.
        
        Args:
            name: Logger name (typically __name__)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Only configure once per logger
        if name in self._configured_loggers:
            return logger
        
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Remove existing handlers to avoid duplication
        logger.handlers = []
        
        # Add console handler
        self._add_console_handler(logger, level)
        
        # Add file handlers
        self._add_file_handlers(logger, name, level)
        
        self._configured_loggers.add(name)
        
        return logger
    
    def _add_console_handler(self, logger: logging.Logger, level: str):
        """Add console handler with appropriate formatter."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        if self.log_format == "json":
            formatter = JSONFormatter('%(message)s')
        else:
            formatter = StandardFormatter()
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _add_file_handlers(self, logger: logging.Logger, name: str, level: str):
        """Add rotating file handlers."""
        # Main log file
        log_file = self.log_dir / f"{name.replace('.', '_')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        if self.log_format == "json":
            formatter = JSONFormatter('%(message)s')
        else:
            formatter = StandardFormatter()
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log (only ERROR and CRITICAL)
        error_log_file = self.log_dir / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    def log_startup(self, logger: logging.Logger, version: str, config_summary: Dict[str, Any]):
        """Log application startup."""
        logger.info("=" * 80)
        logger.info(f"Application Startup - Version {version}")
        logger.info("=" * 80)
        
        for key, value in config_summary.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("=" * 80)
    
    def log_shutdown(self, logger: logging.Logger):
        """Log application shutdown."""
        logger.info("=" * 80)
        logger.info("Application Shutdown")
        logger.info("=" * 80)
    
    def log_crash(self, logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log application crash with context."""
        logger.critical("=" * 80)
        logger.critical("CRITICAL ERROR - APPLICATION CRASH")
        logger.critical("=" * 80)
        logger.critical(f"Error Type: {type(error).__name__}")
        logger.critical(f"Error Message: {str(error)}")
        
        if context:
            for key, value in context.items():
                logger.critical(f"Context - {key}: {value}")
        
        logger.exception("Full traceback:")
        logger.critical("=" * 80)


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None


def initialize_logging(log_dir: str = "logs", log_format: str = "json") -> LoggerManager:
    """Initialize global logging system."""
    global _logger_manager
    _logger_manager = LoggerManager(log_dir, log_format)
    return _logger_manager


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get a configured logger."""
    global _logger_manager
    if _logger_manager is None:
        initialize_logging()
    
    return _logger_manager.get_logger(name, level)


def get_logger_manager() -> LoggerManager:
    """Get the logger manager instance."""
    global _logger_manager
    if _logger_manager is None:
        initialize_logging()
    
    return _logger_manager
