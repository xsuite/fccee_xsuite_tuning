"""Prepare the clean radiating machine with one bend taper per arc.

Run after 001. Tapering orbit trims are independent of the error-correction
trims used by 002. Inspect tw_ideal, tw and the saved machine interactively.
"""

from pathlib import Path
import xtrack as xt

from corr_orbit import install_tapering_orbit_knobs
from correction_workflow import prepare_reference, DEFAULT_STEPS_R_MATRIX
from tapering_workflow import correct_tapering_orbit

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'fccee_z_lcc_correction_knobs.json'
OUTPUT = HERE / 'fccee_z_lcc_tapered.json'
MAX_ITERATIONS = 20
INITIAL_INCREMENT = 1.
MIN_INCREMENT = 1e-3

line = xt.load(INPUT)
# Also accept files made by 001 before the tapering circuit was introduced.
if 'tapering_orbit' not in line.metadata['correction_knobs']:
    install_tapering_orbit_knobs(line)
tapering_circuit = line.metadata['correction_knobs']['tapering_orbit']
line.set(dict.fromkeys(tapering_circuit['x']['knobs'] + tapering_circuit['y']['knobs'], 0.))
line.configure_radiation(model=None)
prepare_reference(line)
line['on_tapering_orbit_corr'] = 1.
line.configure_radiation(model='mean')
line.compensate_radiation_energy_loss(taper_magnets=True, delta0='zero_mean')
tw_ideal = line.twiss5d(chrom=False, steps_R_matrix=DEFAULT_STEPS_R_MATRIX)

tw = correct_tapering_orbit(
    line, tw_ideal, max_iterations=MAX_ITERATIONS,
    initial_increment=INITIAL_INCREMENT, min_increment=MIN_INCREMENT)
line.to_json(OUTPUT, indent=None)
print(f'Saved {OUTPUT}')
tw['x_ideal'] = tw_ideal.x
tw.plot('x_ideal x')
tw.plot('delta')
