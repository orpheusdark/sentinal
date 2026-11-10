// Non-overlapping polling; pause when the page is hidden.
class Dashboard {
    constructor() {
        this.canvas = document.getElementById('liveCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.paused = false;
        this.fps = 15;
        this.frames = 0;
        this.frameTime = performance.now();
        document.getElementById('fpsSelect').addEventListener('change', e => this.fps = Number(e.target.value));
        document.getElementById('qualitySelect').addEventListener('change', e => {
            this.canvas.width = Number(e.target.value);
            this.canvas.height = this.canvas.width * 9 / 16;
        });
        document.getElementById('pauseBtn').addEventListener('click', e => {
            this.paused = !this.paused;
            e.target.textContent = this.paused ? 'Resume preview' : 'Pause preview';
            e.target.setAttribute('aria-pressed', String(this.paused));
            this.previewMessage(this.paused ? 'Preview paused' : 'Connecting to camera');
        });
        this.pollTelemetry();
        this.pollFrame();
    }
    async api(path) {
        const response = await fetch(path, {signal: AbortSignal.timeout(8000)});
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || 'Request failed');
        return result.data;
    }
    text(id, value) { document.getElementById(id).textContent = value; }
    badge(id, active, yes, no) {
        const element = document.getElementById(id);
        element.className = 'status-badge ' + (active ? 'status-connected' : 'status-disconnected');
        element.querySelector('.status-text').textContent = active ? yes : no;
    }
    percent(id, bar, value) {
        this.text(id, Math.round(value) + '%');
        document.getElementById(bar).style.width = Math.max(0, Math.min(100, value)) + '%';
    }
    async pollTelemetry() {
        if (!document.hidden) {
            const tasks = [
                this.api('/api/system/health').then(d => this.badge('cameraStatus', d.camera_connected, 'Connected', 'Disconnected')),
                this.api('/api/recording/status').then(d => this.badge('recordingStatus', d.is_recording, 'Recording', 'Standby')),
                this.api('/api/system/metrics').then(d => {
                    this.percent('cpuUsage', 'cpuBar', d.cpu_percent);
                    this.percent('memoryUsage', 'memoryBar', d.memory_percent);
                    this.percent('diskUsage', 'diskBar', d.disk_percent);
                    this.percent('diskText', 'diskProgress', d.disk_percent);
                }),
                this.api('/api/cameras').then(d => this.text('cameraCount', d.cameras.filter(c => c.connected).length)),
                this.api('/api/analytics').then(d => {
                    this.text('motionCount', d.totals.motion_events_last_24h);
                    this.text('motionEventsCount', d.totals.motion_events_last_24h);
                    this.text('recordingCount', d.totals.recording_count);
                    this.text('recordingSize', d.totals.recording_size_gb.toFixed(2) + ' GB');
                }),
                this.api('/api/motion-events?hours=24').then(d => {
                    const list = document.getElementById('eventsList');
                    list.replaceChildren();
                    if (!d.events.length) {
                        const empty = document.createElement('div');
                        empty.className = 'empty-state';
                        empty.textContent = 'All quiet. No motion in the last 24 hours.';
                        list.append(empty);
                    }
                    for (const event of d.events.slice(0, 10)) {
                        const row = document.createElement('div'); row.className = 'event-item';
                        const time = document.createElement('div'); time.className = 'event-time';
                        time.textContent = new Date(event.start_time + 'Z').toLocaleString();
                        const details = document.createElement('div'); details.className = 'event-duration';
                        details.textContent = `Camera ${event.camera_id} · ${event.duration_seconds == null ? 'Ongoing' : event.duration_seconds.toFixed(1) + 's'} · ${event.contour_count} contours`;
                        row.append(time, details); list.append(row);
                    }
                })
            ];
            const results = await Promise.allSettled(tasks);
            const failed = results.filter(r => r.status === 'rejected').length;
            const notice = document.getElementById('connectionNotice');
            notice.dataset.state = failed ? 'error' : 'ok';
            notice.textContent = failed ? `${failed} telemetry feeds unavailable. Displayed values may be stale. Retrying…` : 'Telemetry online · Updated ' + new Date().toLocaleTimeString();
            if (failed) {
                for (const id of ['cameraStatus', 'recordingStatus']) {
                    document.getElementById(id).className = 'status-badge status-unknown';
                    document.getElementById(id).querySelector('.status-text').textContent = 'Check connection';
                }
            }
        }
        setTimeout(() => this.pollTelemetry(), 5000);
    }
    previewMessage(message) {
        const element = document.getElementById('previewMessage');
        element.textContent = message; element.hidden = !message;
    }
    async pollFrame() {
        let delay = 1000 / this.fps;
        if (!this.paused && !document.hidden) {
            try {
                const d = await this.api('/api/stream/frame');
                const image = new Image();
                image.src = 'data:image/jpeg;base64,' + d.frame;
                await image.decode();
                if (!this.paused) {
                    this.ctx.fillStyle = '#09121b'; this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                    const scale = Math.min(this.canvas.width / image.width, this.canvas.height / image.height);
                    this.ctx.drawImage(image, (this.canvas.width - image.width * scale) / 2, (this.canvas.height - image.height * scale) / 2, image.width * scale, image.height * scale);
                    this.previewMessage('');
                    this.text('signalStatus', 'LIVE / LOCAL CAMERA');
                    this.frames++;
                    const elapsed = performance.now() - this.frameTime;
                    if (elapsed > 1000) {
                        this.text('fps', Math.round(this.frames * 1000 / elapsed) + ' FPS');
                        this.frames = 0; this.frameTime = performance.now();
                    }
                }
            } catch {
                this.previewMessage('Camera signal unavailable · Reconnecting');
                this.text('signalStatus', 'NO SIGNAL'); this.text('fps', '— FPS'); delay = 2000;
            }
        }
        setTimeout(() => this.pollFrame(), delay);
    }
}
document.addEventListener('DOMContentLoaded', () => new Dashboard());
