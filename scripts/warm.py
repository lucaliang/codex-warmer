"""One-shot warmer. Never print auth files, API bodies, or CLI output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
from policy import decide, activated
from auth_refresh import refresh_auth

AUTH = Path.home() / '.codex/auth.json'
STATE = Path('.state/codex-last-warm.txt')

def digest():
    return hashlib.sha256(AUTH.read_bytes()).digest()

def fetch_meter():
    tokens = json.loads(AUTH.read_text())['tokens']
    req = urllib.request.Request('https://chatgpt.com/backend-api/wham/usage', headers={
        'Authorization': 'Bearer ' + tokens['access_token'],
        'ChatGPT-Account-Id': tokens['account_id']})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def meter():
    try:
        return fetch_meter()
    except urllib.error.HTTPError as error:
        print(f"Quota query HTTP status: {error.code}")
        if error.code == 401:
            original = digest()
            refreshed = refresh_auth()
            saved = persist(original)
            if refreshed and saved:
                try:
                    return fetch_meter()
                except Exception:
                    pass
            print("Authentication recovery failed; reauthorization may be required.")
        return None
    except Exception:
        print("Quota query failed: transport, credential format or JSON error.")
        return None

def persist(original):
    if digest() == original:
        print('Credentials unchanged; no write-back needed.')
        return True
    # Pass credential content over stdin, never command-line arguments.
    result = subprocess.run(['gh','secret','set','CODEX_AUTH_JSON','--repo',os.environ['GITHUB_REPOSITORY']],
        input=AUTH.read_bytes(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('Credential persistence: ' + ('success' if result.returncode == 0 else 'FAILED'))
    return result.returncode == 0

def run(verify_request=False):
    original = digest()
    before = meter()
    now = int(time.time())
    try:
        last = int(STATE.read_text().strip())
    except (OSError, ValueError):
        last = 0
    action = decide(before, now, last)
    print('Window decision: ' + action)
    if action == 'blocked' or (action == 'skip' and not verify_request):
        return 0
    if action == 'unknown':
        print('Cannot confirm quota state; no request sent.')
        return 1
    # Do not retry a potentially completed metered request: avoid duplicates.
    started = int(time.time())
    success = False
    verified = False
    saved = False
    try:
        result = subprocess.run(['codex','exec','--skip-git-repo-check','--sandbox','read-only',
            '-m',os.environ['WARM_MODEL'],'-c','model_reasoning_effort="low"',
            'Reply with OK only. Do not use tools.'], cwd='/tmp',
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
        success = result.returncode == 0
        if not success:
            diagnostic = (result.stderr or b'').decode(errors='replace').lower()
            categories = {
                'model': ('model', 'unsupported'),
                'authentication': ('unauthorized', 'token', '401'),
                'rate_limit': ('rate limit', 'usage limit', 'quota'),
                'network': ('connection', 'network', 'tls', 'certificate'),
                'configuration': ('unexpected argument', 'invalid value', 'config'),
                'runtime': ('sandbox', 'landlock', 'permission denied', 'not found'),
            }
            matched = [name for name, terms in categories.items() if any(term in diagnostic for term in terms)]
            print(f"CLI exit code: {result.returncode}; categories: {','.join(matched) or 'unclassified'}")
        print('Warm request: ' + ('success' if success else 'FAILED'))
        if success:
            STATE.parent.mkdir(exist_ok=True)
            STATE.write_text(str(started)+'\n')
            for delay in (20,20,20):
                time.sleep(delay)
                if activated(before,meter(),started,int(time.time())):
                    verified = True
                    break
            print('Window activation: ' + ('verified' if verified else 'UNCONFIRMED'))
    except subprocess.TimeoutExpired:
        print('Request timed out; completion unknown. No immediate retry.')
    finally:
        saved = persist(original)
    return 0 if success and verified and saved else 1

if __name__ == '__main__':
    try:
        if '--verify-auth-refresh' in sys.argv:
            original = digest()
            refreshed = refresh_auth()
            saved = persist(original)
            readable = meter() is not None if saved else False
            print('Forced auth refresh: ' + ('success' if refreshed else 'FAILED'))
            print('Post-refresh quota read: ' + ('success' if readable else 'FAILED'))
            sys.exit(0 if refreshed and saved and readable else 1)
        sys.exit(run(verify_request='--verify-request' in sys.argv))
    except Exception:
        print('Warmer failed; sensitive diagnostics suppressed.')
        sys.exit(1)
