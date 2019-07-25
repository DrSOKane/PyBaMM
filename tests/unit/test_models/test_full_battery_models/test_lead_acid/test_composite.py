#
# Tests for the lead-acid composite model
#
import pybamm
import unittest


class TestLeadAcidComposite(unittest.TestCase):
    def test_well_posed(self):
        # debug mode slows down the composite model a fair bit, so turn off
        pybamm.settings.debug_mode = False
        model = pybamm.lead_acid.Composite()
        pybamm.settings.debug_mode = True
        model.check_well_posedness()

    def test_well_posed_with_convection(self):
        options = {"convection": True}
        # debug mode slows down the composite model a fair bit, so turn off
        pybamm.settings.debug_mode = False
        model = pybamm.lead_acid.Composite(options)
        pybamm.settings.debug_mode = True
        model.check_well_posedness()

    def test_well_posed_differential(self):
        options = {"surface form": "differential"}
        # debug mode slows down the composite model a fair bit, so turn off
        pybamm.settings.debug_mode = False
        model = pybamm.lead_acid.Composite(options)
        pybamm.settings.debug_mode = True
        model.check_well_posedness()

    @unittest.skipIf(pybamm.have_scikits_odes(), "scikits.odes not installed")
    def test_default_solver(self):
        options = {"surface form": "differential"}
        model = pybamm.lead_acid.Composite(options)
        self.assertIsInstance(model.default_solver, pybamm.ScipySolver)
        options = {"surface form": "differential", "bc_options": {"dimensionality": 1}}
        model = pybamm.lead_acid.Composite(options)
        self.assertIsInstance(model.default_solver, pybamm.ScipySolver)
        options = {"surface form": "algebraic"}
        model = pybamm.lead_acid.Composite(options)
        self.assertIsInstance(model.default_solver, pybamm.ScikitsDaeSolver)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    pybamm.settings.debug_mode = True
    unittest.main()
