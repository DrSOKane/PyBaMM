#
# Tests for the lithium-ion DFN model
#
import pybamm
from pybamm.solvers.scikits_ode_solver import scikits_odes_spec
import tests

import numpy as np
import unittest


@unittest.skipIf(scikits_odes_spec is None, "scikits.odes not installed")
class TestDFN(unittest.TestCase):
    def test_basic_processing(self):
        model = pybamm.lithium_ion.DFN()
        var = pybamm.standard_spatial_vars
        var_pts = {var.x_n: 10, var.x_s: 10, var.x_p: 10, var.r_n: 5, var.r_p: 5}
        modeltest = tests.StandardModelTest(model, var_pts=var_pts)
        modeltest.test_all()

    def test_optimisations(self):
        model = pybamm.lithium_ion.DFN()
        optimtest = tests.OptimisationsTest(model)

        original = optimtest.evaluate_model()
        simplified = optimtest.evaluate_model(simplify=True)
        using_known_evals = optimtest.evaluate_model(use_known_evals=True)
        simp_and_known = optimtest.evaluate_model(simplify=True, use_known_evals=True)
        simp_and_python = optimtest.evaluate_model(simplify=True, to_python=True)
        np.testing.assert_array_almost_equal(original, simplified)
        np.testing.assert_array_almost_equal(original, using_known_evals)
        np.testing.assert_array_almost_equal(original, simp_and_known)
        np.testing.assert_array_almost_equal(original, simp_and_python)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
