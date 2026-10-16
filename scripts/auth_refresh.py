"""Ask the official CLI to refresh managed OAuth without generating a response."""
import json
import queue
import subprocess
import threading
import time

def refresh_auth():
    proc = subprocess.Popen(['codex','app-server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,text=True,bufsize=1)
    replies = queue.Queue()
    def read():
        for line in proc.stdout:
            try: replies.put(json.loads(line))
            except ValueError: pass
        replies.put(None)
    worker = threading.Thread(target=read,daemon=True)
    worker.start()
    def send(message):
        proc.stdin.write(json.dumps(message)+'\n');proc.stdin.flush()
    def response(request_id):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            reply=replies.get(timeout=max(.01,deadline-time.monotonic()))
            if reply is None: return False
            if reply.get('id')==request_id:
                if 'error' in reply or 'result' not in reply:
                    return False
                if request_id == 2:
                    account = reply['result'].get('account') or {}
                    return account.get('type') == 'chatgpt'
                return True
        return False
    try:
        send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'codex_warmer','version':'1.0'}}})
        if not response(1): return False
        send({'method':'initialized','params':{}})
        send({'id':2,'method':'account/read','params':{'refreshToken':True}})
        return response(2)
    except (OSError,queue.Empty):
        return False
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill();proc.wait()
        worker.join(timeout=2)
        proc.stdin.close();proc.stdout.close()
