"""Independent tapering circuits and rollback during arc powering changes."""
from types import SimpleNamespace
from pathlib import Path
import sys

import numpy as np
import pytest
import xtrack as xt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import corr_orbit
import tapering_workflow as tapering


def test_independent_orbit_circuits(tmp_path):
    line = xt.Line(elements={'h': xt.Multipole(knl=[0.]),
                             'v': xt.Multipole(ksl=[0.]), 'bpm': xt.Marker()})
    line['base'] = 1e-4
    line.ref['h'].knl[0] = line.ref['base']
    ordinary = corr_orbit._install_orbit_circuit(
        line, 'orbit', 'orbit_corr', 'on_orbit_corr', [['h'], ['v']], ['bpm'])
    dedicated = corr_orbit.install_tapering_orbit_knobs(line)
    line.set(ordinary, [2e-4, 3e-4])
    line.set(dedicated, [4e-4, 5e-4])
    np.testing.assert_allclose([line['h'].knl[0], line['v'].ksl[0]], [-5e-4, 8e-4])
    line['on_tapering_orbit_corr'] = 0.
    np.testing.assert_allclose([line['h'].knl[0], line['v'].ksl[0]], [-1e-4, 3e-4])
    line['on_tapering_orbit_corr'] = 1.
    line['on_orbit_corr'] = 0.
    np.testing.assert_allclose([line['h'].knl[0], line['v'].ksl[0]], [-3e-4, 5e-4])
    line.to_json(tmp_path / 'circuits.json')
    restored = xt.load(tmp_path / 'circuits.json')
    restored['base'] = 2e-4
    np.testing.assert_allclose(restored['h'].knl[0], -2e-4)
    with pytest.raises(ValueError, match='already exist'):
        corr_orbit.install_tapering_orbit_knobs(restored)


@pytest.mark.parametrize('recover', [True, False])
def test_arc_taper_trial_restores_phases_tapers_and_trims(monkeypatch, recover):
    line = xt.Line(elements={
        'b1': xt.Bend(length=1., delta_taper=.01),
        'b2': xt.Bend(length=3., delta_taper=.03),
        'rf': xt.Cavity(phase_taper=.2)})
    line.metadata['tuning_errors'] = dict(magnets={
        'b1': dict(category='arc_dipole', arc_index=0, names=['b1']),
        'b2': dict(category='arc_dipole', arc_index=0, names=['b2'])})
    line['trim_x'] = line['trim_y'] = 0.
    reference = SimpleNamespace(particle_on_co=None, delta=np.zeros(2), s=np.array([0., 4.]))
    calls = []
    def compensate(**kwargs):
        calls.append(line['b1'].delta_taper)
        if len(calls) == 2:
            # The failed full step must have restored these controls before retry.
            assert line['trim_x'] == 0.
            assert line['rf'].phase_taper == .2
        if len(calls) == 1 or not recover:
            line['trim_x'] = 123.
            line['rf'].phase_taper = 456.
            raise RuntimeError('Deliberate failure after changing the machine')
    def optimizer(*args, plane, **kwargs):
        assert kwargs['method'] == '5d'
        assert kwargs['circuit'] == 'tapering_orbit'
        return SimpleNamespace(vary=[SimpleNamespace(name='trim_' + plane)],
                               goal=lambda tw: True, print_metrics=lambda *a, **k: None)
    with monkeypatch.context() as patch:
        patch.setattr(line, 'compensate_radiation_energy_loss', compensate)
        patch.setattr(line, 'twiss', lambda **kwargs: reference)
        patch.setattr(tapering, 'build_orbit_corr_optimizer', optimizer)
        if recover:
            tapering.correct_tapering_orbit(line, reference, log=lambda *a, **k: None)
            np.testing.assert_allclose([line['b1'].delta_taper, line['b2'].delta_taper], .025)
            np.testing.assert_allclose(calls, [.025, .0175, .025])
        else:
            with pytest.raises(RuntimeError, match='Minimum tapering increment'):
                tapering.correct_tapering_orbit(
                    line, reference, min_increment=.25, log=lambda *a, **k: None)
            np.testing.assert_allclose([line['b1'].delta_taper, line['b2'].delta_taper], [.01, .03])
            assert line['rf'].phase_taper == .2
            assert line['trim_x'] == 0.
            assert 'tapering' not in line.metadata


@pytest.mark.parametrize('method,circuit,constraint', [
    ('4d', 'orbit', 'delta0'), ('5d', 'tapering_orbit', 'zeta0')])
def test_orbit_builder_selects_circuit_and_longitudinal_constraint(monkeypatch, method, circuit, constraint):
    import xdeps as xd
    line = xt.Line(elements={'h': xt.Multipole(knl=[0.]),
                             'v': xt.Multipole(ksl=[0.]), 'bpm': xt.Marker()})
    corr_orbit._install_orbit_circuit(
        line, 'orbit', 'orbit_corr', 'on_orbit_corr', [['h'], ['v']], ['bpm'])
    corr_orbit.install_tapering_orbit_knobs(line)
    line.vars.update(dict(dx=0., dy=0., roll=0.))
    line.metadata['tuning_errors'] = dict(bpm_alignment_variables={
        'bpm': dict(shift_x='dx', shift_y='dy', rot_s_rad='roll')})
    reference = xd.Table(dict(name=np.array(['h', 'v', 'bpm']),
                              betx=np.ones(3), mux=np.array([0., .1, .2]), qx=.3),
                         col_names=['name', 'betx', 'mux'])
    class Optimizer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def set_response(self, response):
            self.response = response
    with monkeypatch.context() as patch:
        patch.setattr(corr_orbit, 'CorrectionOptimizer', Optimizer)
        opt = corr_orbit.build_orbit_corr_optimizer(line, reference, plane='x',
                                                    circuit=circuit, method=method)
        assert opt.kwargs['method'] == method
        assert opt.kwargs[constraint] == 0.
        assert ('zeta0' if constraint == 'delta0' else 'delta0') not in opt.kwargs
        assert [v.name for v in opt.kwargs['vary']] == line.metadata['correction_knobs'][circuit]['x']['knobs']
        assert line.twiss_default == {}
