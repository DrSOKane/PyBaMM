#
# Base model class
#
import pybamm

import numbers
import os


class BaseModel(object):
    """Base model class for other models to extend.

    Attributes
    ----------

    rhs: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the rhs
    algebraic: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the algebraic equations. The algebraic expressions are assumed to equate
        to zero. Note that all the variables in the model must exist in the keys of
        `rhs` or `algebraic`.
    initial_conditions: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the initial conditions for the state variables y
    initial_conditions_ydot: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the initial conditions for the time derivative of y
    boundary_conditions: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the boundary conditions
    variables: dict
        A dictionary that maps strings to expressions that represent
        the useful variables

    """

    def __init__(self):
        # Initialise empty model
        self._rhs = {}
        self._algebraic = {}
        self._initial_conditions = {}
        self._initial_conditions_ydot = {}
        self._boundary_conditions = {}
        self._variables = {}
        self._concatenated_rhs = None
        self._concatenated_initial_conditions = None

        # Default parameter values, geometry, submesh, spatial methods and solver
        self.default_parameter_values = pybamm.ParameterValues(
            "input/parameters/lithium-ion/parameters/LCO.csv",
            {
                "I_typ": 1,
                "current function": os.path.join(
                    os.getcwd(),
                    "pybamm",
                    "parameters",
                    "standard_current_functions",
                    "constant_current.py",
                ),
            },
        )
        self.default_geometry = pybamm.Geometry("1D macro", "1D micro")
        self.default_submesh_pts = {
            "negative electrode": {"x": 40},
            "separator": {"x": 25},
            "positive electrode": {"x": 35},
            "negative particle": {"r": 10},
            "positive particle": {"r": 10},
        }
        self.default_submesh_types = {
            "negative electrode": pybamm.Uniform1DSubMesh,
            "separator": pybamm.Uniform1DSubMesh,
            "positive electrode": pybamm.Uniform1DSubMesh,
            "negative particle": pybamm.Uniform1DSubMesh,
            "positive particle": pybamm.Uniform1DSubMesh,
        }
        self.default_spatial_methods = {
            "macroscale": pybamm.FiniteVolume,
            "negative particle": pybamm.FiniteVolume,
            "positive particle": pybamm.FiniteVolume,
        }
        self.default_solver = pybamm.ScipySolver(method="RK45")

    def _set_dict(self, dict, name):
        """
        Convert any scalar equations in dict to 'pybamm.Scalar'
        and check that domains are consistent
        """
        # Convert any numbers to a pybamm.Scalar
        for var, eqn in dict.items():
            if isinstance(eqn, numbers.Number):
                dict[var] = pybamm.Scalar(eqn)

        if not all(
            [
                variable.domain == equation.domain or equation.domain == []
                for variable, equation in dict.items()
            ]
        ):
            raise pybamm.DomainError(
                "variable and equation in '{}' must have the same domain".format(name)
            )

        return dict

    @property
    def rhs(self):
        return self._rhs

    @rhs.setter
    def rhs(self, rhs):
        self._rhs = self._set_dict(rhs, "rhs")

    @property
    def algebraic(self):
        return self._algebraic

    @algebraic.setter
    def algebraic(self, algebraic):
        self._algebraic = self._set_dict(algebraic, "algebraic")

    @property
    def initial_conditions(self):
        return self._initial_conditions

    @initial_conditions.setter
    def initial_conditions(self, initial_conditions):
        self._initial_conditions = self._set_dict(
            initial_conditions, "initial_conditions"
        )

    @property
    def initial_conditions_ydot(self):
        return self._initial_conditions_ydot

    @initial_conditions_ydot.setter
    def initial_conditions_ydot(self, initial_conditions):
        self._initial_conditions_ydot = self._set_dict(
            initial_conditions, "initial_conditions_ydot"
        )

    @property
    def boundary_conditions(self):
        return self._boundary_conditions

    @boundary_conditions.setter
    def boundary_conditions(self, boundary_conditions):
        # Convert any numbers to a pybamm.Scalar
        for var, bcs in boundary_conditions.items():
            for side, eqn in bcs.items():
                if isinstance(eqn, numbers.Number):
                    boundary_conditions[var][side] = pybamm.Scalar(eqn)

        self._boundary_conditions = boundary_conditions

    @property
    def variables(self):
        return self._variables

    @variables.setter
    def variables(self, variables):
        self._variables = variables

    @property
    def concatenated_rhs(self):
        return self._concatenated_rhs

    @concatenated_rhs.setter
    def concatenated_rhs(self, concatenated_rhs):
        self._concatenated_rhs = concatenated_rhs

    @property
    def concatenated_initial_conditions(self):
        return self._concatenated_initial_conditions

    @concatenated_initial_conditions.setter
    def concatenated_initial_conditions(self, concatenated_initial_conditions):
        self._concatenated_initial_conditions = concatenated_initial_conditions

    def __getitem__(self, key):
        return self.rhs[key]

    def update(self, *submodels):
        """
        Update model to add new physics from submodels

        Parameters
        ----------
        submodel : iterable of submodels (subclasses of :class:`pybamm.BaseModel`)
            The submodels from which to create new model
        """
        for submodel in submodels:

            # check and then update dicts
            self.check_and_combine_dict(self._rhs, submodel.rhs)
            self.check_and_combine_dict(self._algebraic, submodel.algebraic)
            self.check_and_combine_dict(
                self._initial_conditions, submodel.initial_conditions
            )
            self.check_and_combine_dict(
                self._boundary_conditions, submodel.boundary_conditions
            )
            self._variables.update(submodel.variables)  # keys are strings so no check

    def check_and_combine_dict(self, dict1, dict2):
        # check that the key ids are distinct
        ids1 = set(x.id for x in dict1.keys())
        ids2 = set(x.id for x in dict2.keys())
        assert len(ids1.intersection(ids2)) == 0, pybamm.ModelError(
            "Submodel incompatible: duplicate variables"
        )
        dict1.update(dict2)

    def check_well_posedness(self):
        """
        Check that the model is well-posed by executing the following tests:
        - Model is not over- or underdetermined, by comparing keys and equations in rhs
        and algebraic. Overdetermined if more equations than variables, underdetermined
        if more variables than equations.
        - There is an initial condition in self.initial_conditions for each
        variable/equation pair in self.rhs
        - There are appropriate boundary conditions in self.boundary_conditions for each
        variable/equation pair in self.rhs and self.algebraic
        """
        # Equations (differential and algebraic)
        # Get all the variables from differential and algebraic equations
        vars_in_rhs_keys = set()
        vars_in_algebraic_keys = set()
        vars_in_eqns = set()
        # Get all variables ids from rhs and algebraic keys and equations
        # For equations we look through the whole expression tree.
        # "Variables" can be Concatenations so we also have to look in the whole
        # expression tree
        for var, eqn in self.rhs.items():
            vars_in_rhs_keys.update(
                [x.id for x in var.pre_order() if isinstance(x, pybamm.Variable)]
            )
            vars_in_eqns.update(
                [x.id for x in eqn.pre_order() if isinstance(x, pybamm.Variable)]
            )
        for var, eqn in self.algebraic.items():
            vars_in_algebraic_keys.update(
                [x.id for x in var.pre_order() if isinstance(x, pybamm.Variable)]
            )
            vars_in_eqns.update(
                [x.id for x in eqn.pre_order() if isinstance(x, pybamm.Variable)]
            )
        # If any keys are repeated between rhs and algebraic then the model is
        # overdetermined
        if not set(vars_in_rhs_keys).isdisjoint(vars_in_algebraic_keys):
            raise pybamm.ModelError("model is overdetermined (repeated keys)")
        # If any algebraic keys don't appear in the eqns then the model is
        # overdetermined (but rhs keys can be absent from the eqns, e.g. dcdt = -1 is
        # fine)
        extra_algebraic_keys = vars_in_algebraic_keys.difference(vars_in_eqns)
        if extra_algebraic_keys:
            raise pybamm.ModelError("model is overdetermined (extra algebraic keys)")
        # If any variables in the equations don't appear in the keys then the model is
        # underdetermined
        vars_in_keys = vars_in_rhs_keys.union(vars_in_algebraic_keys)
        extra_variables = vars_in_eqns.difference(vars_in_keys)
        if extra_variables:
            raise pybamm.ModelError("model is underdetermined (too many variables)")

        # Initial conditions
        for var in self.rhs.keys():
            if var not in self.initial_conditions.keys():
                raise pybamm.ModelError(
                    """no initial condition given for variable '{}'""".format(var)
                )

        # Boundary conditions
        for var, eqn in {**self.rhs, **self.algebraic}.items():
            if eqn.has_spatial_derivatives():
                # Variable must be in at least one expression in the boundary condition
                # keys (to account for both Dirichlet and Neumann boundary conditions)
                if not any(
                    [
                        any([var.id == symbol.id for symbol in key.pre_order()])
                        for key in self.boundary_conditions.keys()
                    ]
                ):
                    raise pybamm.ModelError(
                        """
                        no boundary condition given for variable '{}'
                        with equation '{}'
                        """.format(
                            var, eqn
                        )
                    )
