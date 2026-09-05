"""Tutorial notebooks are pedagogical views, and the contract that keeps them so.

A notebook that restates a research formula, writes into the archive, or presents a number
without saying what standing it has, stops being a view and becomes a second source of evidence.
`cards/tutorial-v0.1.md` states the contract; these tests enforce it.

Execution extracts the code cells and runs them in a temporary directory rather than going
through nbclient. That keeps jupyter, nbformat and nbclient out of the certified numerical
environment while still proving the notebook runs top to bottom under the pinned analysis stack.
Authoring tools live in `tutorials/requirements.txt`. The contract therefore requires plain
Python cells: no line or cell magics, no shell escapes.

An earlier version of this file overclaimed. It asserted nothing about conclusion labels, never
checked claim ids against the ledger, did not hash the protected directories around execution,
and never compared freshly produced output with what was committed — so a notebook whose stored
numbers were stale could pass. Each of those is now a real check.
"""
import hashlib
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

# Two namespaces, deliberately distinct. `worked example` is a calculation done here for
# teaching with standard methods; it is NOT a claim of this project and must not inherit the
# standing of one. A ledger claim is written "C25 - result" and is checked against
# ledgers/status.yaml, id and status.
WORKED = "worked example"
CLAIM_STATUSES = ("result", "pilot", "open", "withdrawn")
CONCLUSION = re.compile(r"^>\s*\*\*(.+?)\*\*")   # applied to the FIRST line of a block only
CLAIM_LABEL = re.compile(r"^(C\d+)\s*[-—]\s*(" + "|".join(CLAIM_STATUSES) + r")$")

PROTECTED = ("analysis/outputs", "figures")
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


def _streams(nb):
    """Concatenated stdout of every code cell, as committed."""
    out = []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                txt = o.get("text", "")
                out.append(txt if isinstance(txt, str) else "".join(txt))
    return "".join(out)


def _conclusion_labels(text):
    """Label opening each blockquote block.

    Only the first line of a block carries the label; bold text later in the same quote is
    ordinary emphasis. Matching every quoted line, as an earlier version did, read
    "**145 at the median**" as a label.
    """
    labels, in_block = [], False
    for line in text.splitlines():
        quoted = line.lstrip().startswith(">")
        if quoted and not in_block:
            m = CONCLUSION.match(line.lstrip())
            labels.append(m.group(1).strip() if m else None)
        in_block = quoted
    return labels


def _ledger():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import pathlib

    import build_site
    rows = build_site.load_yaml_list(pathlib.Path(ROOT) / "ledgers" / "status.yaml")
    return {r["id"]: r["status"] for r in rows}


def _hash_tree(rel):
    """Hash of every file under a protected directory, for before/after comparison."""
    base = os.path.join(ROOT, rel)
    digest = hashlib.sha256()
    for dirpath, _, files in os.walk(base):
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            digest.update(os.path.relpath(path, base).encode())
            with open(path, "rb") as fh:
                digest.update(fh.read())
    return digest.hexdigest()


def _strip_env(text):
    """Drop provenance lines. Which interpreter ran the notebook is expected to differ."""
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("[env]"))


def _canonical_numbers(text):
    """Numbers in a stream, rounded to 4 significant figures.

    Comparison is at 4 significant figures rather than exact so that a different interpreter or
    library patch level does not fail the test on a last-digit difference; the project measures
    that spread at ~1e-12, far below this. A genuinely stale number moves much more than that.
    """
    out = []
    for tok in re.findall(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", text):
        try:
            v = float(tok)
        except ValueError:
            continue
        out.append(0.0 if v == 0 else float(f"{v:.4g}"))
    return out


def _pins(path):
    out = {}
    for line in (open(os.path.join(ROOT, path), encoding="utf-8").read().splitlines()):
        line = line.split("#", 1)[0].strip()
        if "==" in line:
            name, _, ver = line.partition("==")
            out[name.strip().lower()] = ver.strip()
    return out


def test_shared_numerical_pins_match_the_root_environment():
    """A notebook must produce the numbers the certified environment would.

    The tutorial environment is standalone, so nothing forces its numpy/scipy/matplotlib to
    agree with the root pins except this test.
    """
    root, tut = _pins("requirements.txt"), _pins("tutorials/requirements.txt")
    shared = ("numpy", "scipy", "matplotlib")
    for pkg in shared:
        assert pkg in tut, f"tutorials/requirements.txt does not pin {pkg}"
        assert pkg in root, f"requirements.txt does not pin {pkg}"
        assert tut[pkg] == root[pkg], \
            f"{pkg}: tutorial pins {tut[pkg]}, certified environment pins {root[pkg]}"
    for pkg in tut:
        if pkg in root and pkg not in shared:
            assert tut[pkg] == root[pkg], \
                f"{pkg} appears in both files at different versions: {tut[pkg]} vs {root[pkg]}"


def test_tutorial_environment_excludes_the_certification_only_packages():
    """cffconvert must not be installed alongside the tutorial toolchain.

    jupyterlab pulls jsonschema >= 4, violating cffconvert's jsonschema<4 constraint. Keeping
    cffconvert out of this file is what makes the two environments independently installable.
    """
    tut = _pins("tutorials/requirements.txt")
    for pkg in ("cffconvert", "pytest"):
        assert pkg not in tut, \
            f"{pkg} belongs to the certified environment and must not be a tutorial dependency"


def test_no_tutorial_instruction_installs_into_the_certified_environment():
    """The documented route must not corrupt `sid`.

    An earlier revision told readers to `conda activate sid` and then pip install the tutorial
    requirements, which reproduces exactly the dependency conflict the separation exists to
    avoid -- and breaks the CITATION.cff validation gate.
    """
    # The defect is installing the TUTORIAL requirements into `sid`, not activating `sid`,
    # which the root README does correctly for the analysis path. So look for the two things
    # occurring together within one instruction block.
    names_sid = re.compile(r"\bsid\b(?!-)")
    for rel in ("tutorials/README.md", "tutorials/requirements.txt",
                "cards/tutorial-v0.1.md", "README.md"):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        # instruction blocks: fenced code, or the comment header of a requirements file
        blocks = re.findall(r"```[a-z]*\n(.*?)```", text, flags=re.S)
        blocks += ["\n".join(l.lstrip("# ") for l in text.splitlines() if l.startswith("#"))]
        for block in blocks:
            # Only COMMAND lines count. Prose warning against installing into `sid` mentions
            # both, and must not be mistaken for an instruction to do it.
            commands = [l for l in block.splitlines()
                        if re.search(r"\b(conda|pip install|pip\s+install)\b", l)]
            installs = [l for l in commands if "tutorials/requirements.txt" in l]
            if not installs:
                continue
            offender = next((l for l in commands if names_sid.search(l)), None)
            assert not offender, (
                f"{rel}: an instruction block installs tutorials/requirements.txt while "
                f"referring to the certified environment `sid`. Tutorial tooling belongs in a "
                f"standalone environment; installing it into `sid` pulls jsonschema >= 4 and "
                f"breaks the CITATION.cff validation gate.\n  command: {offender.strip()!r}")


def test_there_is_at_least_one_notebook():
    assert NOTEBOOKS, "tutorials/ contains no notebook"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_imports_the_tested_library_rather_than_restating_formulas(name):
    code = "\n".join(_code(_nb(name)))
    assert "sid_lib" in code, f"{name} does not import from analysis/lib"
    for forbidden, why in (
        (r"def\s+DB\s*\(", "Bernoulli divergence must come from sid_lib.DB"),
        (r"def\s+I_ext_exact\s*\(", "extremum divergence must come from sid_lib"),
        (r"def\s+rk_exact\s*\(", "lag correlation must come from sid_lib"),
        (r"def\s+hmm_rate\s*\(", "HMM rate must come from sid_lib"),
    ):
        assert not re.search(forbidden, code), f"{name}: {why}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_cells_are_plain_python(name):
    """No magics or shell escapes: the tests run cells directly, without a Jupyter kernel."""
    for i, cell in enumerate(_code(_nb(name))):
        for line in cell.splitlines():
            stripped = line.strip()
            assert not stripped.startswith(("%", "!", "%%")), \
                f"{name} cell {i} uses a magic or shell escape: {stripped[:40]!r}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_is_deterministic(name):
    code = "\n".join(_code(_nb(name)))
    if "default_rng" in code or "random" in code:
        assert re.search(r"SEED\s*=\s*\d+", code), f"{name} defines no explicit SEED"
        assert not re.search(r"default_rng\(\s*\)", code), f"{name} seeds a generator with nothing"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_source_declares_no_writes(name):
    code = "\n".join(_code(_nb(name)))
    stripped = code.replace('fig.savefig(buf, format="png", bbox_inches="tight")', "")
    for pattern in (r"analysis/outputs", r"savefig", r"to_csv", r"json\.dump", r"write_json",
                    r"open\([^)]*['\"]w"):
        assert not re.search(pattern, stripped), \
            f"{name} appears to write output ({pattern}); tutorials must not"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_every_conclusion_is_labelled_and_claim_labels_match_the_ledger(name):
    """Each quoted conclusion must open with a label, and a claim label must be true."""
    text = _markdown(_nb(name))
    labels = _conclusion_labels(text)
    assert labels, f"{name} states no quoted conclusions"
    assert None not in labels, (
        f"{name}: a quoted conclusion opens without a label. Every block must begin "
        f"'> **worked example**' or '> **C<id> - <status>**'")
    ledger = _ledger()
    saw_claim = False
    for label in labels:
        label = label.strip()
        if label == WORKED:
            continue
        m = CLAIM_LABEL.match(label)
        assert m, (f"{name}: conclusion label {label!r} is neither {WORKED!r} nor "
                   f"'C<id> - <status>'")
        cid, status = m.group(1), m.group(2)
        assert cid in ledger, f"{name} cites {cid}, which is not in ledgers/status.yaml"
        assert ledger[cid] == status, \
            f"{name} labels {cid} as '{status}' but the ledger says '{ledger[cid]}'"
        saw_claim = True
    assert WORKED in " ".join(labels), f"{name} labels nothing as a worked example"
    assert saw_claim, f"{name} cites no ledger claim; a tutorial should connect to the record"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_outputs_are_committed_so_the_notebook_reads_on_github(name):
    nb = _nb(name)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert any(c.get("outputs") for c in code_cells), \
        f"{name} has no stored outputs; a visitor would see an empty notebook"
    assert any("image/png" in o.get("data", {})
               for c in code_cells for o in c.get("outputs", [])), \
        f"{name} stores no rendered figure"
    errors = [o for c in code_cells for o in c.get("outputs", []) if o.get("output_type") == "error"]
    assert not errors, f"{name} was committed with an execution error: {errors[:1]}"


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_executes_freshly_and_its_committed_output_is_not_stale(name, tmp_path):
    """Run the cells in a scratch cwd; the archive must be untouched and the numbers current."""
    nb = _nb(name)
    cells = [c for c in _code(nb) if c.strip()]
    script = "\n\n".join(textwrap.dedent(c) for c in cells)
    script_path = tmp_path / "notebook_cells.py"
    script_path.write_text(script, encoding="utf-8")

    before = {rel: _hash_tree(rel) for rel in PROTECTED}
    env = dict(os.environ, SID_ROOT=ROOT, MPLBACKEND="Agg")
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(script_path)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=RUNTIME_BUDGET_S * 4)
    elapsed = time.time() - t0
    after = {rel: _hash_tree(rel) for rel in PROTECTED}

    assert proc.returncode == 0, f"{name} failed to execute:\n{proc.stderr[-2000:]}"
    assert elapsed < RUNTIME_BUDGET_S, \
        f"{name} took {elapsed:.0f}s, over the {RUNTIME_BUDGET_S}s budget"
    for rel in PROTECTED:
        assert before[rel] == after[rel], f"{name} modified {rel}/ during execution"
    strays = [p for p in os.listdir(tmp_path) if p != "notebook_cells.py"]
    assert not strays, f"{name} left files behind: {strays}"

    fresh = _canonical_numbers(_strip_env(proc.stdout))
    committed = _canonical_numbers(_strip_env(_streams(nb)))
    assert committed, f"{name} committed no printed output to compare against"
    assert fresh == committed, (
        f"{name}: committed output is stale -- re-execute the notebook and commit it.\n"
        f"  {len(committed)} committed numbers, {len(fresh)} fresh\n"
        f"  first difference: "
        + next((f"committed {c} vs fresh {f}" for c, f in zip(committed, fresh) if c != f),
               "lengths differ"))
