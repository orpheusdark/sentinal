"""
Web Server Tests

Tests for Flask app, API endpoints, and WebSocket streaming
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta

from web.server import WebServer
from web.stream import StreamManager
import numpy as np


class TestStreamManager:
    """Test StreamManager for video streaming."""
    
    def test_stream_manager_initialization(self):
        """Test stream manager creation."""
        manager = StreamManager(quality=75, target_fps=15)
        assert manager.quality == 75
        assert manager.target_fps == 15
        assert manager.get_connected_clients() == 0
    
    def test_register_client(self):
        """Test registering a client."""
        manager = StreamManager()
        manager.register_client('client1')
        assert manager.get_connected_clients() == 1
        
        manager.register_client('client2')
        assert manager.get_connected_clients() == 2
    
    def test_unregister_client(self):
        """Test unregistering a client."""
        manager = StreamManager()
        manager.register_client('client1')
        manager.register_client('client2')
        
        manager.unregister_client('client1')
        assert manager.get_connected_clients() == 1
        
        manager.unregister_client('client2')
        assert manager.get_connected_clients() == 0
    
    def test_frame_update(self):
        """Test updating current frame."""
        manager = StreamManager()
        
        # Create test frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        manager.update_frame(frame)
        
        # Check frame info
        info = manager.get_frame_info()
        assert info['has_frame'] is True
        assert info['width'] == 1280
        assert info['height'] == 720
    
    def test_get_frame_as_jpeg(self):
        """Test JPEG encoding."""
        manager = StreamManager()
        
        # Create test frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        manager.update_frame(frame)
        
        # Get JPEG
        jpeg_base64 = manager.get_frame_as_jpeg()
        assert jpeg_base64 is not None
        assert len(jpeg_base64) > 0
    
    def test_quality_setting(self):
        """Test changing quality."""
        manager = StreamManager(quality=50)
        assert manager.quality == 50
        
        manager.set_quality(90)
        assert manager.quality == 90
        
        # Invalid quality should not change
        manager.set_quality(150)
        assert manager.quality == 90  # Unchanged
    
    def test_fps_setting(self):
        """Test changing FPS."""
        manager = StreamManager(target_fps=15)
        assert manager.target_fps == 15
        
        manager.set_fps(30)
        assert manager.target_fps == 30
        assert manager.frame_interval == 1.0 / 30
    
    def test_get_status(self):
        """Test getting stream status."""
        manager = StreamManager()
        manager.register_client('client1')
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        manager.update_frame(frame)
        
        status = manager.get_status()
        assert status['connected_clients'] == 1
        assert status['quality'] == 70
        assert status['target_fps'] == 15
        assert status['frame_info']['has_frame'] is True


class TestWebServer:
    """Test Flask web server."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        server = WebServer(debug=True)
        server.app.config['TESTING'] = True
        return server.app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_server_initialization(self):
        """Test web server creation."""
        server = WebServer(host='localhost', port=8000)
        assert server.host == 'localhost'
        assert server.port == 8000
        assert server.app is not None
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'healthy'
    
    def test_index_route(self, client):
        """Test index route renders dashboard."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Live Stream' in response.data or b'dashboard' in response.data.lower()
    
    def test_recordings_route(self, client):
        """Test recordings page route."""
        response = client.get('/recordings')
        assert response.status_code == 200
        assert b'Recordings' in response.data
    
    def test_settings_route(self, client):
        """Test settings page route."""
        response = client.get('/settings')
        assert response.status_code == 200
        assert b'Settings' in response.data
    
    def test_config_api_endpoint(self, client):
        """Test configuration API endpoint."""
        response = client.get('/api/config')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert 'app_name' in data['data']
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_api_response_format(self, client):
        """Test API response format."""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check standard response format
        assert 'success' in data
        assert isinstance(data['success'], bool)


class TestWebServerIntegration:
    """Integration tests for web server."""
    
    def test_app_context_setting(self):
        """Test setting application context."""
        server = WebServer()
        
        # Create mock context
        class MockContext:
            def __init__(self):
                self.db = None
                self.camera_manager = None
        
        context = MockContext()
        server.set_app_context(context)
        assert server.app_context == context
    
    def test_static_files_exist(self):
        """Test that static files are configured."""
        server = WebServer()
        assert server.app.static_folder == 'web/static'
    
    def test_template_files_exist(self):
        """Test that template folder is configured."""
        server = WebServer()
        assert server.app.template_folder == 'web/templates'


class TestStreamManagerPerformance:
    """Performance tests for stream manager."""
    
    def test_frame_encoding_speed(self):
        """Test JPEG encoding performance."""
        manager = StreamManager(quality=70)
        
        # Create large frame
        frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
        manager.update_frame(frame)
        
        # Time encoding
        import time
        start = time.time()
        for _ in range(10):
            jpeg = manager.get_frame_as_jpeg()
        elapsed = time.time() - start
        
        # Should encode 10 frames in less than 1 second
        assert elapsed < 1.0
        assert jpeg is not None
    
    def test_client_registration_scalability(self):
        """Test handling many connected clients."""
        manager = StreamManager()
        
        # Register many clients
        for i in range(100):
            manager.register_client(f'client_{i}')
        
        assert manager.get_connected_clients() == 100
        
        # Unregister all
        for i in range(100):
            manager.unregister_client(f'client_{i}')
        
        assert manager.get_connected_clients() == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
