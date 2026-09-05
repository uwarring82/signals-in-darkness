# Tutorials

Pedagogical views of the project, in the order a reader should meet them. **They are never a
source of scientific evidence**: every number is computed live from `analysis/lib`, the same
tested code the research runs use, and every conclusion carries a status label.

| notebook | question | status |
|---|---|---|
| `00_how_many_coin_tosses.ipynb` | How many tosses to detect a change in a coin's bias? | available |
| `01_when_the_coin_has_memory.ipynb` | What changes when the bias is an AR(1) process? | planned |
| `02_from_coin_to_quantum_sensor.ipynb` | The binary link, contrast, and the two operating points | planned |
| `03_detection_is_not_identification.ipynb` | Why detecting a change is not interpreting it | planned |

A single-shot quantum measurement **is** a Bernoulli observation, so the coin is not an analogy.
The mathematical language does not change between notebook 00 and notebook 03; only the meaning
of the probability does.

## Reading them

The notebooks are committed **with their outputs**, so they can be read on GitHub with nothing
installed. To re-execute:

```
conda create -n sid-tutorial -c conda-forge python=3.12.14 pip
conda activate sid-tutorial
python -m pip install -r tutorials/requirements.txt
python -m pip check
jupyter lab tutorials/
```

**Create this environment fresh; do not install it into `sid`.** The tutorial toolchain pulls
`jsonschema >= 4`, which violates `cffconvert`'s `jsonschema<4` constraint and breaks the
`CITATION.cff` validation gate that the certified environment exists to run. The numerical
packages are pinned identically in both, so a notebook executed here produces the numbers the
certified environment would; `tests/test_tutorials.py` asserts that those shared pins agree.

## Contract

Enforced by `tests/test_tutorials.py`, which runs in the certified environment and needs none of
the packages above:

- research formulas are **imported** from `analysis/lib`, never restated;
- every random result has a named seed;
- nothing is written into `analysis/outputs/` or `figures/`;
- every quoted conclusion opens with `**worked example**` — computed here for teaching, not a
  claim of this project — or `**C·· — status**`, whose id and status are checked against
  `ledgers/status.yaml`;
- cells are plain Python: no magics, no shell escapes;
- each notebook executes top to bottom in a temporary directory in well under a minute, leaves
  no files behind, changes nothing under `analysis/outputs/` or `figures/` (hashed before and
  after), and its committed numbers match a fresh run to four significant figures.

Governed by `cards/tutorial-v0.1.md`, which is outside the stopping rule of
`cards/repo-seed-v0.2.md`.
