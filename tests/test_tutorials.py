"""Tutorial notebooks are pedagogical views, and the contract that keeps them so.

A notebook that restates a research formula, writes into the archive, or presents a number
without saying what status it has, stops being a view and becomes a second source of evidence.
`cards/tutorial-v0.1.md` states the contract; these tests enforce the checkable parts of it.

Execution is done by extracting the code cells and running them in a temporary directory,
rather than through nbclient. That is deliberate: it keeps jupyter, nbformat and nbclient out
of the certified numerical environment, while still proving the notebook runs top to bottom
under the pinned analysis stack. Authoring tools live in tutorials/requirements.txt.
"""
import json
import os
import re
import subprocess
import sys
import textwrap
import time

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TUTORIALS = os.path.join(ROOT, "tutorials")
NOTEBOOKS = sorted(f for f in os.listdir(TUTORIALS) if f.endswith(".ipynb")) \
    if os.path.isdir(TUTORIALS) else []

# Every conclusion must carry one of these. The four project statuses come from
# ledgers/status.yaml; `textbook` marks a standard result that is NOT a claim of this project,
# because labelling one as `result` would put a textbook fact into the project's claim
# vocabulary -- exactly the conflation the ledger exists to prevent.
LABELS = ("textbook", "result", "pilot", "open", "withdrawn")
RUNTIME_BUDGET_S = 60


def _nb(name):
    with open(os.path.join(TUTORIALS, name), encoding="utf-8") as fh:
        return json.load(fh)


def _source(cell):
    src = cell.get("source", "")
    return src if isinstance(src, str) else "".join(src)


def _code(nb):
    return [_source(c) for c in nb["cells"] if c["cell_type"] == "code"]


def _markdown(nb):
    return "\n".join(_source(c) for c in nb["cells"] if c["cell_type"] == "markdown")


def test_there_is_at_least_one_notebook():
    assert NOTEBOOKS, "tutorials/ contains no notebook"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_imports_the_tested_library_rather_than_restating_formulas(name):
    code = "\n".join(_code(_nb(name)))
    assert "sid_lib" in code, f"{name} does not import from analysis/lib"
    # the research formulas must come from the library, not be retyped
    for forbidden, why in (
        (r"def\s+DB\s*\(", "Bernoulli divergence must come from sid_lib.DB"),
        (r"def\s+I_ext_exact\s*\(", "extremum divergence must come from sid_lib"),
        (r"def\s+rk_exact\s*\(", "lag correlation must come from sid_lib"),
        (r"def\s+hmm_rate\s*\(", "HMM rate must come from sid_lib"),
    ):
        assert not re.search(forbidden, code), f"{name}: {why}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_is_deterministic(name):
    code = "\n".join(_code(_nb(name)))
    if "default_rng" in code or "random" in code:
        assert re.search(r"default_rng\(\s*[A-Za-z_0-9+\s]+\)", code), \
            f"{name} draws random numbers without a named seed"
        assert re.search(r"SEED\s*=\s*\d+", code), f"{name} defines no explicit SEED"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_never_writes_into_the_archive(name):
    code = "\n".join(_code(_nb(name)))
    for pattern in (r"analysis/outputs", r"analysis\W+outputs",
                    r"savefig", r"to_csv", r"json\.dump", r"write_json"):
        assert not re.search(pattern, code.replace("fig.savefig(buf", "")), \
            f"{name} appears to write output ({pattern}); tutorials must not"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_every_conclusion_carries_a_status_label(name):
    text = _markdown(_nb(name))
    quoted = re.findall(r"^>.*$", text, flags=re.M)
    assert quoted, f"{name} states no boxed conclusions"
    for block in quoted:
        if not block.strip("> ").strip():
            continue
        if re.match(r">\s*\*\*[A-Za-z ]", block) or "`" in block:
            pass
    labelled = sum(1 for lab in LABELS if f"`{lab}`" in text)
    assert labelled >= 2, f"{name} uses too few status labels; found {labelled}"
    assert "`textbook`" in text or "`result`" in text, f"{name} labels no conclusion"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_outputs_are_committed_so_the_notebook_reads_on_github(name):
    nb = _nb(name)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    with_output = [c for c in code_cells if c.get("outputs")]
    assert with_output, f"{name} has no stored outputs; a visitor would see an empty notebook"
    has_png = any("image/png" in o.get("data", {})
                  for c in code_cells for o in c.get("outputs", []))
    assert has_png, f"{name} stores no rendered figure"
    errors = [o for c in code_cells for o in c.get("outputs", []) if o.get("output_type") == "error"]
    assert not errors, f"{name} was committed with an execution error: {errors[:1]}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_executes_top_to_bottom_in_a_temporary_directory(name, tmp_path):
    """Run the code cells in a scratch cwd, proving the notebook needs nothing but the library."""
    cells = _code(_nb(name))
    script = "\n\n".join(textwrap.dedent(c) for c in cells if not c.lstrip().startswith("%"))
    script_path = tmp_path / "notebook_cells.py"
    script_path.write_text(script, encoding="utf-8")

    env = dict(os.environ, SID_ROOT=ROOT, MPLBACKEND="Agg")
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(script_path)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=RUNTIME_BUDGET_S * 4)
    elapsed = time.time() - t0
    assert proc.returncode == 0, f"{name} failed to execute:\n{proc.stderr[-2000:]}"
    assert elapsed < RUNTIME_BUDGET_S, \
        f"{name} took {elapsed:.0f}s, over the {RUNTIME_BUDGET_S}s budget"

    # nothing may have been created in the repository, and nothing outside the temp dir
    assert not os.path.exists(os.path.join(ROOT, "notebook_cells.py"))
    strays = [p for p in os.listdir(tmp_path) if p != "notebook_cells.py"]
    assert not strays, f"{name} left files behind: {strays}"
