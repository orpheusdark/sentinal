"""Per-user installer for the frozen Windows application; no admin access."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox
import zipfile


def install():
    target = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Sentinel'
    target.mkdir(parents=True, exist_ok=True)
    payload = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'sentinel-payload.zip'
    # Only extract the build-generated payload, rejecting traversal and links.
    with zipfile.ZipFile(payload) as archive:
        for info in archive.infolist():
            dest = (target / info.filename).resolve()
            if not dest.is_relative_to(target.resolve()):
                raise ValueError('Invalid installer payload')
        archive.extractall(target)
    exe = target / 'Sentinel.exe'
    # JSON string literals safely quote paths for PowerShell's single-string script.
    def ps_literal(value):
        return "'" + str(value).replace("'", "''") + "'"
    start_menu = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs'
    shortcut = start_menu / 'Sentinel.lnk'
    command = ("$shell = New-Object -ComObject WScript.Shell; "
               f"$link = $shell.CreateShortcut({ps_literal(shortcut)}); "
               f"$link.TargetPath = {ps_literal(exe)}; "
               f"$link.WorkingDirectory = {ps_literal(target)}; $link.Save()")
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return exe


def main():
    window = tk.Tk()
    window.title('Install Sentinel')
    window.geometry('500x280')
    window.configure(bg='#080d17')
    tk.Label(window, text='SENTINEL', font=('Bahnschrift', 26), bg='#080d17', fg='#68efd5').pack(pady=(30, 10))
    tk.Label(window, text='Local camera surveillance, ready to run.\nInstalls for your Windows account. No Python required.\nExisting recordings and settings are preserved.',
             bg='#080d17', fg='#e6edf7', wraplength=450).pack(pady=10)
    status = tk.StringVar()
    tk.Label(window, textvariable=status, bg='#080d17', fg='#9aadc5').pack()

    def run():
        button.config(state='disabled')
        status.set('Installing…'); window.update_idletasks()
        try:
            exe = install()
        except Exception:
            status.set('Installation failed. Close Sentinel before trying again.')
            button.config(state='normal')
            return
        status.set('Installed. Find Sentinel in the Start menu.')
        button.config(text='Open Sentinel', state='normal', command=lambda: subprocess.Popen([str(exe)], cwd=exe.parent))

    button = tk.Button(window, text='Install Sentinel', command=run, width=28, bg='#193333', fg='#e6edf7', pady=8)
    button.pack(pady=16)
    window.mainloop()


if __name__ == '__main__':
    main()
