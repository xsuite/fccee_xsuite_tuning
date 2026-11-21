"""Explicit optics settings and RF compensation shared by tuning and analysis."""


def twiss_settings(kwargs):
    settings = dict(kwargs)
    method = settings.setdefault('method', '4d')
    if 'delta0' not in settings and 'zeta0' not in settings:
        if method == '4d':
            settings['delta0'] = 0.
        elif method == '5d':
            settings['zeta0'] = 0.
    return settings


def compensate_rf_phases(line, co_guess=None):
    """Compensate at zero mean momentum and return the resulting orbit guess.

    The last element-by-element track starts on the orbit found by compensation.
    RF rephasing anchors that orbit at zeta=0. Reuse its entrance coordinates so
    the following Twiss does not search from an orbit for the previous RF phases.
    """
    if co_guess is None:
        co_guess = line.metadata.get('orbit_guesses', {}).get(line.element_names[0])
    line.compensate_radiation_energy_loss(
        taper_magnets=False, delta0='zero_mean', verbose=False, co_guess=co_guess)
    mon = line.record_last_track
    guess = {key: float(getattr(mon, key)[0, 0])
             for key in ('x', 'px', 'y', 'py', 'delta')}
    guess['zeta'] = 0.
    return guess
