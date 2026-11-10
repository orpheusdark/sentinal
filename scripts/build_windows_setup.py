"""Package the completed Windows bundle into a single per-user installer."""
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
payload_dir = root / 'build' / 'installer'
payload_dir.mkdir(parents=True, exist_ok=True)
payload = shutil.make_archive(str(payload_dir / 'sentinel-payload'), 'zip', root / 'dist' / 'Sentinel')
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
    '--windowed', '--name', 'Sentinel-Setup-Windows',
    '--version-file','scripts/windows-version.txt',
    '--add-data', f'{payload};.', 'scripts/windows_setup.py',
], cwd=root, check=True)
