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

if sys.platform == 'darwin':
    # macOS requires this usage description before an app accesses a camera.
    import plistlib
    bundle = root / 'dist' / 'Sentinel.app'
    plist_path = bundle / 'Contents' / 'Info.plist'
    with plist_path.open('rb') as stream:
        metadata = plistlib.load(stream)
    metadata['NSCameraUsageDescription'] = 'Sentinel uses your camera to detect motion and record video locally.'
    metadata['CFBundleIdentifier'] = 'org.orpheusdark.sentinel'
    with plist_path.open('wb') as stream:
        plistlib.dump(metadata, stream)
    # Refresh the local build signature after updating the bundle metadata.
    # Distribution signing/notarization still requires the owner's identity.
    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(bundle)], check=True)
