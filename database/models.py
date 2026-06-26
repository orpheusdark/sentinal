"""
Database Layer for Project Sentinel

Responsibility: Database initialization, schema management, and session handling.
Uses SQLite with SQLAlchemy ORM.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Boolean, Text, ForeignKey, Index, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class Application(Base):
    """Application state and metadata."""
    
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False)  # running, crashed, shutdown
    error_message = Column(Text, nullable=True)


class Camera(Base):
    """Camera configuration and status."""
    
    __tablename__ = 'cameras'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    camera_type = Column(String(50), nullable=False)  # builtin, usb, rtsp, etc.
    url = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True)
    
    last_frame_time = Column(DateTime, nullable=True)
    connection_status = Column(String(50), nullable=False, default='disconnected')
    frames_captured = Column(Integer, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MotionEvent(Base):
    """Motion detection events."""
    
    __tablename__ = 'motion_events'
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)
    
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    contour_count = Column(Integer, nullable=False)
    max_contour_area = Column(Integer, nullable=False)
    sensitivity_level = Column(Integer, nullable=False)
    
    false_positive = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_camera_start_time', 'camera_id', 'start_time'),
    )


class Recording(Base):
    """Recording metadata."""
    
    __tablename__ = 'recordings'
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)
    motion_event_id = Column(Integer, ForeignKey('motion_events.id'), nullable=True)
    
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    has_thumbnail = Column(Boolean, default=False)
    thumbnail_path = Column(String(512), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_camera_start_time', 'camera_id', 'start_time'),
        Index('idx_deleted_at', 'deleted_at'),
    )


class SystemMetric(Base):
    """System performance metrics."""
    
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    memory_used_mb = Column(Float, nullable=False)
    memory_available_mb = Column(Float, nullable=False)
    
    disk_used_gb = Column(Float, nullable=False)
    disk_total_gb = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
    )


class ApplicationLog(Base):
    """Application events and errors."""
    
    __tablename__ = 'application_logs'
    
    id = Column(Integer, primary_key=True)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    level = Column(String(50), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    module = Column(String(255), nullable=False)
    
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_level', 'level'),
    )


class Setting(Base):
    """Application settings (key-value store)."""
    
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    """
    Manages SQLite database connections and schema.
    
    Features:
    - Automatic schema creation
    - Connection pooling
    - WAL mode for reliability
    - Session management
    """
    
    def __init__(self, db_path: str = "data/sentinel.db", echo: bool = False):
        """
        Initialize DatabaseManager.
        
        Args:
            db_path: Path to SQLite database file
            echo: Enable SQL query logging
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine(echo)
        self._initialize_schema()
        self._enable_wal()
    
    def _initialize_engine(self, echo: bool):
        """Initialize SQLAlchemy engine."""
        db_url = f"sqlite:///{self.db_path}"
        
        self.engine = create_engine(
            db_url,
            echo=echo,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def _initialize_schema(self):
        """Create all tables and indexes, handling existing schema gracefully."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database schema initialized")
        except Exception as e:
            # Check if it's just an "already exists" error, which is harmless
            error_msg = str(e).lower()
            if "already exists" in error_msg:
                logger.info("Database schema already exists, skipping creation")
            else:
                logger.error(f"Failed to initialize database schema: {e}")
                raise
    
    def _enable_wal(self):
        """Enable Write-Ahead Logging for better concurrency."""
        try:
            with self.get_session() as session:
                session.execute("PRAGMA journal_mode=WAL")
                session.execute("PRAGMA synchronous=NORMAL")
                session.execute("PRAGMA cache_size=10000")
                session.commit()
            logger.info("WAL mode enabled")
        except Exception as e:
            logger.error(f"Failed to enable WAL: {e}")
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def initialize_database(db_path: str = "data/sentinel.db", echo: bool = False) -> DatabaseManager:
    """Initialize global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(db_path, echo)
    return _db_manager


def get_database() -> DatabaseManager:
    """Get global database manager."""
    global _db_manager
    if _db_manager is None:
        initialize_database()
    return _db_manager


def get_db_session() -> Session:
    """Get a database session."""
    return get_database().get_session()
