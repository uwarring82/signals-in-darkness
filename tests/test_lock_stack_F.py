"""The roadmap-F pip lock helper refuses what it must, on fixtures (note 28 §10).

Nothing is installed or downloaded; the report and conda listings are synthetic.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lock_stack_F as lock  # noqa: E402

CONDA = [{"name": "numpy", "channel": "conda-forge"}, {"name": "ruamel.yaml", "channel": "conda-forge"},
         {"name": "cffconvert", "channel": "pypi"}]


def entry(name, version, sha=None, legacy=None):
    archive = {}
    if sha:
        archive["hashes"] = {"sha256": sha}
    if legacy:
        archive["hash"] = legacy
    return {"metadata": {"name": name, "version": version},
            "download_info": {"url": f"https://files.example/{name}-{version}.whl", "archive_info": archive}}


def test_lock_lines_are_hash_pinned_and_sorted():
    report = {"install": [entry("pykwalify", "1.8.0", sha="b" * 64), entry("Click", "8.1.7", sha="a" * 64)]}
    assert lock.pip_lock_lines(report, CONDA) == [f"Click==8.1.7 --hash=sha256:{'a' * 64}",
                                                  f"pykwalify==1.8.0 --hash=sha256:{'b' * 64}"]


def test_pips_legacy_hash_field_is_accepted():
    report = {"install": [entry("jsonschema", "3.2.0", legacy="sha256=" + "c" * 64)]}
    assert lock.pip_lock_lines(report, CONDA) == [f"jsonschema==3.2.0 --hash=sha256:{'c' * 64}"]


@pytest.mark.parametrize("name", ["numpy", "ruamel_yaml", "Ruamel.YAML"])
def test_pip_may_not_replace_a_conda_package(name):
    with pytest.raises(lock.LockError):
        lock.pip_lock_lines({"install": [entry(name, "9.9", sha="d" * 64)]}, CONDA)


def test_a_pip_listed_entry_in_conda_list_is_not_treated_as_conda_provided():
    report = {"install": [entry("cffconvert", "2.0.0", sha="e" * 64)]}
    assert lock.pip_lock_lines(report, CONDA) == [f"cffconvert==2.0.0 --hash=sha256:{'e' * 64}"]


def test_an_entry_without_sha256_is_refused():
    with pytest.raises(lock.LockError):
        lock.pip_lock_lines({"install": [entry("requests", "2.32.3", legacy="md5=" + "f" * 32)]}, CONDA)
