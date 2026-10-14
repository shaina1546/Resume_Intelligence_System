"""Start the app in a subprocess, check HTTP health, then shut it down."""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--server.port','8517'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
    for _ in range(50):
        if p.poll() is not None:
            raise RuntimeError('Server exited before health check')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8517/_stcore/health',timeout=1) as response:
                assert response.status==200
                print('Streamlit HTTP health: 200 / '+response.read().decode());break
        except OSError: time.sleep(.2)
    else: raise RuntimeError('Server did not become healthy')
finally:
    p.terminate()
    output=p.communicate(timeout=10)[0]
    print(output)
