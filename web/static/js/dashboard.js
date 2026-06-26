// Dashboard JavaScript
// Real-time updates and API interaction

class Dashboard {
    constructor() {
        this.canvas = document.getElementById('liveCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.frameCount = 0;
        this.lastFrameTime = Date.now();
        this.fps = 0;
        this.refreshInterval = 5000; // 5 seconds
        
        this.init();
    }

    async init() {
        console.log('Initializing dashboard...');
        
        // Set canvas size
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        // Start real-time updates
        this.startUpdates();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('Dashboard ready');
    }

    resizeCanvas() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = (this.canvas.width * 9) / 16; // 16:9 aspect ratio
    }

    setupEventListeners() {
        document.getElementById('qualityBtn').addEventListener('click', () => this.showQualityOptions());
        document.getElementById('fpsBtn').addEventListener('click', () => this.showFpsOptions());
    }

    async startUpdates() {
        // Update system info
        await this.updateSystemHealth();
        await this.updateDiskUsage();
        await this.updateMotionEvents();
        await this.updateRecordings();
        await this.updateCameras();

        // Set intervals for continuous updates
        setInterval(() => this.updateSystemHealth(), this.refreshInterval);
        setInterval(() => this.updateDiskUsage(), this.refreshInterval);
        setInterval(() => this.updateMotionEvents(), this.refreshInterval * 2);
        setInterval(() => this.updateRecordings(), this.refreshInterval * 3);
        setInterval(() => this.updateCameras(), this.refreshInterval);
    }

    async updateSystemHealth() {
        try {
            const response = await fetch('/api/system/health');
            const data = await response.json();

            if (data.success) {
                // Update camera status
                const cameraStatus = document.getElementById('cameraStatus');
                if (data.data.camera_connected) {
                    cameraStatus.className = 'status-badge status-connected';
                    cameraStatus.querySelector('.status-text').textContent = 'Connected';
                } else {
                    cameraStatus.className = 'status-badge status-disconnected';
                    cameraStatus.querySelector('.status-text').textContent = 'Disconnected';
                }

                // Update recording status (placeholder)
                const recordingStatus = document.getElementById('recordingStatus');
                recordingStatus.className = 'status-badge status-stopped';
                recordingStatus.querySelector('.status-text').textContent = 'Stopped';
            }
        } catch (error) {
            console.error('Error updating health:', error);
        }
    }

    async updateDiskUsage() {
        try {
            const response = await fetch('/api/system/disk');
            const data = await response.json();

            if (data.success) {
                const diskHealth = data.data.disk_health;
                const diskProgress = document.getElementById('diskProgress');
                const diskText = document.getElementById('diskText');
                const diskUsage = document.getElementById('diskUsage');
                const diskBar = document.getElementById('diskBar');

                const usagePercent = diskHealth.used_percent;
                diskProgress.style.width = usagePercent + '%';
                diskText.textContent = Math.round(usagePercent) + '%';
                diskUsage.textContent = Math.round(usagePercent) + '%';
                diskBar.style.width = usagePercent + '%';

                // Update color based on status
                if (diskHealth.status === 'critical') {
                    diskBar.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
                } else if (diskHealth.status === 'warning') {
                    diskBar.style.background = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
                } else {
                    diskBar.style.background = 'linear-gradient(90deg, #0891b2 0%, #06b6d4 100%)';
                }
            }
        } catch (error) {
            console.error('Error updating disk usage:', error);
        }
    }

    async updateMotionEvents() {
        try {
            const response = await fetch('/api/motion-events?hours=24');
            const data = await response.json();

            if (data.success) {
                document.getElementById('motionCount').textContent = data.data.count;

                // Update events list
                const eventsList = document.getElementById('eventsList');
                if (data.data.events.length === 0) {
                    eventsList.innerHTML = '<div class="empty-state">No motion events detected in the last 24 hours</div>';
                } else {
                    eventsList.innerHTML = data.data.events.slice(0, 10).map(event => this.formatEventItem(event)).join('');
                }
            }
        } catch (error) {
            console.error('Error updating motion events:', error);
        }
    }

    formatEventItem(event) {
        const startTime = new Date(event.start_time).toLocaleString();
        const duration = event.duration_seconds ? event.duration_seconds.toFixed(1) + 's' : 'ongoing';

        return `
            <div class="event-item">
                <div>
                    <div class="event-time">${startTime}</div>
                    <div class="event-duration">Duration: ${duration} | Contours: ${event.contour_count}</div>
                </div>
            </div>
        `;
    }

    async updateRecordings() {
        try {
            const response = await fetch('/api/recordings?days=7');
            const data = await response.json();

            if (data.success) {
                document.getElementById('recordingCount').textContent = data.data.count;
                
                // Calculate total size
                let totalSize = 0;
                data.data.recordings.forEach(rec => {
                    if (rec.file_size_bytes) {
                        totalSize += rec.file_size_bytes;
                    }
                });
                
                const sizeMB = (totalSize / (1024 * 1024)).toFixed(1);
                document.getElementById('recordingSize').textContent = sizeMB + ' MB';
            }
        } catch (error) {
            console.error('Error updating recordings:', error);
        }
    }

    async updateCameras() {
        try {
            const response = await fetch('/api/cameras');
            const data = await response.json();

            if (data.success && data.data.cameras.length > 0) {
                const camera = data.data.cameras[0]; // Show first camera
                const cameraStatus = document.getElementById('cameraStatus');
                
                if (camera.connected) {
                    cameraStatus.className = 'status-badge status-connected';
                    cameraStatus.querySelector('.status-text').textContent = 'Connected';
                } else {
                    cameraStatus.className = 'status-badge status-disconnected';
                    cameraStatus.querySelector('.status-text').textContent = 'Disconnected';
                }
            }
        } catch (error) {
            console.error('Error updating cameras:', error);
        }
    }

    showQualityOptions() {
        const quality = prompt('Select quality (low/medium/high):', 'medium');
        if (quality) {
            // TODO: Send to server
            const qualityMap = { 'low': 'Low', 'medium': 'Medium', 'high': 'High' };
            document.getElementById('qualityBtn').textContent = 'Quality: ' + (qualityMap[quality] || 'Medium');
        }
    }

    showFpsOptions() {
        const fps = prompt('Enter FPS (1-30):', '15');
        if (fps) {
            // TODO: Send to server
            document.getElementById('fpsBtn').textContent = 'FPS: ' + fps;
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
