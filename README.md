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
| 001b | [`001b_prepare_tapering.py`](001b_prepare_tapering.py) | Prepares the clean radiating machine with common arc-bend taper settings and dedicated orbit trims; writes `fccee_z_lcc_tapered.json`. |
| 002 | [`002_correct.py`](002_correct.py) | Prepares the clean reference, builds optimizers, ramps errors, and performs iterative corrections and final refinement. 


A successful correction at full error
strength writes **`response_api_class/machine.json`**, the standard input to the
analysis scripts.
the analysis scripts do not select it automatically.

`002` loads `fccee_z_lcc_tapered.json` from `001b` and explicitly creates
`reference_twiss` before constructing `FCCeeCorrection`.
The reference has errors and ordinary correction trims off, with nominal
nonlinear strengths and chromatic quantities enabled. Correction uses 5D Twiss
with mean radiation, preserving the saved magnet tapers and dedicated tapering
orbit trims. RF phases are refreshed at zero mean
momentum before each workflow measurement and restored when a trial is rejected.
Compensation reuses the previous orbit as its starting guess, and Twiss uses the
orbit from compensation's final track. The saved machine includes orbit guesses
at the correction start, IPD and the septum for independent analysis reloads.
Both chromatic corrections are skipped during the error ramp and
applied during refinement, first order before second order. All correction
goals are rechecked after changes.

### Prepare tapering with arc bends powered in series

`001b` uses the 5D Twiss and phase-only compensation functionality developed on
Xtrack's `dev/tapering` branch. It starts with errors off, zero correction trims,
and nominal nonlinear strengths. After ideal tapering of all magnets, it assigns
each arc's bends their length-weighted average `delta_taper`, including dispersion
suppressors. Other magnets keep their ideal taper settings.

The script alternates RF phase compensation at zero mean momentum with 5D orbit
correction. It uses dedicated `tapering_orbit_corr_*` knobs on the existing
correctors. Set `line['on_tapering_orbit_corr'] = 0` or `1` to disable or enable
these kicks independently of the ordinary `on_orbit_corr` circuit. Changing this
switch does not change RF phases or magnet taper settings.

The full change to common arc settings is attempted first. Failed trials restore
RF phases, bend tapers and tapering orbit trims, then retry with a smaller step
between ideal and common tapering. `INITIAL_INCREMENT`, `MIN_INCREMENT` and
`MAX_ITERATIONS` are exposed in the script. Existing files from `001` without the
dedicated circuit are supported; `001b` installs it when needed.

The ordinary correction circuit does not include or scale the dedicated tapering
trims. `002` ramps errors and ordinary correction knobs from this prepared state;
magnet taper values stay fixed. The correction modules still support explicit 4D
settings for radiation-free studies and tests.

To run the untapered, radiation-free workflow, uncomment the configuration block
near the top of each of `002`, `003` and `004`, and skip `001b`. These blocks select
`TWISS_METHOD='4d'`, `RADIATION_MODEL=None` and the original correction-knob input.
The corrected machine is saved in `response_api_class_4d`; analysis uses separate
`*_4d` output directories. In `004`, RF kicks are disabled so momentum stays
constant during radiation-free tracking. The active defaults remain 5D with radiation.

## Analyze the corrected machine

Analysis scripts load `response_api_class/machine.json` and compare it with the
clean prepared machine in `fccee_z_lcc_tapered.json`. Both retain their dedicated
tapering orbit trims and magnet settings. They save standalone results and show
plots by default. For interactive plotting, start IPython and run:

```python
%matplotlib
%run 003_analyze_after_correction.py
# or
%run 004_da_ma_6d.py
```

- [`003_analyze_after_correction.py`](003_analyze_after_correction.py) compares
  on-momentum beta functions and scans orbit, beta functions, and tunes versus
  starting-momentum offset in 5D, with RF phases held fixed during each scan.
  Results go to `analysis/momentum_scan/`. Failed or unreached scan points are
  retained as NaNs.
- [`004_da_ma_6d.py`](004_da_ma_6d.py) performs 6D DA/MA tracking from the septum
  with active RF, 5D launch optics and the saved magnet taper settings. Only RF
  phases are compensated; magnets are not retapered.
  Zeta may slip on the 5D orbit; subsequent tracking evolves all six coordinates
  without resetting it. `RADIATION_MODEL` selects mean or quantum radiation.
  Results normally go to `analysis/da_ma_6d/`; suppressing arc-dipole b4 selects `analysis/da_ma_6d_b4_off/`.


## Code and documentation

| File | Responsibility |
| --- | --- |
| [`error_recipe.py`](error_recipe.py) | Error specifications, sampling, installation, and BPM alignment. |
| [`correction_workflow.py`](correction_workflow.py) | Clean reference preparation, correction sequencing, error ramp, accepted state, and rollback. |
| [`correction_optimizer.py`](correction_optimizer.py) | Shared optimizer interface with module-specific metrics and goals. |
| `corr_orbit.py`, `corr_optics.py`, `corr_coupling.py` | Orbit, normal optics/dispersion, and coupling/vertical-dispersion correction. |
| [`tapering_workflow.py`](tapering_workflow.py) | Common arc-bend taper settings, 5D orbit correction, and rollback of tapering trials. |
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

