#
# Tests for the simple ODE model
#
import pybamm
import tests

import unittest
import numpy as np


class TestSimpleODEModel(unittest.TestCase):
    def test_basic_processing(self):
        model = pybamm.SimpleODEModel()

        modeltest = tests.StandardModelTest(model)
        modeltest.test_all()

    def test_solution(self):
        whole_cell = ["negative electrode", "separator", "positive electrode"]
        model = pybamm.SimpleODEModel()

        # discretise and solve
        disc = model.default_discretisation
        combined_submesh = disc.mesh.combine_submeshes(*whole_cell)
        disc.process_model(model)
        t_eval = np.linspace(0, 1, 100)
        solver = model.default_solver
        solver.solve(model, t_eval)
        T, Y = solver.t, solver.y

        # check output
        np.testing.assert_array_almost_equal(
            model.variables["a"].evaluate(T, Y), 2 * T[np.newaxis, :]
        )
        np.testing.assert_array_almost_equal(
            model.variables["b broadcasted"].evaluate(T, Y),
            np.ones((combined_submesh.npts, T.size)),
        )
        np.testing.assert_array_almost_equal(
            model.variables["c broadcasted"].evaluate(T, Y),
            np.ones(
                sum([disc.mesh[d].npts for d in ["negative electrode", "separator"]])
            )[:, np.newaxis]
            * np.exp(-T),
        )


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
