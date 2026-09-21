"""Rebuild the frozen research package without requesting network data."""
import os, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR','/tmp/mtrn-matplotlib')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
MODULES=['financial_analysis','peer_analysis','stock_analysis','options_analysis',
         'valuation','source_audit','charts','workbook','build_report','validate_research']
if __name__=='__main__':
    for name in MODULES:
        print(f'\nRunning {name}',flush=True)
        subprocess.run([sys.executable,str(HERE/(name+'.py'))],check=True)
    print('\nCompleted frozen MTRN research build and validation.')
