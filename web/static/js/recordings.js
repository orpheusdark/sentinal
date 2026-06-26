// Recordings Page JavaScript

class RecordingsPage {
    constructor() {
        this.daysFilter = 7;
        this.cameraFilter = '';
        this.recordings = [];
        
        this.init();
    }

    async init() {
        console.log('Initializing recordings page...');
        
        // Setup event listeners
        document.getElementById('daysFilter').addEventListener('change', (e) => {
            this.daysFilter = parseInt(e.target.value);
            this.loadRecordings();
        });

        document.getElementById('cameraFilter').addEventListener('change', (e) => {
            this.cameraFilter = e.target.value;
            this.loadRecordings();
        });

        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadRecordings();
        });

        // Load recordings
        await this.loadRecordings();
        
        console.log('Recordings page ready');
    }

    async loadRecordings() {
        try {
            let url = `/api/recordings?days=${this.daysFilter}`;
            if (this.cameraFilter) {
                url += `&camera_id=${this.cameraFilter}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.recordings = data.data.recordings;
                this.displayRecordings();
            }
        } catch (error) {
            console.error('Error loading recordings:', error);
        }
    }

    displayRecordings() {
        const recordingsList = document.getElementById('recordingsList');

        if (this.recordings.length === 0) {
            recordingsList.innerHTML = '<div class="empty-state">No recordings found</div>';
            return;
        }

        recordingsList.innerHTML = this.recordings.map(rec => this.formatRecordingCard(rec)).join('');

        // Add download event listeners
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const recordingId = e.target.dataset.id;
                this.downloadRecording(recordingId);
            });
        });
    }

    formatRecordingCard(recording) {
        const startTime = new Date(recording.start_time).toLocaleString();
        const endTime = recording.end_time ? new Date(recording.end_time).toLocaleString() : 'N/A';
        const duration = recording.duration_seconds ? recording.duration_seconds.toFixed(1) + ' s' : 'N/A';
        const fileSize = recording.file_size_bytes ? 
            (recording.file_size_bytes / (1024 * 1024)).toFixed(1) + ' MB' : 'N/A';

        return `
            <div class="recording-card">
                <div class="recording-header">
                    <div class="recording-title">Camera ${recording.camera_id}</div>
                    <div class="recording-meta">${startTime}</div>
                </div>
                <div class="recording-body">
                    <div class="recording-detail">
                        <span class="recording-label">Duration:</span>
                        <span class="recording-value">${duration}</span>
                    </div>
                    <div class="recording-detail">
                        <span class="recording-label">File Size:</span>
                        <span class="recording-value">${fileSize}</span>
                    </div>
                    <div class="recording-detail">
                        <span class="recording-label">Quality:</span>
                        <span class="recording-value">${recording.quality || 'medium'}</span>
                    </div>
                    <div class="recording-detail">
                        <span class="recording-label">End Time:</span>
                        <span class="recording-value">${endTime}</span>
                    </div>
                </div>
                <div class="recording-actions">
                    <button class="btn btn-primary btn-sm download-btn" data-id="${recording.id}">Download</button>
                    <button class="btn btn-secondary btn-sm delete-btn" data-id="${recording.id}">Delete</button>
                </div>
            </div>
        `;
    }

    async downloadRecording(recordingId) {
        try {
            window.location.href = `/api/recordings/${recordingId}/download`;
        } catch (error) {
            console.error('Error downloading recording:', error);
            alert('Failed to download recording');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RecordingsPage();
});
