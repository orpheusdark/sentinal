"""Small native launcher for the local dashboard, suitable for frozen builds."""
import argparse
import os
from pathlib import Path
import sys
import threading
import webbrowser


def prepare_runtime(data_dir=None):
    """Keep writable files outside the install directory on every platform."""
    import shutil
    if data_dir is None:
        if sys.platform == 'win32':
            base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Sentinel'
        elif sys.platform == 'darwin':
            base = Path.home() / 'Library' / 'Application Support' / 'Sentinel'
        else:
            base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'sentinel'
    else:
        base = Path(data_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    config_file = base / 'config' / 'settings.json'
    config_file.parent.mkdir(exist_ok=True)
    if not config_file.exists():
        shutil.copyfile(Path(__file__).parent / 'config' / 'settings.json', config_file)
    os.chdir(base)
    return config_file


def main():
    parser = argparse.ArgumentParser(description='Sentinel desktop launcher')
    parser.add_argument('--self-check', action='store_true', help='Check bundled resources without camera access')
    parser.add_argument('--data-dir', help='Override the application data directory')
    args = parser.parse_args()
    if args.self_check:
        from config.settings import ConfigManager
        from web.server import WebServer
        ConfigManager()
        server = WebServer()
        with server.app.test_client() as client:
            for route in ('/', '/settings', '/recordings', '/api/health', '/static/css/style.css'):
                if client.get(route).status_code != 200:
                    raise RuntimeError(f'Bundled resource failed: {route}')
        return 0
    config_file = prepare_runtime(args.data_dir)
    import tkinter as tk
    from tkinter import messagebox
    from app import Application

    window = tk.Tk()
    window.title('Sentinel · Local surveillance')
    window.geometry('500x340')
    window.configure(bg='#080d17')
    status = tk.StringVar(value='Ready. Start Sentinel to connect your camera.')
    state = {'app': None, 'worker': None, 'closing': False}
    tk.Label(window, text='SENTINEL', bg='#080d17', fg='#68efd5', font=('Bahnschrift', 26)).pack(pady=(30, 5))
    tk.Label(window, text='LOCAL SURVEILLANCE CONTROL', bg='#080d17', fg='#9aadc5').pack()
    tk.Label(window, textvariable=status, bg='#080d17', fg='#e6edf7', wraplength=440).pack(pady=24)

    def open_dashboard():
        app = state['app']
        if app and app.context.web_server and app.context.running:
            cfg = app.context.config.web
            webbrowser.open(f"{'https' if cfg.use_https else 'http'}://127.0.0.1:{cfg.port}")

    def start():
        if state['worker'] and state['worker'].is_alive():
            return
        app = Application(config_file=str(config_file))
        state['app'] = app
        state['worker'] = threading.Thread(target=app.run, daemon=True)
        state['worker'].start()
        status.set('Starting camera and local dashboard…')
        window.after(500, ready)

    def ready():
        app = state['app']
        if state['closing']:
            return
        if app.context.running:
            status.set('Running. Video is stored on this device.')
            open_dashboard()
        elif state['worker'].is_alive():
            window.after(500, ready)
        else:
            status.set('Unable to start. Check camera permissions and logs in the data folder.')

    def stop():
        if state['app']:
            state['app'].context.shutdown()
            status.set('Stopping and finalizing recordings…')
            window.after(300, stopped)

    def stopped():
        if state['worker'] and state['worker'].is_alive():
            window.after(300, stopped)
        elif state['closing']:
            window.destroy()
        else:
            status.set('Stopped. Recordings are saved.')

    def close():
        state['closing'] = True
        if state['app']:
            stop()
        else:
            window.destroy()

    for label, command in [('Start Sentinel', start), ('Open dashboard', open_dashboard), ('Stop Sentinel', stop)]:
        tk.Button(window, text=label, command=command, bg='#193333', fg='#e6edf7', width=30, pady=5).pack(pady=3)
    window.protocol('WM_DELETE_WINDOW', close)
    window.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
