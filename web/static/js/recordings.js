class RecordingPlayback {
    constructor() {
        this.dialog = document.getElementById('playbackDialog'); this.generation = 0; this.timer = null; this.playing = false; this.url = null;
        document.getElementById('closePlaybackBtn').addEventListener('click', () => this.close());
        this.dialog.addEventListener('cancel', event => { event.preventDefault(); this.close(); });
        document.getElementById('playPauseBtn').addEventListener('click', () => this.playing ? this.pause() : this.play());
        document.getElementById('playbackSeek').addEventListener('input', event => this.seek(Number(event.target.value)));
    }
    time(value) { const seconds = Math.max(0,Math.floor(value)); return Math.floor(seconds/60) + ':' + String(seconds%60).padStart(2,'0'); }
    controls() {
        document.getElementById('playPauseBtn').textContent = this.playing ? 'Pause' : 'Play';
        document.getElementById('playbackSeek').value = this.position;
        document.getElementById('playbackTime').textContent = this.time(this.position) + ' / ' + this.time(this.duration);
    }
    async open(id) {
        this.pause(); this.generation++; this.id = Number(id); this.position = 0; this.duration = 0;
        const generation = this.generation;
        this.focusReturn = document.activeElement;
        if (!this.dialog.open) this.dialog.showModal();
        document.getElementById('playbackMessage').textContent = 'Loading recording…';
        document.getElementById('playbackImage').removeAttribute('src');
        try {
            const response = await fetch(`/api/recordings/${this.id}/playback`,{signal:AbortSignal.timeout(8000)});
            const result = await response.json(); if (!response.ok || !result.success) throw new Error(result.error || 'Playback unavailable');
            if (generation !== this.generation) return;
            this.duration = result.data.duration;
            document.getElementById('playbackTitle').textContent = `Camera ${result.data.camera_id} · ${result.data.filename}`;
            document.getElementById('playbackDownload').href = `/api/recordings/${this.id}/download`;
            document.getElementById('playbackSeek').max = this.duration;
            this.controls(); await this.frame(0,generation);
            if (generation === this.generation) document.getElementById('playbackMessage').textContent = 'Ready. Play or seek to review the recording.';
        } catch (error) { document.getElementById('playbackMessage').textContent = error.message; }
    }
    async frame(seconds, generation) {
        const response = await fetch(`/api/recordings/${this.id}/frame?time=${seconds.toFixed(3)}`,{signal:AbortSignal.timeout(8000)});
        if (!response.ok) throw new Error('Recording preview unavailable. Try downloading the original.');
        const blob = await response.blob();
        if (generation !== this.generation || !this.dialog.open) return;
        const url = URL.createObjectURL(blob); const previous = this.url;
        const image = document.getElementById('playbackImage'); image.src = url; this.url = url;
        try { await image.decode(); } finally { if (previous) URL.revokeObjectURL(previous); }
    }
    play() {
        if (!this.duration) return;
        if (this.position >= this.duration) this.position = 0;
        this.playing = true; this.started = performance.now() - this.position*1000; this.controls(); this.loop(this.generation);
    }
    pause() { this.playing = false; clearTimeout(this.timer); this.timer = null; if (this.position !== undefined) this.controls(); }
    async loop(generation) {
        if (!this.playing || generation !== this.generation) return;
        this.position = Math.min(this.duration,(performance.now()-this.started)/1000); this.controls();
        try { await this.frame(this.position,generation); }
        catch (error) { this.pause(); document.getElementById('playbackMessage').textContent = error.message; return; }
        if (this.position >= this.duration) { this.pause(); return; }
        if (this.playing && generation === this.generation) this.timer = setTimeout(() => this.loop(generation),200);
    }
    async seek(position) {
        const resume = this.playing; this.pause(); this.position = position; this.generation++; const generation = this.generation; this.controls();
        try { await this.frame(position,generation); if (resume && generation === this.generation) this.play(); }
        catch (error) { document.getElementById('playbackMessage').textContent = error.message; }
    }
    close() {
        this.pause(); this.generation++; this.dialog.close();
        document.getElementById('playbackImage').removeAttribute('src');
        if (this.url) URL.revokeObjectURL(this.url); this.url = null;
        this.focusReturn?.focus();
    }
}

class RecordingsPage {
    constructor() {
        this.offset = 0; this.limit = 30; this.request = 0; this.playback = new RecordingPlayback();
        for (const id of ['daysFilter','cameraFilter']) document.getElementById(id).addEventListener('change', () => {this.offset = 0; this.load();});
        document.getElementById('refreshBtn').addEventListener('click', () => this.load());
        document.getElementById('previousBtn').addEventListener('click', () => {this.offset = Math.max(0,this.offset-this.limit); this.load();});
        document.getElementById('nextBtn').addEventListener('click', () => {this.offset += this.limit; this.load();});
        this.load(); this.cameras();
    }
    async cameras() {
        try {
            const response = await fetch('/api/analytics'); const result = await response.json();
            if (!result.success) return;
            for (const camera of result.data.cameras) {
                const option = document.createElement('option'); option.value = camera.camera_id; option.textContent = camera.name; document.getElementById('cameraFilter').append(option);
            }
        } catch { /* Archive remains available if metadata is temporarily offline. */ }
    }
    async timeline(days, camera, request) {
        const list = document.getElementById('activityTimeline');
        try {
            const params = new URLSearchParams({hours:Number(days)*24}); if (camera) params.set('camera_id',camera);
            const response = await fetch('/api/timeline?' + params,{signal:AbortSignal.timeout(8000)}); const result = await response.json();
            if (!response.ok || !result.success) throw new Error();
            if (request !== this.request) return;
            list.replaceChildren();
            for (const event of result.data.events) {
                const row = document.createElement('div'); row.className = 'timeline-item'; row.setAttribute('role','listitem');
                const content = document.createElement('div');
                const title = document.createElement('strong'); title.textContent = `Motion · Camera ${event.camera_id}`;
                const details = document.createElement('p'); details.className = 'help-text'; details.textContent = new Date(event.start_time+'Z').toLocaleString() + (event.end_time ? ' · Completed' : ' · Ongoing');
                content.append(title,details); row.append(content);
                if (event.recording_id) { const play = document.createElement('button'); play.className = 'btn btn-sm'; play.textContent = 'Review video'; play.addEventListener('click', () => this.playback.open(event.recording_id)); row.append(play); }
                else { const label = document.createElement('span'); label.className = 'help-text'; label.textContent = 'No finalized video'; row.append(label); }
                list.append(row);
            }
            if (!result.data.events.length) {const empty = document.createElement('div'); empty.className = 'empty-state'; empty.textContent = 'No events in the selected period.'; list.append(empty);}
        } catch { if (request === this.request) list.textContent = 'Timeline unavailable. Refresh to retry.'; }
    }
    async load() {
        const id = ++this.request; const list = document.getElementById('recordingsList'); list.textContent = 'Loading archive…';
        const days = document.getElementById('daysFilter').value, camera = document.getElementById('cameraFilter').value;
        this.timeline(days,camera,id);
        try {
            const params = new URLSearchParams({days,limit:this.limit,offset:this.offset}); if (camera) params.set('camera_id',camera);
            const response = await fetch('/api/recordings?' + params,{signal:AbortSignal.timeout(8000)}); const result = await response.json();
            if (!response.ok || !result.success) throw new Error(); if (id !== this.request) return;
            list.replaceChildren(); const data = result.data;
            for (const rec of data.recordings) {
                const card = document.createElement('article'); card.className = 'recording-card';
                const image = document.createElement('img'); image.className = 'recording-thumbnail'; image.loading = 'lazy'; image.alt = `Recording preview from camera ${rec.camera_id}`; image.src = `/api/recordings/${Number(rec.id)}/thumbnail`;
                image.addEventListener('error', () => {image.hidden = true;});
                const header = document.createElement('div'); header.className = 'recording-header';
                const title = document.createElement('h2'); title.className = 'recording-title'; title.textContent = `Camera ${rec.camera_id}`;
                const time = document.createElement('p'); time.className = 'recording-meta'; time.textContent = new Date(rec.start_time+'Z').toLocaleString(); header.append(title,time);
                const body = document.createElement('div'); body.className = 'recording-body'; body.textContent = `${(rec.duration_seconds ?? 0).toFixed(1)} seconds · ${((rec.file_size_bytes ?? 0)/1048576).toFixed(1)} MB`;
                const actions = document.createElement('div'); actions.className = 'recording-actions';
                const play = document.createElement('button'); play.className = 'btn btn-primary'; play.textContent = 'Play / seek'; play.addEventListener('click', () => this.playback.open(rec.id));
                const download = document.createElement('a'); download.className = 'btn'; download.href = `/api/recordings/${Number(rec.id)}/download`; download.textContent = 'Download';
                actions.append(play,download); card.append(image,header,body,actions); list.append(card);
            }
            if (!data.recordings.length) {const empty = document.createElement('div'); empty.className = 'empty-state'; empty.textContent = 'No recordings in this time period.'; list.append(empty);}
            document.getElementById('previousBtn').disabled = this.offset === 0;
            document.getElementById('nextBtn').disabled = this.offset+data.count >= data.total;
            document.getElementById('pageStatus').textContent = `${data.total ? this.offset+1 : 0}–${this.offset+data.count} of ${data.total}`;
        } catch {if (id === this.request) {list.textContent = 'Archive unavailable. Check your connection and refresh.'; document.getElementById('nextBtn').disabled = true;}}
    }
}
document.addEventListener('DOMContentLoaded', () => new RecordingsPage());
