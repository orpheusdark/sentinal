// Settings Page JavaScript

class SettingsPage {
    constructor() {
        this.config = {};
        
        this.init();
    }

    async init() {
        console.log('Initializing settings page...');
        
        // Load current configuration
        await this.loadConfig();
        
        // Setup event listeners
        document.getElementById('sensitivityValue').textContent = document.getElementById('motionSensitivity').value;
        document.getElementById('motionSensitivity').addEventListener('input', (e) => {
            document.getElementById('sensitivityValue').textContent = e.target.value;
        });

        document.getElementById('saveBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('restoreBtn').addEventListener('click', () => this.restoreDefaults());

        console.log('Settings page ready');
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();

            if (data.success) {
                this.config = data.data;
                this.populateForm();
            }
        } catch (error) {
            this.showMessage('Unable to load configuration. Check your connection.', 'error');
            document.getElementById('saveBtn').disabled = true;
        }
    }

    populateForm() {
        // Camera settings
        document.getElementById('cameraFps').value = this.config.camera?.fps || 15;
        document.getElementById('cameraResolution').value = this.config.camera?.resolution || '720p';

        // Motion settings
        document.getElementById('motionSensitivity').value = this.config.motion?.sensitivity ?? 30;
        document.getElementById('sensitivityValue').textContent = this.config.motion?.sensitivity ?? 30;
        document.getElementById('minContourArea').value = this.config.motion?.min_contour_area || 500;

        // Recording settings
        document.getElementById('recordingEnabled').checked = this.config.recording?.enabled ?? true;
        document.getElementById('recordingQuality').value = this.config.recording?.quality || 'medium';
        document.getElementById('postMotionSeconds').value = this.config.recording?.post_motion_seconds ?? 10;

        // Storage settings
        document.getElementById('retentionDays').value = this.config.storage?.retention_days || 30;
        document.getElementById('criticalDiskPercent').value = this.config.storage?.critical_disk_percent || 95;
        document.getElementById('targetFreePercent').value = this.config.storage?.target_free_percent || 60;
    }

    async saveSettings() {
        try {
            const settings = {
                camera: {
                    fps: parseInt(document.getElementById('cameraFps').value),
                    resolution: document.getElementById('cameraResolution').value,
                },
                motion: {
                    sensitivity: parseInt(document.getElementById('motionSensitivity').value),
                    min_contour_area: parseInt(document.getElementById('minContourArea').value),
                },
                recording: {
                    enabled: document.getElementById('recordingEnabled').checked,
                    quality: document.getElementById('recordingQuality').value,
                    post_motion_seconds: parseInt(document.getElementById('postMotionSeconds').value),
                },
                storage: {
                    retention_days: parseInt(document.getElementById('retentionDays').value),
                    critical_disk_percent: parseInt(document.getElementById('criticalDiskPercent').value),
                    target_free_percent: parseInt(document.getElementById('targetFreePercent').value),
                },
            };

            if (![...document.querySelectorAll('form')].every(form => form.reportValidity())) return;
            const response = await fetch('/api/config', {
                method: 'PUT', headers: {'Content-Type': 'application/json', 'X-Sentinel-Request': 'dashboard'},
                body: JSON.stringify(settings), signal: AbortSignal.timeout(8000)
            });
            const result = await response.json();
            if (!response.ok || !result.success) throw new Error(result.error || 'Unable to save');
            this.showMessage(result.message, 'success');
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showMessage(error.message, 'error');
        }
    }

    async restoreDefaults() {
        if (confirm('Are you sure you want to restore default settings?')) {
            // Reset to defaults
            document.getElementById('cameraFps').value = 15;
            document.getElementById('cameraResolution').value = '720p';
            document.getElementById('motionSensitivity').value = 30;
            document.getElementById('sensitivityValue').textContent = 30;
            document.getElementById('minContourArea').value = 300;
            document.getElementById('recordingEnabled').checked = true;
            document.getElementById('recordingQuality').value = 'medium';
            document.getElementById('postMotionSeconds').value = 10;
            document.getElementById('retentionDays').value = 30;
            document.getElementById('criticalDiskPercent').value = 95;
            document.getElementById('targetFreePercent').value = 60;

            this.showMessage('Default values loaded. Save Settings to persist them.', 'success');
        }
    }

    showMessage(text, type) {
        const messageEl = document.getElementById('message');
        messageEl.textContent = text;
        messageEl.className = 'message ' + type;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageEl.className = 'message';
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SettingsPage();
});
