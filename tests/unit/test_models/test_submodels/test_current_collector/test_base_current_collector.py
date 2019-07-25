#
# Test base current collector submodel
#

import pybamm
import tests
import unittest


class TestBaseModel(unittest.TestCase):
    def test_public_functions(self):
        submodel = pybamm.current_collector.BaseModel(None, None)
        std_tests = tests.StandardSubModelTests(submodel)
        std_tests.test_all()


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    pybamm.settings.debug_mode = True
    unittest.main()
