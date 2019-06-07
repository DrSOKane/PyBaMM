#
# Tests for updating parameter values
#
import pybamm

import unittest
import numpy as np
import tests


class TestUpdateParameters(unittest.TestCase):
    def test_update_parameters_eqn(self):
        a = pybamm.Scalar(1)
        b = pybamm.Scalar(2, name="test parameter")
        c = pybamm.Scalar(3)
        eqn = a + b * c
        self.assertEqual(eqn.evaluate(), 7)

        parameter_values = pybamm.ParameterValues({"test parameter": 3})
        eqn_changed = parameter_values.update_scalars(eqn)
        self.assertEqual(eqn_changed.evaluate(), 10)

    def test_set_and_update_parameters(self):
        a = pybamm.Scalar(1)
        b = pybamm.Parameter(name="test parameter")
        c = pybamm.Scalar(3)
        eqn = a + b * c

        parameter_values = pybamm.ParameterValues({"test parameter": 2})
        eqn_processed = parameter_values.process_symbol(eqn)
        self.assertEqual(eqn_processed.evaluate(), 7)

        parameter_values = pybamm.ParameterValues({"test parameter": 3})
        eqn_updated = parameter_values.update_scalars(eqn_processed)
        self.assertEqual(eqn_updated.evaluate(), 10)

    def test_update_model(self):
        # standard model
        model1 = pybamm.ReactionDiffusionModel()
        modeltest1 = tests.StandardModelTest(model1)
        t_eval = np.linspace(0, 0.9)

        modeltest1.test_all(t_eval=t_eval)
        Y1 = modeltest1.solution.y

        # double initial conditions
        model2 = pybamm.ReactionDiffusionModel()
        # process and solve the model a first time
        modeltest2 = tests.StandardModelTest(model2)
        modeltest2.test_all()
        # process and solve with updated parameter values
        parameter_values_update = pybamm.ParameterValues(
            base_parameters=model2.default_parameter_values,
            optional_parameters={"Typical current [A]": 2},
        )
        modeltest2.test_update_parameters(parameter_values_update)
        modeltest2.test_solving(t_eval=t_eval)
        Y2 = modeltest2.solution.y

        # results should be different
        self.assertNotEqual(np.linalg.norm(Y1 - Y2), 0)

    def test_update_geometry(self):
        # standard model
        model1 = pybamm.ReactionDiffusionModel()
        modeltest1 = tests.StandardModelTest(model1)
        t_eval = np.linspace(0, 0.9)
        modeltest1.test_all(t_eval=t_eval)

        T1, Y1 = modeltest1.solution.t, modeltest1.solution.y

        # trying to update the geometry fails
        parameter_values_update = pybamm.ParameterValues(
            base_parameters=model1.default_parameter_values,
            optional_parameters={
                "Negative electrode width [m]": 0.000002,
                "Separator width [m]": 0.000003,
                "Positive electrode width [m]": 0.000004,
            },
        )
        with self.assertRaisesRegex(ValueError, "geometry has changed"):
            modeltest1.test_update_parameters(parameter_values_update)

        # instead we need to make a new model and re-discretise
        model2 = pybamm.ReactionDiffusionModel()
        parameter_values_update = pybamm.ParameterValues(
            base_parameters=model2.default_parameter_values,
            optional_parameters={
                "Negative electrode width [m]": 0.000002,
                "Separator width [m]": 0.000003,
                "Positive electrode width [m]": 0.000004,
            },
        )
        # nb: need to be careful make parameters a reasonable size
        modeltest2 = tests.StandardModelTest(model2)
        modeltest2.test_all(param=parameter_values_update, t_eval=t_eval)
        T2, Y2 = modeltest2.solution.t, modeltest2.solution.y
        # results should be different
        c1 = pybamm.ProcessedVariable(
            modeltest1.model.variables["Electrolyte concentration"],
            T1,
            Y1,
            mesh=modeltest1.disc.mesh,
        ).entries
        c2 = pybamm.ProcessedVariable(
            modeltest2.model.variables["Electrolyte concentration"],
            T2,
            Y2,
            mesh=modeltest2.disc.mesh,
        ).entries
        self.assertNotEqual(np.linalg.norm(c1 - c2), 0)
        self.assertNotEqual(np.linalg.norm(Y1 - Y2), 0)


if __name__ == "__main__":
    import sys

    print("Add -v for more debug output")

    if "-v" in sys.argv:
        debug = True
    unittest.main()
