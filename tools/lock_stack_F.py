#!/usr/bin/env python3
"""Lock and record the roadmap-F execution stack (note 28 §10).

Used only after the installation step is approved, inside the sid-f environment:

    python tools/lock_stack_F.py pip-lock REPORT.json CONDA_LIST.json OUT.txt
    python tools/lock_stack_F.py record CONDA_LIST.json OUT.json

`pip-lock` turns pip's own `install --dry-run --report` into a hash-pinned requirements file.
It refuses if pip would install anything conda already provides, or if an entry has no
sha256. `record` writes the resolved Python, architecture, NumPy/SciPy, BLAS packages and
thread variables. Neither command installs anything.
"""
import json
import os
import platform
import re
import sys
from pathlib import Path

THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")
BLAS_PACKAGES = ("libblas", "libcblas", "liblapack", "libopenblas")


class LockError(RuntimeError):
    pass


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def conda_provided(conda_list):
    """Names of packages installed by conda (not the pip-installed entries conda also lists)."""
    return {canonical(p["name"]) for p in conda_list if p.get("channel") != "pypi"}


def sha256_of(item):
    archive = (item.get("download_info") or {}).get("archive_info") or {}
    hashes = archive.get("hashes") or {}
    if "sha256" in hashes:
        return hashes["sha256"]
    legacy = archive.get("hash", "")
    if legacy.startswith("sha256="):
        return legacy[len("sha256="):]
    return None


def pip_lock_lines(report, conda_list):
    provided = conda_provided(conda_list)
    lines = []
    for item in report.get("install", []):
        name, version = item["metadata"]["name"], item["metadata"]["version"]
        if canonical(name) in provided:
            raise LockError(f"pip would install {name} {version}, which conda already provides")
        digest = sha256_of(item)
        if not digest:
            raise LockError(f"{name} {version}: the pip report records no sha256")
        lines.append(f"{name}=={version} --hash=sha256:{digest}")
    return sorted(lines, key=str.lower)


def stack_record(conda_list):
    import numpy
    import scipy
    blas = {p["name"]: {"version": p["version"], "build": p.get("build_string"), "channel": p.get("channel")}
            for p in conda_list if p["name"] in BLAS_PACKAGES}
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "machine": platform.machine(), "platform": platform.platform(),
            "numpy": numpy.__version__, "scipy": scipy.__version__,
            "numpy_config": numpy.show_config("dicts"),
            "blas_packages": blas,
            "openblas_pinned": "openblas" in (blas.get("libblas") or {}).get("build", ""),
            "threads": {v: os.environ.get(v) for v in THREAD_VARIABLES}}


def main(argv):
    if len(argv) == 4 and argv[0] == "pip-lock":
        report, conda_list = json.loads(Path(argv[1]).read_text()), json.loads(Path(argv[2]).read_text())
        try:
            lines = pip_lock_lines(report, conda_list)
        except LockError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        Path(argv[3]).write_text("\n".join(lines) + "\n")
        return 0
    if len(argv) == 3 and argv[0] == "record":
        conda_list = json.loads(Path(argv[1]).read_text())
        Path(argv[2]).write_text(json.dumps(stack_record(conda_list), indent=2, default=str) + "\n")
        return 0
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
