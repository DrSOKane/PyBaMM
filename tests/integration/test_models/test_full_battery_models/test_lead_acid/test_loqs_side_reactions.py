#
# Tests for the lead-acid LOQS model
#
import pybamm
import tests
import unittest


@unittest.skipIf(pybamm.have_scikits_odes(), "scikits.odes not installed")
class TestLeadAcidLOQSWithSideReactions(unittest.TestCase):
    def test_discharge_differential(self):
        options = {"capacitance": "differential", "side reactions": ["oxygen"]}
        model = pybamm.lead_acid.LOQS(options)
        modeltest = tests.StandardModelTest(model)
        modeltest.test_all()

    def test_discharge_differential_varying_surface_area(self):
        options = {
            "capacitance": "differential",
            "side reactions": ["oxygen"],
            "interfacial surface area": "varying",
        }
        model = pybamm.lead_acid.LOQS(options)
        modeltest = tests.StandardModelTest(model)
        modeltest.test_all()

    @unittest.skipIf(pybamm.have_scikits_odes(), "scikits.odes not installed")
    def test_discharge_algebraic(self):
        options = {"capacitance": "algebraic", "side reactions": ["oxygen"]}
        model = pybamm.lead_acid.LOQS(options)
        modeltest = tests.StandardModelTest(model)
        modeltest.test_all(skip_output_tests=True)

    def test_charge(self):
        options = {"capacitance": "differential", "side reactions": ["oxygen"]}
        model = pybamm.lead_acid.LOQS(options)
        parameter_values = model.default_parameter_values
        parameter_values.update(
            {"Typical current [A]": -1, "Initial State of Charge": 0.5}
        )
        modeltest = tests.StandardModelTest(model, parameter_values=parameter_values)
        modeltest.test_all(skip_output_tests=True)

    def test_zero_current(self):
        options = {"capacitance": "differential", "side reactions": ["oxygen"]}
        model = pybamm.lead_acid.LOQS(options)
        parameter_values = model.default_parameter_values
        parameter_values.update(
            {"Current function": pybamm.GetConstantCurrent(current=0)}
        )
        modeltest = tests.StandardModelTest(model, parameter_values=parameter_values)
        modeltest.test_all(skip_output_tests=True)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
