"""Check actual frozen resources on each build platform without camera access."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if sys.platform == 'win32':
    executable = root / 'dist/Sentinel/Sentinel.exe'
elif sys.platform == 'darwin':
    executable = root / 'dist/Sentinel.app/Contents/MacOS/Sentinel'
else:
    executable = root / 'dist/Sentinel/Sentinel'
subprocess.run([str(executable), '--self-check'], cwd=root, check=True, timeout=90)
print('Frozen application resource check passed')
