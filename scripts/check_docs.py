"""Validate current guide links and UTF-8 without depending on a Markdown parser."""
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[1]
guides=[root/name for name in ('readme.md','CONTRIBUTING.md','SECURITY.md','SUPPORT.md','CODE_OF_CONDUCT.md')]
guides += [p for p in (root/'docs').glob('*.md') if not p.name.startswith('PHASE')]
errors=[]
for path in guides:
    try:text=path.read_bytes().decode('utf-8')
    except UnicodeDecodeError:
        errors.append(f'{path.name}: expected UTF-8');continue
    if '\r\r' in text:errors.append(f'{path.name}: repeated carriage returns')
    for destination in re.findall(r'\]\(([^)]+)\)',text):
        if destination.startswith(('http:','https:','#','mailto:')):continue
        target=destination.split('#',1)[0]
        if target and not (path.parent/target).exists():errors.append(f'{path.name}: missing link {target}')
if errors:raise SystemExit('\n'.join(errors))
print(f'Documentation checks passed for {len(guides)} current guides')
