# FCC-ee Xsuite tuning

Error installation, accelerator correction, and optics and acceptance studies
for the FCC-ee lattice using Xsuite. The workflow starts from a clean lattice,
installs reproducible errors and correction knobs, and gradually increases the
errors while correcting the machine. Separate analysis scripts compare clean
and corrected optics, dynamic aperture (DA), and momentum-dependent survival (MA).

The correction covers horizontal and vertical orbit, beta and alpha functions,
dispersion, transverse coupling, tunes, and first- and second-order chromaticity.
The scripts expose their configuration and intermediate objects for interactive
inspection.

## Environment

Use a Python environment with compatible editable installations of **xtrack,
xdeps, xobjects, and xpart**, together with NumPy and Matplotlib. IPython is
useful for interactive work; `nafflib` is needed only for the optional
amplitude-detuning diagnostic. Tests require `pytest` and `pytest-mock`.

This workflow uses the fixed-response optimizer API in xtrack/xdeps, including
`set_response` and `run_lstsq` with externally supplied Twiss results. It was
developed with xtrack's `fccee-phase-advance-investigation` branch; compatibility
with an arbitrary released Xsuite version is not established. The focused tests
below provide a check of the installed environment.

There is no package installation step for this repository. Run the commands
below from its root, with the intended Python environment activated. For
comparable correction timings, use one BLAS/OMP thread:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
```

Tracking parallelism is configured separately by `TRACKING_THREADS` in `004`.

## Run the correction

The clean input, [`fccee_z_lcc.json`](fccee_z_lcc.json), is included in the
repository. Generated machines are ignored by Git and must be produced locally.
Settings such as the random seed, correction tolerances, and ramp increments
are near the top of the scripts or in the corresponding `corr_*` module.
Input and output paths are resolved relative to the scripts.

| Step | Script | Result |
| --- | --- | --- |
| 000 | [`000_install_errors.py`](000_install_errors.py) | Installs alignment, support, field, and BPM errors; writes `fccee_z_lcc_errors.json`. |
| 001 | [`001_install_correction_knobs.py`](001_install_correction_knobs.py) | Installs correction circuits and records their metadata; writes `fccee_z_lcc_correction_knobs.json`. |
| 002 | [`002_correct.py`](002_correct.py) | Prepares the clean reference, builds optimizers, ramps errors, and performs final refinement. |

```sh
python -u 000_install_errors.py
python -u 001_install_correction_knobs.py
python -u 002_correct.py > /tmp/fccee_correction.log 2>&1
```

Follow the correction in another terminal with
`tail -f /tmp/fccee_correction.log`. A successful correction at full error
strength writes **`response_api_class/machine.json`**, the standard input to the
analysis scripts. A partial result is saved as `response_api_class/partial.json`;
the analysis scripts do not select it automatically.

`002` explicitly creates `reference_twiss` before constructing `FCCeeCorrection`.
The reference has errors and correction trims off, with nominal nonlinear
strengths and chromatic quantities enabled. Correction uses radiation and
tapering off. Both chromatic corrections are skipped during the error ramp and
applied during refinement, first order before second order. All correction
goals are rechecked after changes.

In an interactive session, inspect `reference_twiss`, `correction.optimizers`,
each optimizer's `settings`, and `correction.last_accepted_twiss`. To start over
after changing the error recipe or knob installation, rerun from `000`.
Installers expect inputs without their correction knobs already installed.

## Analyze the corrected machine

Both analysis scripts load `response_api_class/machine.json` and construct clean
and corrected comparisons. They save standalone results and show plots by
default. For interactive plotting, start IPython and run:

```python
%matplotlib
%run 003_analyze_after_correction.py
```

- [`003_analyze_after_correction.py`](003_analyze_after_correction.py) compares
  on-momentum beta functions and scans orbit, beta functions, and tunes versus
  momentum offset in 4D. Results go to `analysis/momentum_scan/`. Failed or
  unreached scan points are retained as NaNs.
- [`004_da_ma_6d.py`](004_da_ma_6d.py) performs 6D DA/MA tracking from the septum
  with active RF and independent mean-radiation tapering for each machine.
  `RADIATION_MODEL` selects mean or quantum radiation. Results normally go to
  `analysis/da_ma_6d/`; suppressing arc-dipole b4 selects `analysis/da_ma_6d_b4_off/`.

Run `004` with `%run 004_da_ma_6d.py` in the same way. Set `SHOW_PLOTS=False` for
batch analysis. Its default tracking length is 300 turns; use `RUN_SCANS=False`
to run preparation and the timing pilot before committing to larger scans.
The optional amplitude-detuning diagnostic is disabled by default.

Correction convergence does not establish full DA/MA acceptance. The MA output
is a transverse-amplitude versus initial-momentum survival map, not a local
Touschek momentum acceptance or lifetime calculation.

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
The [LaTeX source](doc/response_matrices.tex) and PDF are both tracked. With
`latexmk` and `pdflatex` installed:

```sh
make -C doc        # Build doc/response_matrices.pdf
make -C doc clean  # Remove auxiliary files, keeping the PDF
```

[`design.md`](design.md) records design decisions, validation runs, and study
history. Historical results there refer to the code and settings used for those
runs.

## Tests

With the thread settings above, run:

```sh
python -m pytest -q tests
```

These tests include finite-difference checks of analytical responses and checks
of state restoration and correction-knob installation. They do not run the
full FCC-ee correction or the DA/MA scans.

## Data and provenance

The clean lattice was copied from
`xtrack/examples/fcc_ee_solenoid/fccee_z_lcc.json`. The tuning workflow moved from
`xtrack/examples/fccee_tuning` at xtrack commit `46b620d2d`; development now takes
place here. Generated machine JSON files, `response_api_class/`, and `analysis/`
are local outputs ignored by Git. An optional local `from_satya/` study directory
is also ignored and is not required by the standard workflow.

See [LICENSE](LICENSE) for the repository license.
