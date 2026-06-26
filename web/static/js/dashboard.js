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
        // Start frame stream
        this.startFrameStream();
        
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

    async startFrameStream() {
        /**Stream live frames and display on canvas*/
        const streamFrame = async () => {
            try {
                const response = await fetch('/api/stream/frame');
                const data = await response.json();

                if (data.success && data.data && data.data.frame) {
                    // Create image from base64
                    const img = new Image();
                    img.onload = () => {
                        try {
                            // Clear canvas first
                            this.ctx.fillStyle = '#000';
                            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                            
                            // Draw image to canvas
                            const scale = Math.min(
                                this.canvas.width / img.width,
                                this.canvas.height / img.height
                            );
                            const x = (this.canvas.width - img.width * scale) / 2;
                            const y = (this.canvas.height - img.height * scale) / 2;
                            
                            this.ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
                            
                            // Update FPS counter
                            this.frameCount++;
                            const now = Date.now();
                            if (now - this.lastFrameTime >= 1000) {
                                this.fps = this.frameCount;
                                this.frameCount = 0;
                                this.lastFrameTime = now;
                                document.getElementById('fps').textContent = this.fps + ' FPS';
                            }
                        } catch (e) {
                            console.error('Error drawing image:', e);
                        }
                    };
                    img.onerror = () => {
                        console.warn('Failed to load frame image');
                    };
                    img.src = 'data:image/jpeg;base64,' + data.data.frame;
                } else if (!data.success) {
                    console.warn('Stream error:', data.error);
                }
            } catch (error) {
                console.warn('Error fetching frame:', error);
            }
            
            // Request next frame with 66ms delay (15 FPS)
            setTimeout(streamFrame, 66);
        };
        
        // Start frame stream
        streamFrame();
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
        
        // Fetch real-time metrics
        try {
            const response = await fetch('/api/system/metrics');
            const data = await response.json();
            
            if (data.success) {
                const metrics = data.data;
                
                // Update CPU
                const cpuUsage = document.getElementById('cpuUsage');
                const cpuBar = document.getElementById('cpuBar');
                if (cpuUsage && cpuBar) {
                    cpuUsage.textContent = Math.round(metrics.cpu_percent) + '%';
                    cpuBar.style.width = metrics.cpu_percent + '%';
                }
                
                // Update Memory
                const memoryUsage = document.getElementById('memoryUsage');
                const memoryBar = document.getElementById('memoryBar');
                if (memoryUsage && memoryBar) {
                    memoryUsage.textContent = Math.round(metrics.memory_percent) + '%';
                    memoryBar.style.width = metrics.memory_percent + '%';
                }
                
                // Update Disk
                const diskUsage = document.getElementById('diskUsage');
                const diskBar = document.getElementById('diskBar');
                if (diskUsage && diskBar) {
                    diskUsage.textContent = Math.round(metrics.disk_percent) + '%';
                    diskBar.style.width = metrics.disk_percent + '%';
                }
            }
        } catch (error) {
            console.error('Error updating metrics:', error);
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
