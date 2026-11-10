"""Opt-in, background release notifications; never download or execute updates."""
import json
import re
import threading
import time
from urllib.request import Request,urlopen


def version_key(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:(?:-preview\.|rc)(\d+))?',value)
    if not match: return None
    major,minor,patch,preview=match.groups()
    return int(major),int(minor),int(patch),1 if preview is None else 0,int(preview or 0)


class UpdateChecker:
    def __init__(self, version):
        self.version=version
        self.lock=threading.Lock()
        self.result={'state':'not_checked','current_version':version,'available':False}
        self.last_check=0

    def check(self):
        with self.lock:
            if self.result['state']=='checking' or time.monotonic()-self.last_check<60:
                return dict(self.result)
            self.last_check=time.monotonic()
            self.result.update(state='checking',error=None)
        threading.Thread(target=self._run,name='sentinel-updates',daemon=True).start()
        return self.status()

    def _run(self):
        try:
            request=Request('https://api.github.com/repos/orpheusdark/sentinal/releases?per_page=20',
                            headers={'Accept':'application/vnd.github+json','User-Agent':'Sentinel-update-check'})
            with urlopen(request,timeout=8) as response:
                data=json.loads(response.read(1024*1024))
            choices=[(version_key(item.get('tag_name','')),item) for item in data if not item.get('draft')]
            choices=[item for item in choices if item[0] is not None]
            current=version_key(self.version)
            latest=max(choices,key=lambda item:item[0])[1] if choices else None
            available=bool(latest and current and version_key(latest['tag_name'])>current)
            url=latest.get('html_url','') if latest else ''
            if not url.startswith('https://github.com/orpheusdark/sentinal/releases/'):
                url='https://github.com/orpheusdark/sentinal/releases'
            result={'state':'available' if available else 'up_to_date','available':available,
                    'latest_version':latest['tag_name'] if latest else self.version,'url':url,'checked_at':time.time()}
        except Exception:
            result={'state':'error','available':False,'error':'Unable to check GitHub. Your installed application is unchanged.'}
        with self.lock: self.result.update(result)

    def status(self):
        with self.lock: return dict(self.result)
