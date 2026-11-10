class Diagnostics {
    constructor() {
        this.data = null;
        document.getElementById('refreshDiagnosticsBtn').addEventListener('click', () => this.refresh());
        document.getElementById('downloadDiagnosticsBtn').addEventListener('click', () => this.download());
        document.getElementById('checkUpdatesBtn').addEventListener('click', () => this.checkUpdates());
        document.getElementById('saveUpdatePreferenceBtn').addEventListener('click', () => this.savePreference());
        this.refresh();
    }
    cards(id, values) {
        const list = document.getElementById(id); list.replaceChildren();
        for (const [label,value] of values) {
            const card = document.createElement('div'); card.className = 'metric-card';
            const heading = document.createElement('h3'); heading.textContent = label;
            const text = document.createElement('div'); text.className = 'metric-value'; text.textContent = value;
            card.append(heading,text); list.append(card);
        }
    }
    async refresh() {
        try {
            const response = await fetch('/api/diagnostics',{signal:AbortSignal.timeout(8000)}); const result = await response.json();
            if (!response.ok || !result.success) throw new Error('Diagnostics unavailable');
            const d = result.data; this.data = d;
            document.getElementById('automaticUpdates').checked = d.automatic_update_checks;
            this.cards('diagnosticMetrics',[['Version',d.version],['Memory',`${d.process_memory_mb} MB`],['Host CPU',`${d.cpu_percent}%`],['Disk free',`${d.disk_free_gb} GB`],['Database',d.database_healthy ? 'Healthy' : 'Unavailable'],['OpenCV threads',d.opencv_threads]]);
            const pipelines = document.getElementById('pipelineDiagnostics'); pipelines.replaceChildren();
            for (const pipeline of d.camera_pipelines) {
                const row = document.createElement('div'); row.className = 'event-item';
                const title = document.createElement('h3'); title.textContent = pipeline.name;
                const info = document.createElement('p'); info.textContent = `${pipeline.connected ? 'Connected' : 'Disconnected'} · ${pipeline.observed_fps} observed / ${pipeline.target_fps} target FPS · ${pipeline.processing_ms} ms processing · ${pipeline.errors} errors · ${pipeline.recording ? 'Recording' : 'Standby'} · ${pipeline.scheduled ? 'Schedule active' : 'Outside schedule'} · Last frame: ${pipeline.frame_age_seconds == null ? 'never' : pipeline.frame_age_seconds + 's ago'}`;
                const detection = document.createElement('p'); detection.className = 'help-text'; detection.textContent = pipeline.object_detector.backend + (pipeline.object_detector.error ? ': ' + pipeline.object_detector.error : '');
                row.append(title,info,detection); pipelines.append(row);
            }
            if (!d.camera_pipelines.length) pipelines.textContent = 'No camera pipelines. Use Cameras to configure a device and restart.';
            const a = d.alerts;
            this.cards('alertDiagnostics',[['Pending',a.pending ?? '—'],['Delivered',a.sent ?? '—'],['Retries',a.retried ?? '—'],['Failed',a.failed ?? '—'],['Dropped',a.dropped ?? '—']]);
            this.updateStatus(d.updates);
            document.getElementById('diagnosticsMessage').textContent = 'Updated ' + new Date().toLocaleTimeString();
        } catch (error) { document.getElementById('diagnosticsMessage').textContent = error.message; }
    }
    updateStatus(d) {
        const messages = {not_checked:'No update check requested. Checking contacts GitHub and never installs software automatically.',checking:'Checking GitHub…',available:`New release available: ${d.latest_version}`,up_to_date:`No newer release found. Installed: ${d.current_version}`,error:d.error};
        document.getElementById('updateMessage').textContent = messages[d.state] || 'Update status unavailable';
        if (d.url?.startsWith('https://github.com/orpheusdark/sentinal/releases')) document.getElementById('releaseLink').href = d.url;
    }
    async checkUpdates() {
        const button = document.getElementById('checkUpdatesBtn'); button.disabled = true;
        try {
            const response = await fetch('/api/updates/check',{method:'POST',headers:{'Content-Type':'application/json','X-Sentinel-Request':'dashboard'},body:'{}',signal:AbortSignal.timeout(8000)});
            const result = await response.json(); if (!response.ok || !result.success) throw new Error('Update check unavailable');
            this.updateStatus(result.data);
            const poll = async () => {
                try {
                    const response = await fetch('/api/updates',{signal:AbortSignal.timeout(8000)}); const result = await response.json();
                    this.updateStatus(result.data);
                    if (result.data.state === 'checking') setTimeout(poll,1000); else button.disabled = false;
                } catch { button.disabled = false; document.getElementById('updateMessage').textContent = 'Update status unavailable. Try again later.'; }
            }; setTimeout(poll,1000);
        } catch (error) { button.disabled = false; document.getElementById('updateMessage').textContent = error.message; }
    }
    download() {
        if (!this.data) return;
        const blob = new Blob([JSON.stringify(this.data,null,2)],{type:'application/json'});
        const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'sentinel-diagnostics.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
    }
    async savePreference() {
        try {
            const response = await fetch('/api/config',{method:'PUT',headers:{'Content-Type':'application/json','X-Sentinel-Request':'dashboard'},body:JSON.stringify({web:{check_updates:document.getElementById('automaticUpdates').checked}}),signal:AbortSignal.timeout(8000)});
            const result = await response.json(); if (!response.ok || !result.success) throw new Error(result.error || 'Unable to save preference');
            document.getElementById('updatePreferenceMessage').textContent = result.message;
        } catch (error) { document.getElementById('updatePreferenceMessage').textContent = error.message; }
    }
}
document.addEventListener('DOMContentLoaded', () => new Diagnostics());
