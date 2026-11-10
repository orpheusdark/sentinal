class CameraSetup {
    constructor() {
        this.profiles = []; this.selected = -1; this.image = null;
        this.canvas = document.getElementById('setupCanvas'); this.ctx = this.canvas.getContext('2d');
        this.form = document.getElementById('cameraForm');
        document.getElementById('scanBtn').addEventListener('click', () => this.scan());
        document.getElementById('addCameraBtn').addEventListener('click', () => this.add());
        document.getElementById('previewBtn').addEventListener('click', () => this.preview());
        document.getElementById('saveCamerasBtn').addEventListener('click', () => this.save());
        document.getElementById('removeCameraBtn').addEventListener('click', () => this.remove());
        document.getElementById('addScheduleBtn').addEventListener('click', () => this.scheduleRow());
        document.getElementById('addZoneBtn').addEventListener('click', () => this.addZone(['zoneX','zoneY','zoneW','zoneH'].map(id => Number(document.getElementById(id).value))));
        document.getElementById('clearZonesBtn').addEventListener('click', () => { this.current().zones = []; this.draw(); });
        this.canvas.addEventListener('pointerdown', event => {
            if (!this.current()) return;
            this.origin = this.point(event); this.canvas.setPointerCapture(event.pointerId);
        });
        this.canvas.addEventListener('pointerup', event => {
            if (!this.origin) return;
            const end = this.point(event), start = this.origin; this.origin = null;
            this.addZone([Math.min(start[0], end[0]), Math.min(start[1], end[1]), Math.abs(start[0] - end[0]), Math.abs(start[1] - end[1])]);
        });
        this.load();
    }
    current() { return this.profiles[this.selected]; }
    message(value, error = false) { const element = document.getElementById('setupMessage'); element.textContent = value; element.className = 'message ' + (error ? 'error' : 'success'); }
    async api(path, method = 'GET', data) {
        const response = await fetch(path, {method, headers: {'Content-Type':'application/json','X-Sentinel-Request':'dashboard'}, body: data === undefined ? undefined : JSON.stringify(data), signal: AbortSignal.timeout(60000)});
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || 'Request failed');
        return result;
    }
    async load() {
        try { const result = await this.api('/api/camera-setup'); this.profiles = result.data.profiles; this.select(this.profiles.length ? 0 : -1, false); }
        catch (error) { this.message(error.message, true); document.getElementById('saveCamerasBtn').disabled = true; }
    }
    capture() {
        const profile = this.current(); if (!profile) return;
        const fields = {index:'deviceIndex', name:'cameraName', fps:'profileFps', resolution:'profileResolution', sensitivity:'profileSensitivity', min_contour_area:'profileArea', post_motion_seconds:'profileTail', max_duration_seconds:'profileSegment'};
        for (const [key, id] of Object.entries(fields)) profile[key] = ['name','resolution'].includes(key) ? document.getElementById(id).value : Number(document.getElementById(id).value);
        for (const [key,id] of Object.entries({enabled:'cameraEnabled',motion_enabled:'motionEnabled',recording_enabled:'recordingEnabled',object_detection_enabled:'objectDetection'})) profile[key] = document.getElementById(id).checked;
        profile.record_on_motion = document.getElementById('recordingMode').value === 'motion';
        profile.schedule = [...document.querySelectorAll('.schedule-row')].map(row => ({days: [...row.querySelectorAll('input[type=checkbox]:checked')].map(input => Number(input.dataset.day)), start: row.querySelector('.schedule-start').value, end: row.querySelector('.schedule-end').value}));
    }
    select(index, capture = true) {
        if (capture) { if (!this.form.reportValidity()) return; this.capture(); }
        this.selected = index; this.image = null;
        document.getElementById('profileEditor').hidden = index < 0;
        this.renderList();
        const profile = this.current(); if (!profile) return;
        for (const [key,id] of Object.entries({index:'deviceIndex',name:'cameraName',fps:'profileFps',resolution:'profileResolution',sensitivity:'profileSensitivity',min_contour_area:'profileArea',post_motion_seconds:'profileTail',max_duration_seconds:'profileSegment'})) document.getElementById(id).value = profile[key];
        for (const [key,id] of Object.entries({enabled:'cameraEnabled',motion_enabled:'motionEnabled',recording_enabled:'recordingEnabled',object_detection_enabled:'objectDetection'})) document.getElementById(id).checked = profile[key];
        document.getElementById('recordingMode').value = profile.record_on_motion ? 'motion' : 'continuous';
        document.getElementById('scheduleRows').replaceChildren();
        for (const rule of profile.schedule || []) this.scheduleRow(rule);
        document.getElementById('previewInfo').textContent = 'Capture a preview to check framing and draw motion zones.';
        this.draw();
    }
    renderList() {
        const list = document.getElementById('profileList'); list.replaceChildren();
        this.profiles.forEach((profile,index) => {
            const button = document.createElement('button'); button.className = 'btn profile-button';
            button.textContent = `${profile.name} · Device ${profile.index}`; button.setAttribute('aria-pressed', String(index === this.selected));
            button.addEventListener('click', () => this.select(index)); list.append(button);
        });
        if (!this.profiles.length) list.textContent = 'No configured feeds. Detect a camera or add one manually.';
    }
    add(index) {
        if (this.current() && !this.form.reportValidity()) return;
        this.capture();
        if (this.profiles.length >= 8) return this.message('Up to eight cameras can be configured.', true);
        if (index === undefined) index = Array.from({length:16}, (_,i) => i).find(i => !this.profiles.some(profile => profile.index === i));
        const existing = this.profiles.findIndex(profile => profile.index === index);
        if (existing >= 0) return this.select(existing, false);
        this.profiles.push({index,name:`Camera ${index + 1}`,enabled:true,fps:15,resolution:'720p',motion_enabled:true,sensitivity:30,min_contour_area:300,recording_enabled:true,record_on_motion:true,post_motion_seconds:10,max_duration_seconds:300,zones:[],schedule:[],object_detection_enabled:false});
        this.select(this.profiles.length - 1, false);
    }
    remove() { if (!this.current()) return; this.profiles.splice(this.selected,1); this.select(this.profiles.length ? 0 : -1,false); }
    async scan() {
        const button = document.getElementById('scanBtn'); button.disabled = true; this.message('Checking local cameras…');
        try {
            const result = await this.api('/api/camera-setup/discover','POST',{});
            const list = document.getElementById('discoveredDevices'); list.replaceChildren();
            for (const device of result.data.devices) {
                const button = document.createElement('button'); button.className = 'btn';
                button.textContent = `${device.name} · Device ${device.index}`;
                button.addEventListener('click', () => this.add(device.index)); list.append(button);
            }
            this.message(result.data.devices.length ? 'Select a detected device to configure it.' : 'No camera found. Check device permissions, connections and other camera apps.');
        } catch (error) { this.message(error.message,true); }
        finally { button.disabled = false; }
    }
    async preview() {
        if (!this.current() || !this.form.reportValidity()) return;
        this.capture(); const button = document.getElementById('previewBtn'); button.disabled = true;
        try {
            const profile = this.current(); const result = await this.api('/api/camera-setup/preview','POST',{index:profile.index,fps:profile.fps,resolution:profile.resolution});
            const image = new Image(); image.src = 'data:image/jpeg;base64,' + result.data.frame; await image.decode();
            this.image = image; this.canvas.width = image.width; this.canvas.height = image.height; this.draw();
            document.getElementById('previewInfo').textContent = `${result.data.width} × ${result.data.height} captured. ${result.data.note || 'Drag to add motion zones.'}`;
        } catch (error) { this.message(error.message,true); }
        finally { button.disabled = false; }
    }
    point(event) { const rect = this.canvas.getBoundingClientRect(); return [Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height))]; }
    addZone(values) {
        const profile = this.current(); if (!profile) return;
        const [x,y,w,h] = values;
        if (profile.zones.length >= 12 || values.some(value => !Number.isFinite(value)) || Math.min(x,y)<0 || Math.min(w,h)<0.01 || x+w>1.000001 || y+h>1.000001) return this.message('Use up to 12 rectangles that fit inside the image.',true);
        profile.zones.push(values.map(value => Math.round(value*10000)/10000)); this.draw();
    }
    draw() {
        this.ctx.fillStyle = '#09121b'; this.ctx.fillRect(0,0,this.canvas.width,this.canvas.height);
        if (this.image) this.ctx.drawImage(this.image,0,0,this.canvas.width,this.canvas.height);
        const list = document.getElementById('zoneList'); list.replaceChildren();
        for (const [index,zone] of (this.current()?.zones || []).entries()) {
            const [x,y,w,h] = zone; this.ctx.strokeStyle = '#68efd5'; this.ctx.lineWidth = 3;
            this.ctx.strokeRect(x*this.canvas.width,y*this.canvas.height,w*this.canvas.width,h*this.canvas.height);
            const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-sm';
            button.textContent = `Remove zone ${index+1}: ${zone.map(value => value.toFixed(2)).join(', ')}`;
            button.addEventListener('click', () => {this.current().zones.splice(index,1); this.draw();}); list.append(button);
        }
    }
    scheduleRow(rule = {days:[0,1,2,3,4],start:'09:00',end:'17:00'}) {
        const row = document.createElement('fieldset'); row.className = 'schedule-row';
        const legend = document.createElement('legend'); legend.textContent = 'Active window'; row.append(legend);
        const days = document.createElement('div'); days.className = 'schedule-days';
        ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].forEach((name,index) => {
            const label = document.createElement('label'); label.className = 'check-label';
            const input = document.createElement('input'); input.type = 'checkbox'; input.dataset.day = index; input.checked = rule.days.includes(index);
            label.append(input,document.createTextNode(name)); days.append(label);
        }); row.append(days);
        for (const key of ['start','end']) {
            const label = document.createElement('label'); label.textContent = key === 'start' ? 'From ' : 'Until ';
            const input = document.createElement('input'); input.type = 'time'; input.className = 'schedule-' + key; input.required = true; input.value = rule[key]; label.append(input); row.append(label);
        }
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn'; remove.textContent = 'Remove window'; remove.addEventListener('click', () => row.remove()); row.append(remove);
        document.getElementById('scheduleRows').append(row);
    }
    async save() {
        if (this.current() && !this.form.reportValidity()) return;
        this.capture(); const button = document.getElementById('saveCamerasBtn'); button.disabled = true;
        try { const result = await this.api('/api/camera-setup','PUT',{profiles:this.profiles}); this.message(result.message); this.renderList(); }
        catch (error) { this.message(error.message,true); }
        finally { button.disabled = false; }
    }
}
document.addEventListener('DOMContentLoaded', () => new CameraSetup());
