"""One offline rebuild command. Retrieval is a separate, deliberately network-only entry point.

Order matters: features writes the variable registry that documentation enriches; the
model stages are independent of one another and run concurrently, each writing its own
interim ledger; score consolidates those ledgers into the named tables, after which the
interim copies are removed; report reads everything; validate runs last but one.
"""
import shutil,subprocess,sys
from settings import ROOT,REPO,INTERIM,CORE

MODELS=[['return_models.py','--ticker',tk] for tk in CORE]+[['variance_models.py'],['pooling.py'],['transform_models.py']]
STAGES=[[['../tests/test_methods.py']],[['features.py']],MODELS,[['score.py']],'remove interim ledgers',
        [['diagnostics.py']],[['dependence.py']],[['documentation.py']],[['revision.py']],[['report.py']],[['validate.py']],[['audits.py']]]

def command(args):
    return [sys.executable,'-B',str((ROOT/'code'/args[0]).resolve())]+args[1:]

def main():
    for stage in STAGES:
        if stage=='remove interim ledgers':
            print('\nRemoving interim ledgers (consolidated by score.py)',flush=True);shutil.rmtree(INTERIM,ignore_errors=True);continue
        print('\nRunning '+', '.join(' '.join(s) for s in stage),flush=True)
        running=[subprocess.Popen(command(s),cwd=REPO) for s in stage]
        codes=[p.wait() for p in running]
        if any(codes):raise SystemExit(f'Stage failed: {stage} exit codes {codes}')
    # Later stages recreate the interim directory on start-up; leave no empty shell behind.
    if INTERIM.exists() and not any(INTERIM.iterdir()):INTERIM.rmdir()
    print('\nRebuild complete.',flush=True)

if __name__=='__main__':main()
