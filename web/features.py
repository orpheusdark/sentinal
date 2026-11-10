"""Camera setup, playback, timeline, diagnostics and opt-in update endpoints."""
from datetime import datetime,timedelta
from pathlib import Path
import base64
import io
import math
import time
import cv2
from flask import jsonify,request,render_template,Response,send_file
from config.settings import get_config,save_public_settings
from database.models import Recording,MotionEvent
from camera.drivers.builtin import BuiltinCameraDriver
from web.playback import Playback
from web.updates import UpdateChecker


def register_features(server):
    app=server.app
    server.playback=Playback()
    server.updates=UpdateChecker(server.config.version)
    server.started_at=time.monotonic()

    def context(): return server.app_context

    def video(recording_id):
        if not context() or not context().db:
            return None,None,503
        row=server._db_session().query(Recording).filter(Recording.id==recording_id,Recording.deleted_at.is_(None)).first()
        if not row: return None,None,404
        path=Path(row.filepath).resolve()
        if not path.is_relative_to(Path(server.config.storage.recordings_dir).resolve()): return None,None,403
        if not path.is_file(): return None,None,404
        return row,path,200

    @app.get('/cameras/setup')
    def cameras_setup_page():
        return render_template('camera_setup.html',app_name=server.config.app_name,version=server.config.version)

    @app.get('/diagnostics')
    def diagnostics_page():
        return render_template('diagnostics.html',app_name=server.config.app_name,version=server.config.version)

    @app.get('/api/camera-setup')
    def camera_setup_config():
        from config.profiles import profiles_from_config
        from dataclasses import asdict
        return jsonify(success=True,data={'profiles':[asdict(profile) for profile in profiles_from_config(get_config())],
            'resolutions':['360p','480p','720p','1080p'],'max_cameras':8,'schedule_timezone':'host local time'})

    @app.post('/api/camera-setup/discover')
    def camera_discover():
        if not context() or not context().camera_manager:
            return jsonify(success=False,error='Camera service unavailable'),503
        if not server.scan_lock.acquire(blocking=False):
            return jsonify(success=False,error='Camera discovery is already running'),409
        try:
            devices=context().camera_manager.discover()
            for device in devices:
                device['camera_id']=context().camera_manager.camera_db_ids.get(f"builtin_{device['index']}")
            return jsonify(success=True,data={'devices':devices})
        finally: server.scan_lock.release()

    @app.post('/api/camera-setup/preview')
    def camera_preview():
        from config.profiles import CameraProfile
        data=request.get_json()
        try: profile=CameraProfile(index=data.get('index',0),fps=data.get('fps',15),resolution=data.get('resolution','720p')).validate()
        except (AttributeError,TypeError,ValueError) as error:
            return jsonify(success=False,error=str(error)),400
        manager=context().camera_manager if context() else None
        existing=manager.cameras.get(f'builtin_{profile.index}') if manager else None
        pipeline=next((p for p in getattr(context(),'pipelines',{}).values() if p.profile.index==profile.index),None)
        if pipeline and pipeline.stream.get_frame_info()['has_frame']:
            return jsonify(success=True,data={'frame':pipeline.stream.get_frame_as_jpeg(),
                'width':pipeline.stream.get_frame_info().get('width'),'height':pipeline.stream.get_frame_info().get('height'),
                'active':True,'note':'Preview uses the active feed. Saved camera settings apply after restart.'})
        if not server.scan_lock.acquire(blocking=False):
            return jsonify(success=False,error='Camera discovery or preview is already running'),409
        driver=existing or BuiltinCameraDriver(profile.index,profile.name,profile.fps,profile.resolution)
        try:
            if not driver.is_connected and not driver.connect():
                return jsonify(success=False,error='Camera unavailable. Check permissions and other camera applications.'),404
            frame=driver.get_frame()
            if frame is None: return jsonify(success=False,error='No camera frame available'),404
            height,width=frame.shape[:2]
            ok,jpeg=cv2.imencode('.jpg',frame)
            if not ok: return jsonify(success=False,error='Unable to encode preview'),500
            return jsonify(success=True,data={'frame':base64.b64encode(jpeg).decode(),'width':width,'height':height,'active':bool(existing)})
        finally:
            if not existing: driver.disconnect()
            server.scan_lock.release()

    @app.put('/api/camera-setup')
    def camera_save():
        data=request.get_json()
        try:
            if not isinstance(data,dict) or set(data)!={'profiles'}: raise ValueError('Provide camera profiles')
            profiles=data['profiles']
            if not isinstance(profiles,list): raise ValueError('Profiles must be a list')
            save_public_settings({'camera':{'sources':profiles,'enabled':any(profile.get('enabled',True) for profile in profiles if isinstance(profile,dict))}})
            return jsonify(success=True,restart_required=True,message='Camera profiles saved. Restart Sentinel to apply.')
        except (TypeError,ValueError) as error: return jsonify(success=False,error=str(error)),400

    @app.get('/api/recordings/<int:recording_id>/playback')
    def playback_metadata(recording_id):
        row,path,status=video(recording_id)
        if status!=200: return jsonify(success=False,error='Recording unavailable'),status
        try: return jsonify(success=True,data=dict(server.playback.metadata(path),camera_id=row.camera_id,filename=row.filename))
        except ValueError: return jsonify(success=False,error='Recording cannot be decoded. Download it to review in another player.'),415

    @app.get('/api/recordings/<int:recording_id>/frame')
    def playback_frame(recording_id):
        _,path,status=video(recording_id)
        if status!=200: return jsonify(success=False,error='Recording unavailable'),status
        seconds=request.args.get('time',default=0,type=float)
        if seconds is None or not math.isfinite(seconds) or seconds<0:
            return jsonify(success=False,error='Playback time must be a non-negative number'),400
        try: return Response(server.playback.frame(path,seconds),mimetype='image/jpeg')
        except ValueError: return jsonify(success=False,error='Frame unavailable'),415

    @app.get('/api/recordings/<int:recording_id>/thumbnail')
    def recording_thumbnail(recording_id):
        row,path,status=video(recording_id)
        if status!=200: return jsonify(success=False,error='Recording unavailable'),status
        if row.has_thumbnail and row.thumbnail_path:
            thumb=Path(row.thumbnail_path).resolve()
            if thumb.is_relative_to(Path(server.config.storage.recordings_dir).resolve()) and thumb.is_file():
                return send_file(str(thumb),mimetype='image/jpeg')
        try: return Response(server.playback.frame(path,0,width=320),mimetype='image/jpeg')
        except ValueError: return jsonify(success=False,error='Thumbnail unavailable'),404

    @app.get('/api/timeline')
    def timeline():
        if not context() or not context().db: return jsonify(success=False,error='Database unavailable'),503
        session=server._db_session()
        hours=max(1,min(8760,request.args.get('hours',24,type=int)))
        camera_id=request.args.get('camera_id',type=int)
        cutoff=datetime.utcnow()-timedelta(hours=hours)
        events=session.query(MotionEvent).filter(MotionEvent.start_time>=cutoff)
        recordings=session.query(Recording).filter(Recording.start_time>=cutoff,Recording.deleted_at.is_(None))
        if camera_id:
            events=events.filter(MotionEvent.camera_id==camera_id);recordings=recordings.filter(Recording.camera_id==camera_id)
        videos=recordings.order_by(Recording.start_time.desc()).limit(500).all()
        rows=[]
        for event in events.order_by(MotionEvent.start_time.desc()).limit(200).all():
            match=next((v for v in videos if v.camera_id==event.camera_id and
                        (v.motion_event_id==event.id or (v.start_time<=event.start_time and v.end_time and v.end_time>=event.start_time))),None)
            rows.append({'id':event.id,'camera_id':event.camera_id,'start_time':event.start_time.isoformat(),
                'end_time':event.end_time.isoformat() if event.end_time else None,'contour_count':event.contour_count,
                'recording_id':match.id if match else None})
        return jsonify(success=True,data={'events':rows,'count':len(rows),'hours':hours})

    @app.get('/api/diagnostics')
    def diagnostics():
        import psutil,shutil,platform
        ctx=context();memory=psutil.Process().memory_info()
        root=Path(server.config.storage.recordings_dir).resolve()
        disk=shutil.disk_usage(root if root.exists() else Path.cwd())
        return jsonify(success=True,data={'version':server.config.version,'platform':platform.system(),
            'python':platform.python_version(),'uptime_seconds':round(time.monotonic()-server.started_at),
            'process_memory_mb':round(memory.rss/1048576,1),'logical_cpus':psutil.cpu_count(),
            'cpu_percent':psutil.cpu_percent(None),'disk_free_gb':round(disk.free/1073741824,2),
            'database_healthy':bool(ctx and ctx.db and ctx.db.health_check()),
            'opencv_threads':cv2.getNumThreads(),'camera_pipelines':[p.status() for p in getattr(ctx,'pipelines',{}).values()],
            'alerts':ctx.alert_manager.status() if ctx and hasattr(getattr(ctx,'alert_manager',None),'status') else {'state':'unavailable'},
            'updates':server.updates.status(),'automatic_update_checks':server.config.web.check_updates,'windows_distribution_signed':False,
            'notice':'Diagnostics omit credentials, hostnames, IP addresses and filesystem paths.'})

    @app.get('/api/updates')
    def updates_status(): return jsonify(success=True,data=server.updates.status())

    @app.post('/api/updates/check')
    def updates_check(): return jsonify(success=True,data=server.updates.check())
