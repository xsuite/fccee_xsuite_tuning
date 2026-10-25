# FCC-ee Xsuite tuning

Error installation, correction, and acceptance studies for the FCC-ee lattice.
This workflow was moved from `xtrack/examples/fccee_tuning` at xtrack commit
`46b620d2d` on branch `fccee-phase-advance-investigation`. Development continues
in this repository; `design.md` records the correction decisions and validation.

Use the existing editable Xsuite installation, including the xtrack changes on
that branch. The analysis scripts also use Matplotlib; the optional amplitude
detuning diagnostic uses `nafflib`. The tests require `pytest` and `pytest-mock`.

Run the scripts in order, with configuration near the top of each file:

1. `000_install_errors.py`: load the clean `fccee_z_lcc.json` and install errors.
2. `001_install_correction_knobs.py`: install correction knobs and switches.
3. `002_correct.py`: prepare an inspectable clean reference, correct the machine,
   and save `response_api_class/machine.json`.
4. `003_analyze_after_correction.py`: inspect orbit, optics, and tunes versus delta.
5. `004_da_ma_6d.py`: compare clean and corrected DA/MA with 6D tracking.

For interactive plots, use IPython with `%matplotlib` and, for example,
`%run 003_analyze_after_correction.py`. Paths are relative to each script's
location. The clean input lattice was copied unchanged from
`xtrack/examples/fcc_ee_solenoid/fccee_z_lcc.json`.

Generated machines, `response_api_class/`, and `analysis/` are local outputs
ignored by Git. Existing outputs and the `from_satya/` study files were preserved
during the move; the standard workflow uses the clean input above.

Run the focused tests from this repository, using one BLAS/OMP thread:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python -m pytest -q tests
```
