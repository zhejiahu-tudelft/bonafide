"""Compatibility entry point; shared retrieval lives in common/code."""
from pathlib import Path
import runpy
import sys
if __name__ == "__main__":
    if "--out" not in sys.argv:
        sys.argv.extend(["--out", str(Path(__file__).resolve().parents[1])])
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "common/code/fetch_company_data.py"), run_name="__main__")
