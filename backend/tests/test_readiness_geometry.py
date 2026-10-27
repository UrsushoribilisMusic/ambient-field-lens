"""Measured-geometry algorithm tests using explicitly synthetic coordinates."""
from dataclasses import replace
import unittest
import numpy as np

from readiness.checks import Frame
from readiness.geometry import Correspondence, fit_registration, rasterize_footprint, project


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.matrix = ((2., .2, 20.), (.1, 1.5, 20.), (.001, .002, 1.))
        self.fit = self.pairs([(0., 0.), (20., 0.), (20., 20.), (0., 20.)])
        self.validation = self.pairs([(5., 5.), (15., 5.), (15., 15.), (5., 15.)])
        self.identity = dict(camera='camera', rig='rig', surface_pose='pose', source_frame_sha256='synthetic')
        self.frame = Frame('current-synthetic', 100, 100, 0, 'camera', 'rig', 'pose', 'pen', 'session')

    def pairs(self, points):
        return [Correspondence(p, tuple(q)) for p, q in zip(points, project(self.matrix, points))]

    def registration(self, fit=None, validation=None):
        return fit_registration(self.fit if fit is None else fit,
                                self.validation if validation is None else validation, **self.identity)

    def test_normalized_dlt_recovers_projective_mapping(self):
        registration = self.registration()
        self.assertLess(registration.max_validation_error_px, 1e-8)
        np.testing.assert_allclose(project(registration.matrix, [(8, 12)]), project(self.matrix, [(8, 12)]), atol=1e-8)

    def test_cannot_validate_using_fitting_points(self):
        with self.assertRaises(ValueError):
            self.registration(validation=self.fit)

    def test_collinear_or_incomplete_points_rejected(self):
        for fit in (self.fit[:3], self.pairs([(0, 0), (1, 0), (2, 0), (3, 0)])):
            with self.subTest(fit=fit), self.assertRaises(ValueError):
                self.registration(fit=fit)

    def test_held_out_error_does_not_silently_accept_mapping(self):
        bad = list(self.validation)
        bad[0] = replace(bad[0], image_px=(80, 80))
        with self.assertRaises(ValueError):
            self.registration(validation=bad)

    def test_moved_surface_rejects_old_registration(self):
        with self.assertRaises(ValueError):
            rasterize_footprint(replace(self.frame, surface_pose='moved'), self.registration(), [(5, 5), (10, 5), (10, 10), (5, 10)])

    def test_no_extrapolation_beyond_measured_plane(self):
        with self.assertRaises(ValueError):
            rasterize_footprint(self.frame, self.registration(), [(30, 30), (35, 30), (35, 35), (30, 35)])

    def test_margin_increases_conservative_cells(self):
        p = [(5, 5), (10, 5), (10, 10), (5, 10)]
        small = rasterize_footprint(self.frame, self.registration(), p, margin_mm=0, required_margin_mm=0)
        large = rasterize_footprint(self.frame, self.registration(), p)
        self.assertTrue(small.cells < large.cells)
        self.assertEqual(large.frame_sha256, self.frame.sha256)

    def test_boundary_touching_cells_are_included(self):
        r = replace(self.registration(), matrix=((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)))
        f = rasterize_footprint(self.frame, r, [(5, 5), (8, 5), (8, 8), (5, 8)], margin_mm=0, required_margin_mm=0)
        self.assertIn((4, 5), f.cells)
        self.assertIn((8, 8), f.cells)

    def test_offscreen_and_self_intersecting_footprints_rejected(self):
        for polygon in ([(-50, -50), (-40, -50), (-40, -40), (-50, -40)],
                        [(5, 5), (10, 10), (5, 10), (10, 5)]):
            with self.subTest(polygon=polygon), self.assertRaises(ValueError):
                rasterize_footprint(self.frame, self.registration(), polygon)


if __name__ == '__main__':
    unittest.main()
