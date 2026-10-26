# FCC-ee Xsuite tuning

Installation of misalignments and multipolar imperfection followed by correction
for the FCC-ee lattice using Xsuite. The workflow starts from a clean lattice,
installs reproducible errors and correction knobs, and gradually increases the
errors while correcting the machine. Separate analysis scripts compare clean
and corrected optics, dynamic aperture (DA), and momentum-dependent survival (MA).

The correction covers horizontal and vertical orbit, beta and alpha functions,
dispersion, transverse coupling, tunes, and first- and second-order chromaticity.
The scripts expose their configuration and intermediate objects for interactive
inspection.

The code is based on the material available in the
[FCC-ee optics tuning WG meetings](https://indico.cern.ch/category/18470/).

## Environment

Install the production Xsuite package in your Python environment:

```sh
pip install xsuite
```

The required optimizer functionality is included in the production versions.
Matplotlib is used for analysis plots, and IPython is useful for interactive
work. `nafflib` is needed only for the optional amplitude-detuning diagnostic.
Tests require `pytest` and `pytest-mock`.

There is no package installation step for this repository. Run the commands
below from its root, with the intended Python environment activated.

## Run the correction

An example lattice without errors, [`fccee_z_lcc.json`](fccee_z_lcc.json), is included in the repository.
Settings such as the random seed, correction tolerances, and ramp increments
are near the top of the scripts or in the corresponding `corr_*` module.
Input and output paths are resolved relative to the scripts.

| Step | Script | Result |
| --- | --- | --- |
| 000 | [`000_install_errors.py`](000_install_errors.py) | Installs alignment, field, and BPM errors; writes `fccee_z_lcc_errors.json`. |
| 001 | [`001_install_correction_knobs.py`](001_install_correction_knobs.py) | Installs correction circuits and records their metadata; writes `fccee_z_lcc_correction_knobs.json`. |
| 002 | [`002_correct.py`](002_correct.py) | Prepares the clean reference, builds optimizers, ramps errors, and performs iterative corrections and final refinement. 


A successful correction at full error
strength writes **`response_api_class/machine.json`**, the standard input to the
analysis scripts.
the analysis scripts do not select it automatically.

`002` explicitly creates `reference_twiss` before constructing `FCCeeCorrection`.
The reference has errors and correction trims off, with nominal nonlinear
strengths and chromatic quantities enabled. Correction uses radiation and
tapering off. Both chromatic corrections are skipped during the error ramp and
applied during refinement, first order before second order. All correction
goals are rechecked after changes.

## Analyze the corrected machine

Analysis scripts load `response_api_class/machine.json` and construct clean
vs corrected comparisons. They save standalone results and show plots by
default. For interactive plotting, start IPython and run:

```python
%matplotlib
%run 003_analyze_after_correction.py
# or
%run 004_da_ma_6d.py
```

- [`003_analyze_after_correction.py`](003_analyze_after_correction.py) compares
  on-momentum beta functions and scans orbit, beta functions, and tunes versus
  momentum offset in 4D. Results go to `analysis/momentum_scan/`. Failed or
  unreached scan points are retained as NaNs.
- [`004_da_ma_6d.py`](004_da_ma_6d.py) performs 6D DA/MA tracking from the septum
  with active RF and independent mean-radiation tapering for each machine.
  `RADIATION_MODEL` selects mean or quantum radiation. Results normally go to
  `analysis/da_ma_6d/`; suppressing arc-dipole b4 selects `analysis/da_ma_6d_b4_off/`.


## Code and documentation

| File | Responsibility |
| --- | --- |
| [`error_recipe.py`](error_recipe.py) | Error specifications, sampling, installation, and BPM alignment. |
| [`correction_workflow.py`](correction_workflow.py) | Clean reference preparation, correction sequencing, error ramp, accepted state, and rollback. |
| [`correction_optimizer.py`](correction_optimizer.py) | Shared optimizer interface with module-specific metrics and goals. |
| `corr_orbit.py`, `corr_optics.py`, `corr_coupling.py` | Orbit, normal optics/dispersion, and coupling/vertical-dispersion correction. |
| `corr_tune.py`, `corr_chromaticity.py`, `corr_second_order_chrom.py` | Tune and chromatic corrections. |
| [`response_builders.py`](response_builders.py) | Analytical orbit, normal-quadrupole, and skew-quadrupole responses. |
| [`tests/`](tests/) | Focused installation, response, workflow, and analysis checks. |

Read the [response-matrix note](doc/response_matrices.pdf) for the equations,
signs, units, knob mapping, and numerical derivatives. Its appendices explain
Gauss–Legendre integration and optics propagation within quadrupoles.

## Tests

With the thread settings above, run:

```sh
python -m pytest -q tests
```

These tests include finite-difference checks of analytical responses and checks
of state restoration and correction-knob installation. They do not run the
full FCC-ee correction or the DA/MA scans.

