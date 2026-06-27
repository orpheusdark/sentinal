"""
Flask Web Server Application

Responsibility: Web interface for surveillance system monitoring and control.
"""

import hmac
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
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
        self.auth_enabled = getattr(self.config.security, 'enable_auth', False)
        self.admin_username = getattr(self.config.security, 'admin_username', 'admin')
        self.admin_password = getattr(self.config.security, 'admin_password', 'sentinel')
        self.session_timeout_minutes = getattr(self.config.security, 'session_timeout_minutes', 60)
        self.max_login_attempts = getattr(self.config.security, 'max_login_attempts', 5)
        self.lockout_duration_minutes = getattr(self.config.security, 'lockout_duration_minutes', 15)
        self.require_api_key = getattr(self.config.security, 'require_api_key', False)
        self.api_key = getattr(self.config.security, 'api_key', None)
        self.failed_login_attempts = 0
        self.lockout_until = None
        
        # Use absolute folders for web templates and static assets.
        base_dir = Path(__file__).parent  # web/ directory
        template_dir = str(base_dir / 'templates')
        static_dir = str(base_dir / 'static')

        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.secret_key = getattr(self.config.security, 'session_secret', None) or f"{self.config.app_name}:{self.config.version}"
        self.app.permanent_session_lifetime = timedelta(minutes=self.session_timeout_minutes)
        
        # Enable CORS
        CORS(self.app)
        
        # Application context
        self.app_context = None  # Will be set by main application
        
        # Register routes
        self.app.before_request(self._enforce_access_control)
        self.app.context_processor(self._inject_template_context)
        self._register_routes()
        
        logger.info(f"Web server initialized (http://{host}:{port})")
    
    def set_app_context(self, app_context):
        """Set application context for access to managers."""
        self.app_context = app_context

    def _inject_template_context(self):
        """Expose auth state to all templates."""
        return {
            'authenticated': self._is_authenticated(),
            'username': session.get('username'),
            'auth_enabled': self.auth_enabled,
        }

    def _is_authenticated(self) -> bool:
        """Check whether the current session is authenticated."""
        if not self.auth_enabled:
            return True

        return bool(session.get('authenticated'))

    def _is_public_path(self, path: str) -> bool:
        """Return True for routes that should remain publicly accessible."""
        public_paths = {
            '/login',
            '/logout',
            '/api/health',
            '/api/system/health',
            '/api/system/info',
        }
        return path in public_paths or path.startswith('/static/')

    def _enforce_access_control(self):
        """Protect dashboard routes and sensitive API endpoints."""
        if not self.auth_enabled:
            return self._enforce_api_key()

        if self._is_public_path(request.path):
            return self._enforce_api_key()

        if self._is_authenticated():
            return self._enforce_api_key()

        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        return redirect(url_for('login', next=request.full_path if request.full_path else '/'))

    def _enforce_api_key(self):
        """Protect mutating API routes when API key enforcement is enabled."""
        if not self.require_api_key or not self.api_key:
            return None

        if not request.path.startswith('/api/'):
            return None

        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return None

        provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if provided_key != self.api_key:
            return jsonify({
                'success': False,
                'error': 'API key required'
            }), 401

        return None

    def _verify_credentials(self, username: str, password: str) -> bool:
        """Validate submitted credentials using constant-time comparison."""
        return hmac.compare_digest(username or '', self.admin_username) and hmac.compare_digest(password or '', self.admin_password)

    def _is_locked_out(self) -> bool:
        """Check whether login attempts are temporarily locked out."""
        if self.lockout_until is None:
            return False

        if datetime.utcnow() >= self.lockout_until:
            self.lockout_until = None
            self.failed_login_attempts = 0
            return False

        return True
    
    def _register_routes(self):
        """Register all web routes."""
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Render and process the login form."""
            if not self.auth_enabled:
                return redirect(url_for('index'))

            if self._is_authenticated():
                return redirect(url_for('index'))

            error = None
            next_url = request.values.get('next') or url_for('index')

            if request.method == 'POST':
                if self._is_locked_out():
                    error = 'Too many failed attempts. Try again later.'
                else:
                    username = request.form.get('username', '').strip()
                    password = request.form.get('password', '')

                    if self._verify_credentials(username, password):
                        session.clear()
                        session.permanent = True
                        session['authenticated'] = True
                        session['username'] = username
                        session['login_time'] = datetime.utcnow().isoformat()
                        self.failed_login_attempts = 0
                        self.lockout_until = None
                        return redirect(next_url)

                    self.failed_login_attempts += 1
                    if self.failed_login_attempts >= self.max_login_attempts:
                        self.lockout_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
                        error = f'Login locked for {self.lockout_duration_minutes} minutes after repeated failures.'
                    else:
                        error = 'Invalid username or password.'

            return render_template(
                'login.html',
                app_name=self.config.app_name,
                version=self.config.version,
                error=error,
                next_url=next_url,
                locked_out=self._is_locked_out(),
            )

        @self.app.route('/logout')
        def logout():
            """Clear the current session and return to the login page."""
            session.clear()
            return redirect(url_for('login'))

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
        
        # API: System Metrics
        @self.app.route('/api/system/metrics')
        def api_system_metrics():
            """Get real-time system metrics."""
            try:
                import psutil
                import shutil
                
                mem = psutil.virtual_memory()
                disk = shutil.disk_usage('/')
                
                return jsonify({
                    'success': True,
                    'data': {
                        'cpu_percent': psutil.cpu_percent(interval=0.1),
                        'memory_percent': mem.percent,
                        'memory_used_mb': mem.used / (1024**2),
                        'memory_available_mb': mem.available / (1024**2),
                        'disk_percent': (disk.used / disk.total) * 100,
                        'disk_used_gb': disk.used / (1024**3),
                        'disk_total_gb': disk.total / (1024**3),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
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

        @self.app.route('/api/auth/status')
        def api_auth_status():
            """Report the current authentication state."""
            return jsonify({
                'success': True,
                'data': {
                    'auth_enabled': self.auth_enabled,
                    'authenticated': self._is_authenticated(),
                    'username': session.get('username'),
                }
            })
        
        # API: Health Status
        @self.app.route('/api/system/health')
        def api_system_health():
            """Get system health status."""
            try:
                if not self.app_context:
                    return jsonify({'success': False, 'error': 'App context not set'}), 500
                
                camera_healthy = False
                if self.app_context.camera_manager:
                    camera_status = self.app_context.camera_manager.get_status()
                    camera_healthy = any(
                        camera.get('connected', False) and camera.get('alive', False)
                        for camera in camera_status.values()
                    )
                
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
        
        # API: Recording Status
        @self.app.route('/api/recording/status')
        def api_recording_status():
            """Get current recording status."""
            try:
                if not self.app_context or not self.app_context.recording_manager:
                    return jsonify({
                        'success': False,
                        'error': 'Recording manager not available'
                    }), 500
                
                is_recording = self.app_context.recording_manager.is_recording
                current_video = self.app_context.recording_manager.current_video_path
                
                return jsonify({
                    'success': True,
                    'data': {
                        'is_recording': is_recording,
                        'current_video': current_video,
                        'status': 'Recording' if is_recording else 'Stopped'
                    }
                })
            except Exception as e:
                logger.error(f"Error getting recording status: {e}")
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
                        'filepath': rec.filepath,
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

        @self.app.route('/api/analytics')
        def api_analytics():
            """Get system analytics and summary statistics."""
            try:
                if not self.app_context or not self.app_context.db:
                    return jsonify({'success': False, 'error': 'Database not available'}), 500

                session = self.app_context.db.get_session()
                from database.models import Camera, Recording, MotionEvent

                camera_count = session.query(Camera).count()
                total_recordings = session.query(Recording).count()
                total_motion_events = session.query(MotionEvent).count()
                recordings_last_week = session.query(Recording).filter(
                    Recording.start_time >= datetime.utcnow() - timedelta(days=7)
                ).count()
                motion_events_last_24h = session.query(MotionEvent).filter(
                    MotionEvent.start_time >= datetime.utcnow() - timedelta(hours=24)
                ).count()

                camera_summaries = []
                for camera in session.query(Camera).order_by(Camera.id).all():
                    recording_count = session.query(Recording).filter(Recording.camera_id == camera.id).count()
                    motion_count = session.query(MotionEvent).filter(MotionEvent.camera_id == camera.id).count()
                    camera_summaries.append({
                        'camera_id': camera.id,
                        'name': camera.name,
                        'enabled': camera.enabled,
                        'connection_status': camera.connection_status,
                        'recording_count': recording_count,
                        'motion_event_count': motion_count,
                    })

                total_size_bytes = session.query(Recording.file_size_bytes).filter(Recording.file_size_bytes.isnot(None)).all()
                session.close()
                recording_size_bytes = sum(r[0] or 0 for r in total_size_bytes)

                return jsonify({
                    'success': True,
                    'data': {
                        'totals': {
                            'camera_count': camera_count,
                            'recording_count': total_recordings,
                            'motion_event_count': total_motion_events,
                            'recordings_last_week': recordings_last_week,
                            'motion_events_last_24h': motion_events_last_24h,
                            'recording_size_gb': recording_size_bytes / (1024 ** 3),
                        },
                        'cameras': camera_summaries,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error getting analytics: {e}")
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
                
                if not os.path.exists(recording.filepath):
                    return jsonify({'success': False, 'error': 'Video file not found'}), 404
                
                # Stream file for download
                return send_file(
                    recording.filepath,
                    as_attachment=True,
                    download_name=os.path.basename(recording.video_path)
                )
            except Exception as e:
                logger.error(f"Error downloading recording: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # API: Live Frame Stream
        @self.app.route('/api/stream/frame')
        def api_stream_frame():
            """Get current frame as JPEG."""
            try:
                if not self.app_context or not self.app_context.stream_manager:
                    return jsonify({'success': False, 'error': 'Stream manager not available'}), 500
                
                # Get frame as base64 JPEG
                frame_b64 = self.app_context.stream_manager.get_frame_as_jpeg()
                
                if not frame_b64:
                    return jsonify({'success': False, 'error': 'No frame available'}), 404
                
                return jsonify({
                    'success': True,
                    'data': {
                        'frame': frame_b64,
                        'timestamp': datetime.utcnow().isoformat(),
                        'quality': self.app_context.stream_manager.quality,
                        'fps': self.app_context.stream_manager.target_fps,
                    }
                })
            except Exception as e:
                logger.error(f"Error getting stream frame: {e}")
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
    
    def run(self, threaded: bool = True, ssl_context=None):
        """
        Start web server.
        
        Args:
            threaded: Run in threaded mode
            ssl_context: SSL context tuple or object for HTTPS
        """
        scheme = 'https' if ssl_context else 'http'
        logger.info(f"Starting web server on {scheme}://{self.host}:{self.port}")
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            threaded=threaded,
            use_reloader=False,
            ssl_context=ssl_context
        )
