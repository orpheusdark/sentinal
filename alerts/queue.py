"""Bounded, retrying background delivery so network delays never stall capture."""
import queue
import threading
import time
from alerts.telegram import TelegramAlertResult


class QueuedAlerts:
    def __init__(self, client, capacity=128, retries=2, cooldown=10):
        self.client=client
        self.queue=queue.Queue(maxsize=capacity)
        self.retries=retries
        self.cooldown=cooldown
        self.last_motion={}
        self.stop_event=threading.Event()
        self.lock=threading.Lock()
        self.counts={'accepted':0,'sent':0,'failed':0,'dropped':0,'retried':0}
        self.worker=threading.Thread(target=self._run,name='sentinel-alerts',daemon=True)
        self.worker.start()

    def is_configured(self):
        return self.client.is_configured()

    def _enqueue(self, method, kwargs):
        if not self.is_configured() or self.stop_event.is_set():
            return TelegramAlertResult(False,error_message='Alerts are disabled or stopping')
        with self.lock:
            if method=='send_motion_alert':
                key=kwargs['camera_id']; now=time.monotonic()
                if now-self.last_motion.get(key,-float('inf'))<self.cooldown:
                    return TelegramAlertResult(True)
            try: self.queue.put_nowait((method,kwargs))
            except queue.Full:
                self.counts['dropped']+=1
                return TelegramAlertResult(False,error_message='Alert queue is full')
            if method=='send_motion_alert': self.last_motion[key]=now
            self.counts['accepted']+=1
        return TelegramAlertResult(True)

    def send_startup_alert(self, **kwargs): return self._enqueue('send_startup_alert',kwargs)
    def send_shutdown_alert(self, app_name): return self._enqueue('send_shutdown_alert',{'app_name':app_name})
    def send_motion_alert(self, **kwargs): return self._enqueue('send_motion_alert',kwargs)

    def _run(self):
        while not self.stop_event.is_set() or not self.queue.empty():
            try: method,kwargs=self.queue.get(timeout=0.2)
            except queue.Empty: continue
            try:
                success=False
                for attempt in range(self.retries+1):
                    try: result=getattr(self.client,method)(**kwargs)
                    except Exception: result=TelegramAlertResult(False,error_message='Alert delivery failed')
                    if result.success:
                        success=True; break
                    if attempt<self.retries:
                        with self.lock: self.counts['retried']+=1
                        if self.stop_event.wait(min(2**attempt,4)): break
                with self.lock: self.counts['sent' if success else 'failed']+=1
            finally: self.queue.task_done()

    def status(self):
        with self.lock: return dict(self.counts,pending=self.queue.qsize(),worker_alive=self.worker.is_alive())

    def close(self, timeout=2):
        deadline=time.monotonic()+timeout
        while self.queue.unfinished_tasks and time.monotonic()<deadline:
            time.sleep(0.02)
        self.stop_event.set()
        self.worker.join(timeout=max(0,deadline-time.monotonic()))
