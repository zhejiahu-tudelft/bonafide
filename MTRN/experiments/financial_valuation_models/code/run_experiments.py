"""One offline rebuild command. Retrieval is a separate, deliberately network-only entry point.

Order matters: features writes the variable registry that documentation enriches, score
consolidates the per-issuer ledgers that diagnostics reads, and report reads everything.
"""
import subprocess,sys
from settings import ROOT,REPO

STAGES=['../tests/test_methods.py','features.py','return_models.py','variance_models.py',
        'pooling.py','transform_models.py','score.py','diagnostics.py','dependence.py',
        'documentation.py','report.py','validate.py','audits.py']

def main():
    for script in STAGES:
        print('\nRunning '+script,flush=True)
        subprocess.run([sys.executable,'-B',str((ROOT/'code'/script).resolve())],cwd=REPO,check=True)
    print('\nRebuild complete.',flush=True)

if __name__=='__main__':main()
