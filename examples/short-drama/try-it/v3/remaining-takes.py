"""Three explicitly chosen new takes, never retries unknown submissions."""
import subprocess
import sys
from pathlib import Path
script=Path(__file__).with_name('generate.py')
for shot,take in [('S03','s03-hands-v3'),('S04','s04-close-v3'),('S06','s06-close-v3')]:
    subprocess.run([sys.executable,str(script),shot,take],check=True)
