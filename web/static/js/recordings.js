class RecordingsPage {
    constructor() {
        this.offset = 0; this.limit = 30; this.request = 0;
        for (const id of ['daysFilter', 'cameraFilter']) document.getElementById(id).addEventListener('change', () => {this.offset = 0; this.load();});
        document.getElementById('refreshBtn').addEventListener('click', () => this.load());
        document.getElementById('previousBtn').addEventListener('click', () => {this.offset = Math.max(0, this.offset - this.limit); this.load();});
        document.getElementById('nextBtn').addEventListener('click', () => {this.offset += this.limit; this.load();});
        this.load(); this.cameras();
    }
    async cameras() {
        try {
            const response = await fetch('/api/cameras'); const result = await response.json();
            if (!result.success) return;
            for (const camera of result.data.cameras) {
                const option = document.createElement('option'); option.value = camera.id;
                option.textContent = `Camera ${camera.id}`; document.getElementById('cameraFilter').append(option);
            }
        } catch { /* Archive remains available if the camera manager is offline. */ }
    }
    async load() {
        const id = ++this.request;
        const list = document.getElementById('recordingsList');
        list.textContent = 'Loading archive…';
        try {
            const params = new URLSearchParams({days: document.getElementById('daysFilter').value, limit: this.limit, offset: this.offset});
            const camera = document.getElementById('cameraFilter').value;
            if (camera) params.set('camera_id', camera);
            const response = await fetch('/api/recordings?' + params, {signal: AbortSignal.timeout(8000)});
            const result = await response.json();
            if (!response.ok || !result.success) throw new Error();
            if (id !== this.request) return;
            list.replaceChildren();
            const data = result.data;
            for (const rec of data.recordings) {
                const card = document.createElement('article'); card.className = 'recording-card';
                const header = document.createElement('div'); header.className = 'recording-header';
                const title = document.createElement('h2'); title.className = 'recording-title'; title.textContent = `Camera ${rec.camera_id}`;
                const time = document.createElement('p'); time.className = 'recording-meta'; time.textContent = new Date(rec.start_time + 'Z').toLocaleString();
                header.append(title, time);
                const body = document.createElement('div'); body.className = 'recording-body';
                body.textContent = `${(rec.duration_seconds ?? 0).toFixed(1)} seconds · ${((rec.file_size_bytes ?? 0) / 1048576).toFixed(1)} MB`;
                const actions = document.createElement('div'); actions.className = 'recording-actions';
                const download = document.createElement('a'); download.className = 'btn btn-primary';
                download.href = `/api/recordings/${Number(rec.id)}/download`; download.textContent = 'Download recording';
                actions.append(download); card.append(header, body, actions); list.append(card);
            }
            if (!data.recordings.length) {const empty = document.createElement('div'); empty.className = 'empty-state'; empty.textContent = 'No recordings in this time period.'; list.append(empty);}
            document.getElementById('previousBtn').disabled = this.offset === 0;
            document.getElementById('nextBtn').disabled = this.offset + data.count >= data.total;
            document.getElementById('pageStatus').textContent = `${data.total ? this.offset + 1 : 0}–${this.offset + data.count} of ${data.total}`;
        } catch {
            if (id === this.request) {list.textContent = 'Archive unavailable. Check your connection and refresh.'; document.getElementById('nextBtn').disabled = true;}
        }
    }
}
document.addEventListener('DOMContentLoaded', () => new RecordingsPage());
