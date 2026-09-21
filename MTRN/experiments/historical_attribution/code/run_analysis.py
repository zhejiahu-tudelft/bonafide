"""One offline rebuild command; retrieval is intentionally a separate entry point."""
import subprocess,sys
from settings import ROOT,REPO

def main():
    for script in ['test_methods.py','market_analysis.py','event_analysis.py','financial_analysis.py','robustness.py','context_analysis.py','build_report.py','validate.py']:
        print('\nRunning '+script,flush=True)
        subprocess.run([sys.executable,'-B',str(ROOT/'code'/script)],cwd=REPO,check=True)

if __name__=='__main__':main()
