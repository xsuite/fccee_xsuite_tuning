"""Prepare arc dipoles powered in series, with independent orbit trims."""

import numpy as np
import xtrack as xt

from corr_orbit import build_orbit_corr_optimizer
from correction_workflow import DEFAULT_STEPS_R_MATRIX


def arc_bend_tapers(line):
    """Return arc bend names, ideal tapers and length-weighted arc averages.

    Use the installed physical-magnet metadata; DS bends belong to the arcs.
    Weighting by magnetic length makes the average independent of splitting.
    """
    arcs = {}
    for magnet in line.metadata['tuning_errors']['magnets'].values():
        if magnet['category'] == 'arc_dipole':
            arcs.setdefault(magnet['arc_index'], []).extend(magnet['names'])
    if not arcs:
        raise ValueError('No arc dipoles found in the error metadata')
    names, ideal, common = [], [], []
    for arc in sorted(arcs):
        arc_names = list(dict.fromkeys(arcs[arc]))
        if any(not isinstance(line.element_dict[n], (xt.Bend, xt.RBend)) for n in arc_names):
            raise ValueError(f'Arc {arc} contains a non-bend element')
        values = np.array([line[n].delta_taper for n in arc_names])
        lengths = np.array([line[n].length for n in arc_names])
        average = np.average(values, weights=lengths)
        names.extend(arc_names)
        ideal.extend(values)
        common.extend([average] * len(arc_names))
    return names, np.array(ideal), np.array(common)


def correct_tapering_orbit(line, reference, *, settings=None, max_iterations=20,
                            initial_increment=1., min_increment=1e-3,
                            mean_delta_tol=1e-9, log=print):
    """Replace ideal bend tapering by arc averages, correcting at each step.

    Other magnets retain their ideal tapers. RF phases are compensated at zero
    mean momentum. Failed trials restore bend tapers, RF phases and dedicated
    orbit trims before reducing the step towards the common arc settings.
    """
    if not 0 < min_increment <= initial_increment <= 1:
        raise ValueError('Require 0 < min_increment <= initial_increment <= 1')
    if max_iterations < 1:
        raise ValueError('max_iterations must be positive')
    names, ideal, common = arc_bend_tapers(line)
    optimizers = [build_orbit_corr_optimizer(
        line, reference, plane=plane, circuit='tapering_orbit', method='5d',
        settings=settings, steps_R_matrix=DEFAULT_STEPS_R_MATRIX.copy())
        for plane in 'xy']
    knobs = [vary.name for opt in optimizers for vary in opt.vary]
    cavities = line.get_table().rows.match(element_type='Cavity').name
    fraction, increment = 0., initial_increment
    tw = reference
    while fraction < 1.:
        target = min(fraction + increment, 1.)
        previous_knobs = np.array(line.get(knobs))
        previous_phases = [line[n].phase_taper for n in cavities]
        previous_tapers = [line[n].delta_taper for n in names]
        previous_twiss = tw
        log(f'Common arc taper fraction: {target:g}', flush=True)
        try:
            for name, value in zip(names, (1 - target) * ideal + target * common):
                line[name].delta_taper = value
            for iteration in range(max_iterations + 1):
                line.compensate_radiation_energy_loss(
                    taper_magnets=False, delta0='zero_mean', verbose=False)
                tw = line.twiss(
                    method='5d', zeta0=0., chrom=False, radiation_integrals=False,
                    co_guess=tw.particle_on_co,
                    steps_R_matrix=DEFAULT_STEPS_R_MATRIX.copy())
                mean_delta = np.trapezoid(tw.delta, tw.s) / (tw.s[-1] - tw.s[0])
                for opt in optimizers:
                    opt.print_metrics(tw, log=log)
                if all(opt.goal(tw) for opt in optimizers) and abs(mean_delta) < mean_delta_tol:
                    break
                if iteration == max_iterations:
                    raise RuntimeError('Tapering orbit correction did not converge')
                for opt in optimizers:
                    opt.run_lstsq(action_results=[tw])
        except (ValueError, RuntimeError, xt.twiss.ClosedOrbitSearchError) as err:
            line.set(knobs, previous_knobs)
            for name, value in zip(cavities, previous_phases):
                line[name].phase_taper = value
            for name, value in zip(names, previous_tapers):
                line[name].delta_taper = value
            tw = previous_twiss
            increment /= 2
            log(f'Rejected: {err}; reduced increment to {increment:g}', flush=True)
            if increment < min_increment:
                raise RuntimeError(f'Minimum tapering increment reached at {fraction:g}') from err
            continue
        fraction = target
        increment = min(2 * increment, 1.)
    line.metadata['tapering'] = dict(
        arc_bend_names=names, ideal_bend_tapers=ideal.tolist(),
        common_bend_tapers=common.tolist(), orbit_circuit='tapering_orbit',
        mean_delta=float(mean_delta))
    return tw
