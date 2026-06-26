"""
Flask Web Server Application

Responsibility: Web interface for surveillance system monitoring and control.
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import get_config
from utils.logger import get_logger
from database.models import get_database


logger = get_logger(__name__)


class WebServer:
    """
    Flask web server for surveillance dashboard.
    
    Features:
    - REST API for camera control and data retrieval
    - WebSocket for live streaming
    - Recording playback
    - System metrics display
    - Configuration management
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """
        Initialize web server.
        
        Args:
            host: Server host address
            port: Server port
            debug: Enable debug mode
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.config = get_config()
        
        # Get absolute paths for templates and static files
        base_dir = Path(__file__).parent  # web/ directory
        template_dir = str(base_dir / 'templates')
        static_dir = str(base_dir / 'static')
        
        # Create Flask app with absolute paths
        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        self.app.config['JSON_SORT_KEYS'] = False
        
        # Enable CORS
        CORS(self.app)
        
        # Application context
        self.app_context = None  # Will be set by main application
        
        # Register routes
        self._register_routes()
        
        logger.info(f"Web server initialized (http://{host}:{port})")
    
    def set_app_context(self, app_context):
        """Set application context for access to managers."""
        self.app_context = app_context
    
    def _register_routes(self):
        """Register all web routes."""
        
        # Dashboard pages
        @self.app.route('/')
        def index():
            """Render main dashboard."""
            return render_template('dashboard.html', 
                                 app_name=self.config.app_name,
                                 version=self.config.version)
        
        @self.app.route('/recordings')
        def recordings_page():
            """Render recordings page."""
            return render_template('recordings.html',
                                 app_name=self.config.app_name)
        
        @self.app.route('/settings')
        def settings_page():
            """Render settings page."""
            return render_template('settings.html',
                                 app_name=self.config.app_name)
        
        # API: System Info
        @self.app.route('/api/system/info')
        def api_system_info():
            """Get system information."""
            try:
                from utils.system import SystemInfo
                system_info = SystemInfo.get_system_info()
                return jsonify({
                    'success': True,
                    'data': system_info
                })
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Health Status
        @self.app.route('/api/system/health')
        def api_system_health():
            """Get system health status."""
            try:
                if not self.app_context:
                    return jsonify({'success': False, 'error': 'App context not set'}), 500
                
                camera_healthy = self.app_context.camera_manager.health_status if self.app_context.camera_manager else False
                
                from utils.system import ResourceMonitor
                healthy, health_status = ResourceMonitor.full_health_check()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'overall_healthy': healthy,
                        'details': health_status,
                        'camera_connected': camera_healthy,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error getting health status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Disk Usage
        @self.app.route('/api/system/disk')
        def api_system_disk():
            """Get disk usage information."""
            try:
                if not self.app_context or not self.app_context.storage_manager:
                    return jsonify({'success': False, 'error': 'Storage manager not available'}), 500
                
                disk_health = self.app_context.storage_manager.check_disk_health()
                storage_info = self.app_context.storage_manager.get_storage_info()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'disk_health': disk_health,
                        'storage_info': storage_info
                    }
                })
            except Exception as e:
                logger.error(f"Error getting disk info: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Recording List
        @self.app.route('/api/recordings')
        def api_recordings():
            """Get list of recordings."""
            try:
                if not self.app_context or not self.app_context.db:
                    return jsonify({'success': False, 'error': 'Database not available'}), 500
                
                # Query recordings from database
                session = self.app_context.db.get_session()
                from database.models import Recording
                
                # Get query parameters
                camera_id = request.args.get('camera_id', type=int)
                days = request.args.get('days', default=7, type=int)
                
                # Build query
                query = session.query(Recording)
                if camera_id:
                    query = query.filter(Recording.camera_id == camera_id)
                
                # Filter by date
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Recording.start_time >= cutoff_date)
                
                # Order by date
                recordings = query.order_by(Recording.start_time.desc()).all()
                
                # Convert to dict
                recording_list = []
                for rec in recordings:
                    recording_list.append({
                        'id': rec.id,
                        'camera_id': rec.camera_id,
                        'video_path': rec.video_path,
                        'start_time': rec.start_time.isoformat() if rec.start_time else None,
                        'end_time': rec.end_time.isoformat() if rec.end_time else None,
                        'duration_seconds': rec.duration_seconds,
                        'file_size_bytes': rec.file_size_bytes,
                        'quality': rec.quality,
                    })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'recordings': recording_list,
                        'count': len(recording_list),
                    }
                })
            except Exception as e:
                logger.error(f"Error getting recordings: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Motion Events
        @self.app.route('/api/motion-events')
        def api_motion_events():
            """Get recent motion events."""
            try:
                if not self.app_context or not self.app_context.db:
                    return jsonify({'success': False, 'error': 'Database not available'}), 500
                
                session = self.app_context.db.get_session()
                from database.models import MotionEvent
                
                # Get query parameters
                camera_id = request.args.get('camera_id', type=int)
                hours = request.args.get('hours', default=24, type=int)
                
                # Build query
                query = session.query(MotionEvent)
                if camera_id:
                    query = query.filter(MotionEvent.camera_id == camera_id)
                
                # Filter by date
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                query = query.filter(MotionEvent.start_time >= cutoff_time)
                
                # Order by date
                events = query.order_by(MotionEvent.start_time.desc()).limit(100).all()
                
                # Convert to dict
                event_list = []
                for evt in events:
                    duration = None
                    if evt.end_time:
                        duration = (evt.end_time - evt.start_time).total_seconds()
                    
                    event_list.append({
                        'id': evt.id,
                        'camera_id': evt.camera_id,
                        'start_time': evt.start_time.isoformat() if evt.start_time else None,
                        'end_time': evt.end_time.isoformat() if evt.end_time else None,
                        'duration_seconds': duration,
                        'contour_count': evt.contour_count,
                        'max_contour_area': evt.max_contour_area,
                    })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'events': event_list,
                        'count': len(event_list),
                    }
                })
            except Exception as e:
                logger.error(f"Error getting motion events: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Camera Status
        @self.app.route('/api/cameras')
        def api_cameras():
            """Get camera list and status."""
            try:
                if not self.app_context or not self.app_context.camera_manager:
                    return jsonify({'success': False, 'error': 'Camera manager not available'}), 500
                
                cameras = []
                for camera_id, driver in self.app_context.camera_manager.cameras.items():
                    status = driver.get_status()
                    cameras.append({
                        'id': camera_id,
                        'connected': driver.is_alive(),
                        'status': status
                    })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'cameras': cameras,
                        'count': len(cameras)
                    }
                })
            except Exception as e:
                logger.error(f"Error getting cameras: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Configuration
        @self.app.route('/api/config')
        def api_config():
            """Get current configuration."""
            try:
                config = get_config()
                return jsonify({
                    'success': True,
                    'data': {
                        'app_name': config.app_name,
                        'version': config.version,
                        'camera': {
                            'fps': config.camera.fps,
                            'resolution': config.camera.resolution,
                        },
                        'motion': {
                            'sensitivity': config.motion.sensitivity,
                            'min_contour_area': config.motion.min_contour_area,
                        },
                        'recording': {
                            'enabled': config.recording.enabled,
                            'quality': config.recording.quality,
                        },
                        'storage': {
                            'retention_days': config.storage.retention_days,
                        }
                    }
                })
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Recording Download
        @self.app.route('/api/recordings/<int:recording_id>/download')
        def api_recording_download(recording_id):
            """Download a recording file."""
            try:
                if not self.app_context or not self.app_context.db:
                    return jsonify({'success': False, 'error': 'Database not available'}), 500
                
                session = self.app_context.db.get_session()
                from database.models import Recording
                
                recording = session.query(Recording).filter(Recording.id == recording_id).first()
                if not recording:
                    return jsonify({'success': False, 'error': 'Recording not found'}), 404
                
                if not os.path.exists(recording.video_path):
                    return jsonify({'success': False, 'error': 'Video file not found'}), 404
                
                # Stream file for download
                return send_file(
                    recording.video_path,
                    as_attachment=True,
                    download_name=os.path.basename(recording.video_path)
                )
            except Exception as e:
                logger.error(f"Error downloading recording: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # Health check endpoint
        @self.app.route('/api/health')
        def api_health():
            """Health check endpoint."""
            return jsonify({
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'success': False,
                'error': 'Not found'
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500
    
    def run(self, threaded: bool = True):
        """
        Start web server.
        
        Args:
            threaded: Run in threaded mode
        """
        logger.info(f"Starting web server on http://{self.host}:{self.port}")
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            threaded=threaded,
            use_reloader=False
        )
