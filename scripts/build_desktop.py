"""Build on the target OS: python scripts/build_desktop.py."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
separator = os.pathsep
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
    '--windowed', '--name', 'Sentinel', '--collect-all', 'cv2',
    '--hidden-import', 'sqlalchemy.sql.default_comparator',
    '--add-data', f'web/templates{separator}web/templates',
    '--add-data', f'web/static{separator}web/static',
    '--add-data', f'config/settings.json{separator}config', 'desktop.py',
], cwd=root, check=True)
