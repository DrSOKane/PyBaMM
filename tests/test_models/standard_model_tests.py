#
# Standard basic tests for any model
#
import numpy as np


class StandardModelTest(object):
    def __init__(self, model):
        self.model = model
        # Set defaults
        self.param = model.default_parameter_values
        self.geometry = model.default_geometry
        self.disc = model.default_discretisation
        self.solver = model.default_solver

    def test_processing_parameters(self, param=None):
        # Overwrite parameters if given
        if param is not None:
            self.param = param
        self.param.process_model(self.model)
        # Model should still be well-posed after processing
        self.model.check_well_posedness()

    def test_processing_disc(self, disc=None):
        # Overwrite discretisation if given
        if disc is not None:
            self.disc = disc
        self.disc.process_model(self.model)
        # Model should still be well-posed after processing
        self.model.check_well_posedness()

    def test_solving(self, solver=None):
        # Overwrite solver if given
        if solver is not None:
            self.solver = solver
        t_eval = np.linspace(0, 1, 100)
        self.solver.solve(self.model, t_eval)

    def test_all(self, param=None, disc=None, solver=None):
        self.model.check_well_posedness()
        self.test_processing_parameters(param)
        self.test_processing_disc(disc)
        self.test_solving(solver)
