"""Explicit remaining performances with the locked audio; no blind retry."""
from pathlib import Path
import subprocess
import sys
script=Path(__file__).with_name('s2v.py')
for shot,take in [('S01','S01-audio-driven-v1'),('LIN1','LIN-part1-audio-driven-v2'),('LIN2','LIN-part2-audio-driven-v2')]:
    subprocess.run([sys.executable,str(script),shot,take],check=True)
