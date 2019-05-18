#
# Interface for discretisation
#
import pybamm

import numpy as np
from scipy.sparse import block_diag, csr_matrix


class Discretisation(object):
    """The discretisation class, with methods to process a model and replace
    Spatial Operators with Matrices and Variables with StateVectors

    Parameters
    ----------
    mesh : pybamm.Mesh
            contains all submeshes to be used on each domain
    spatial_methods : dict
            a dictionary of the spatial method to be used on each
            domain. The keys correspond to the keys in a pybamm.Model
    """

    def __init__(self, mesh=None, spatial_methods=None):
        self._mesh = mesh
        if mesh is None:
            self._spatial_methods = {}
        else:
            # Unpack macroscale to the constituent subdomains
            if "macroscale" in spatial_methods.keys():
                method = spatial_methods["macroscale"]
                spatial_methods["negative electrode"] = method
                spatial_methods["separator"] = method
                spatial_methods["positive electrode"] = method
            self._spatial_methods = {
                dom: method(mesh) for dom, method in spatial_methods.items()
            }
        self._bcs = {}
        self._y_slices = {}

    @property
    def mesh(self):
        return self._mesh

    def process_model(self, model, inplace=True):
        """Discretise a model.
        Currently inplace, could be changed to return a new model.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            Model to dicretise. Must have attributes rhs, initial_conditions and
            boundary_conditions (all dicts of {variable: equation})
        inplace: bool, optional
            If True, discretise the model in place. Otherwise, return a new
            discretised model. Default is True.

        Returns
        -------
        model_disc : :class:`pybamm.BaseModel`
            The discretised model. Note that if ``inplace`` is True, model will
            have also been discretised in place so model == model_disc. If
            ``inplace`` is False, model != model_disc

        """
        pybamm.logger.info("Start discretising {}".format(model.name))

        # Prepare discretisation
        # set variables (we require the full variable not just id)
        variables = list(model.rhs.keys()) + list(model.algebraic.keys())

        # Set the y split for variables
        self.set_variable_slices(variables)

        # set boundary conditions (only need key ids for boundary_conditions)
        self._bcs = self.process_boundary_conditions(model)

        # set up inplace vs not inplace
        if inplace:
            # any changes to model_disc attributes will change model attributes
            # since they point to the same object
            model_disc = model
        else:
            # create a blank model so that original model is unchanged
            model_disc = pybamm.BaseModel()

        # Process initial condtions
        ics, concat_ics = self.process_initial_conditions(model)
        model_disc.initial_conditions = ics
        model_disc.concatenated_initial_conditions = concat_ics

        # Process parabolic and elliptic equations
        rhs, concat_rhs, alg, concat_alg = self.process_rhs_and_algebraic(model)
        model_disc.rhs, model_disc.concatenated_rhs = rhs, concat_rhs
        model_disc.algebraic, model_disc.concatenated_algebraic = alg, concat_alg

        # Discretise variables (applying boundary conditions)
        # Note that we **do not** discretise the keys of model.rhs,
        # model.initial_conditions and model.boundary_conditions
        model_disc.variables = self.process_dict(model.variables)

        # Process events
        processed_events = [None] * len(model.events)
        for idx, event in enumerate(model.events):
            processed_events[idx] = self.process_symbol(event)
        model_disc.events = processed_events

        # Create mass matrix
        model_disc.mass_matrix = self.create_mass_matrix(model)

        # Check that resulting model makes sense
        self.check_model(model_disc)

        pybamm.logger.info("Finish discretising {}".format(model.name))

        return model_disc

    def set_variable_slices(self, variables):
        """Sets the slicing for variables.

        variables : iterable of :class:`pybamm.Variables`
            The variables for which to set slices
        """
        # Unpack symbols in variables that are concatenations of variables
        unpacked_variables = []
        for symbol in variables:
            if isinstance(symbol, pybamm.Concatenation):
                unpacked_variables.extend([var for var in symbol.children])
            else:
                unpacked_variables.append(symbol)
        # Set up y_slices
        y_slices = {variable.id: None for variable in unpacked_variables}
        start = 0
        end = 0
        # Iterate through unpacked variables, adding appropriate slices to y_slices
        for variable in unpacked_variables:
            # If domain is empty then variable has size 1
            if variable.domain == []:
                end += 1
            # Otherwise, add up the size of all the domains in variable.domain
            else:
                for dom in variable.domain:
                    for submesh in self._spatial_methods[dom].mesh[dom]:
                        end += submesh.npts_for_broadcast
            y_slices[variable.id] = slice(start, end)
            start = end
        self._y_slices = y_slices

        assert isinstance(self._y_slices, dict), ValueError(
            """y_slices should be dict, not {}""".format(type(self._y_slices))
        )

    def process_initial_conditions(self, model):
        """Discretise model initial_conditions.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            Model to dicretise. Must have attributes rhs, initial_conditions and
            boundary_conditions (all dicts of {variable: equation})

        Returns
        -------
        tuple
            Tuple of processed_initial_conditions (dict of initial conditions) and
            concatenated_initial_conditions (numpy array of concatenated initial
            conditions)

        """
        # Discretise initial conditions
        processed_initial_conditions = self.process_dict(model.initial_conditions)

        # Concatenate initial conditions into a single vector
        # check that all initial conditions are set
        processed_concatenated_initial_conditions = self._concatenate_in_order(
            processed_initial_conditions, check_complete=True
        ).evaluate(0, None)

        return processed_initial_conditions, processed_concatenated_initial_conditions

    def process_boundary_conditions(self, model):
        """Discretise model boundary_conditions, also converting keys to ids

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            Model to dicretise. Must have attributes rhs, initial_conditions and
            boundary_conditions (all dicts of {variable: equation})

        Returns
        -------
        dict
            Dictionary of processed boundary conditions

        """
        processed_bcs = {}
        for key, bcs in model.boundary_conditions.items():
            processed_bcs[key.id] = {}
            for side, bc in bcs.items():
                eqn, typ = bc
                processed_eqn = self.process_symbol(eqn)
                processed_bcs[key.id][side] = (processed_eqn, typ)

        return processed_bcs

    def process_rhs_and_algebraic(self, model):
        """Discretise model equations - differential ('rhs') and algebraic.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            Model to dicretise. Must have attributes rhs, initial_conditions and
            boundary_conditions (all dicts of {variable: equation})

        Returns
        -------
        tuple
            Tuple of processed_rhs (dict of processed differential equations),
            processed_concatenated_rhs, processed_algebraic (dict of processed algebraic
            equations) and processed_concatenated_algebraic

        """
        # Discretise right-hand sides, passing domain from variable
        processed_rhs = self.process_dict(model.rhs)
        # Concatenate rhs into a single state vector

        # Need to concatenate in order as the ordering of equations could be different
        # in processed_rhs and model.rhs (for Python Version <= 3.5)
        processed_concatenated_rhs = self._concatenate_in_order(processed_rhs)

        # Discretise and concatenate algebraic equations
        processed_algebraic = self.process_dict(model.algebraic)

        processed_concatenated_algebraic = self._concatenate_in_order(
            processed_algebraic
        )

        return (
            processed_rhs,
            processed_concatenated_rhs,
            processed_algebraic,
            processed_concatenated_algebraic,
        )

    def create_mass_matrix(self, model):
        """Creates mass matrix of the discretised model.
        Note that the model is assumed to be of the form M*y_dot = f(t,y), where
        M is the (possibly singular) mass matrix.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            Discretised model. Must have attributes rhs, initial_conditions and
            boundary_conditions (all dicts of {variable: equation})

        Returns
        -------
        :class:`pybamm.Matrix`
            The mass matrix
        """
        # Create list of mass matrices for each equation to be put into block
        # diagonal mass matrix for the model
        mass_list = []

        # get a list of model rhs variables that are sorted according to
        # where they are in the state vector
        model_variables = model.rhs.keys()
        model_slices = []
        for v in model_variables:
            if isinstance(v, pybamm.Concatenation):
                model_slices.append(
                    slice(
                        self._y_slices[v.children[0].id].start,
                        self._y_slices[v.children[-1].id].stop,
                    )
                )
            else:
                model_slices.append(self._y_slices[v.id])
        sorted_model_variables = [
            v for _, v in sorted(zip(model_slices, model_variables))
        ]

        # Process mass matrices for the differential equations
        for var in sorted_model_variables:
            if var.domain == []:
                # If variable domain empty then mass matrix is just 1
                mass_list.append(1.0)
            else:
                mass_list.append(
                    self._spatial_methods[var.domain[0]]
                    .mass_matrix(var, self._bcs)
                    .entries
                )

        # Create lumped mass matrix (of zeros) of the correct shape for the
        # discretised algebraic equations
        if model.algebraic.keys():
            y0 = model.concatenated_initial_conditions
            mass_algebraic_size = model.concatenated_algebraic.evaluate(0, y0).shape[0]
            mass_algebraic = csr_matrix((mass_algebraic_size, mass_algebraic_size))
            mass_list.append(mass_algebraic)

        # Create block diagonal (sparse) mass matrix
        mass_matrix = block_diag(mass_list)

        return pybamm.Matrix(mass_matrix)

    def process_dict(self, var_eqn_dict):
        """Discretise a dictionary of {variable: equation}, broadcasting if necessary
        (can be model.rhs, model.initial_conditions or model.variables).

        Parameters
        ----------
        var_eqn_dict : dict
            Equations ({variable: equation} dict) to dicretise
            (can be model.rhs, model.initial_conditions or model.variables)

        Returns
        -------
        new_var_eqn_dict : dict
            Discretised equations

        """
        new_var_eqn_dict = {}
        for eqn_key, eqn in var_eqn_dict.items():
            # Broadcast if the equation evaluates to a number(e.g. Scalar)

            if eqn.evaluates_to_number():
                if not isinstance(eqn_key, str):
                    if eqn_key.domain == []:
                        eqn = pybamm.Broadcast(eqn, eqn_key.domain)
                    else:
                        eqn = self._spatial_methods[eqn_key.domain[0]].broadcast(
                            eqn, eqn_key.domain
                        )

            new_var_eqn_dict[eqn_key] = self.process_symbol(eqn)

            # note we are sending in the key.id here so we don't have to
            # keep calling .id
        return new_var_eqn_dict

    def process_symbol(self, symbol):
        """Discretise operators in model equations.

        Parameters
        ----------
        symbol : :class:`pybamm.expression_tree.symbol.Symbol`
            Symbol to discretise

        Returns
        -------
        :class:`pybamm.expression_tree.symbol.Symbol`
            Discretised symbol

        """
        pybamm.logger.debug("Discretise {!s}".format(symbol))

        if isinstance(symbol, pybamm.BinaryOperator):
            # Pre-process children
            left, right = symbol.children
            disc_left = self.process_symbol(left)
            disc_right = self.process_symbol(right)
            if symbol.domain == []:
                return symbol.__class__(disc_left, disc_right)
            else:
                return self._spatial_methods[symbol.domain[0]].process_binary_operators(
                    symbol, left, right, disc_left, disc_right
                )

        elif isinstance(symbol, pybamm.Gradient):
            child = symbol.children[0]
            discretised_child = self.process_symbol(child)
            return self._spatial_methods[child.domain[0]].gradient(
                child, discretised_child, self._bcs
            )

        elif isinstance(symbol, pybamm.Divergence):
            child = symbol.children[0]
            discretised_child = self.process_symbol(child)
            return self._spatial_methods[child.domain[0]].divergence(
                child, discretised_child, self._bcs
            )

        elif isinstance(symbol, pybamm.IndefiniteIntegral):
            child = symbol.children[0]
            discretised_child = self.process_symbol(child)
            return self._spatial_methods[child.domain[0]].indefinite_integral(
                child.domain, child, discretised_child
            )

        elif isinstance(symbol, pybamm.Integral):
            child = symbol.children[0]
            discretised_child = self.process_symbol(child)
            return self._spatial_methods[child.domain[0]].integral(
                child.domain, child, discretised_child
            )

        elif isinstance(symbol, pybamm.Broadcast):
            # Process child first
            new_child = self.process_symbol(symbol.children[0])
            # Broadcast new_child to the domain specified by symbol.domain
            # Different discretisations may broadcast differently
            if symbol.domain == []:
                symbol = new_child * pybamm.Vector(np.array([1]))
            else:
                symbol = self._spatial_methods[symbol.domain[0]].broadcast(
                    new_child, symbol.domain
                )
            return symbol

        elif isinstance(symbol, pybamm.BoundaryOperator):
            child = symbol.children[0]
            discretised_child = self.process_symbol(child)
            return self._spatial_methods[child.domain[0]].boundary_value_or_flux(
                symbol, discretised_child
            )

        elif isinstance(symbol, pybamm.Function):
            new_child = self.process_symbol(symbol.children[0])
            return pybamm.Function(symbol.func, new_child)

        elif isinstance(symbol, pybamm.UnaryOperator):
            new_child = self.process_symbol(symbol.children[0])
            return symbol.__class__(new_child)

        elif isinstance(symbol, pybamm.Variable):
            return pybamm.StateVector(self._y_slices[symbol.id], domain=symbol.domain)

        elif isinstance(symbol, pybamm.SpatialVariable):
            return self._spatial_methods[symbol.domain[0]].spatial_variable(symbol)

        elif isinstance(symbol, pybamm.Concatenation):
            new_children = [self.process_symbol(child) for child in symbol.children]
            return self._spatial_methods[symbol.domain[0]].domain_concatenation(
                new_children
            )

        elif isinstance(symbol, pybamm.Scalar):
            return pybamm.Scalar(symbol.value, symbol.name, symbol.domain)

        elif isinstance(symbol, pybamm.Array):
            return symbol.__class__(symbol.entries, symbol.name, symbol.domain)

        elif isinstance(symbol, pybamm.StateVector):
            return symbol.__class__(symbol.y_slice, symbol.name, symbol.domain)

        elif isinstance(symbol, pybamm.Time):
            return pybamm.Time()

        else:
            raise NotImplementedError(
                "Cannot discretise symbol of type '{}'".format(type(symbol))
            )

    def concatenate(self, *symbols):
        return pybamm.NumpyConcatenation(*symbols)

    def _concatenate_in_order(self, var_eqn_dict, check_complete=False):
        """
        Concatenate a dictionary of {variable: equation} using self._y_slices

        The keys/variables in `var_eqn_dict` must be the same as the ids in
        `self._y_slices`.
        The resultant concatenation is ordered according to the ordering of the slice
        values in `self._y_slices`

        Parameters
        ----------
        var_eqn_dict : dict
            Equations ({variable: equation} dict) to dicretise

                Returns
        -------
        var_eqn_dict : dict
            Discretised right-hand side equations

        """
        # Unpack symbols in variables that are concatenations of variables
        unpacked_variables = []
        slices = []
        for symbol in var_eqn_dict.keys():
            if isinstance(symbol, pybamm.Concatenation):
                unpacked_variables.extend([var for var in symbol.children])
                slices.append(
                    slice(
                        self._y_slices[symbol.children[0].id].start,
                        self._y_slices[symbol.children[-1].id].stop,
                    )
                )
            else:
                unpacked_variables.append(symbol)
                slices.append(self._y_slices[symbol.id])

        if check_complete:
            # Check keys from the given var_eqn_dict against self._y_slices
            ids = {v.id for v in unpacked_variables}
            if ids != self._y_slices.keys():
                given_variable_names = [v.name for v in var_eqn_dict.keys()]
                raise pybamm.ModelError(
                    "Initial conditions are insufficient. Only "
                    "provided for {} ".format(given_variable_names)
                )

        equations = list(var_eqn_dict.values())

        # sort equations according to slices
        sorted_equations = [eq for _, eq in sorted(zip(slices, equations))]

        return self.concatenate(*sorted_equations)

    def check_model(self, model):
        """ Perform some basic checks to make sure the discretised model makes sense."""
        # Check initial conditions are a numpy array
        # Individual
        for var, eqn in model.initial_conditions.items():
            assert type(eqn.evaluate(0, None)) is np.ndarray, pybamm.ModelError(
                """
                initial_conditions must be numpy array after discretisation but they are
                {} for variable '{}'.
                """.format(
                    type(eqn.evaluate(0, None)), var
                )
            )
        # Concatenated
        assert (
            type(model.concatenated_initial_conditions) is np.ndarray
        ), pybamm.ModelError(
            """
            Concatenated initial_conditions must be numpy array after discretisation but
            they are {}.
            """.format(
                type(model.concatenated_initial_conditions)
            )
        )

        # Check initial conditions and rhs have the same shape
        y0 = model.concatenated_initial_conditions
        # Individual
        for var in model.rhs.keys():
            assert (
                model.rhs[var].evaluate(0, y0).shape
                == model.initial_conditions[var].evaluate(0, None).shape
            ), pybamm.ModelError(
                """
                rhs and initial_conditions must have the same shape after discretisation
                but rhs.shape = {} and initial_conditions.shape = {} for variable '{}'.
                """.format(
                    model.rhs[var].evaluate(0, y0).shape,
                    model.initial_conditions[var].evaluate(0, None).shape,
                    var,
                )
            )
        # Concatenated
        assert (
            model.concatenated_rhs.evaluate(0, y0).shape[0]
            + model.concatenated_algebraic.evaluate(0, y0).shape[0]
            == y0.shape[0]
        ), pybamm.ModelError(
            """
            Concatenation of (rhs, algebraic) and initial_conditions must have the
            same shape after discretisation but rhs.shape = {}, algebraic.shape = {},
            and initial_conditions.shape = {}.
            """.format(
                model.concatenated_rhs.evaluate(0, y0).shape,
                model.concatenated_algebraic.evaluate(0, y0).shape,
                y0.shape,
            )
        )

        # Check variables in variable list against rhs
        # Be lenient with size check if the variable in model.variables is broadcasted
        # If broadcasted, variable is a multiplication with a vector of ones
        for rhs_var in model.rhs.keys():
            if rhs_var.name in model.variables.keys():
                var = model.variables[rhs_var.name]
                if not (
                    model.rhs[rhs_var].evaluate(0, y0).shape
                    == var.evaluate(0, y0).shape
                    or isinstance(var, pybamm.Concatenation)
                    or (
                        isinstance(var, pybamm.Multiplication)
                        and isinstance(var.right, pybamm.Vector)
                        and np.all(var.right.entries == 1)
                    )
                ):
                    raise pybamm.ModelError(
                        """
                    variable and its eqn must have the same shape after discretisation
                    but variable.shape = {} and rhs.shape = {} for variable '{}'.
                    """.format(
                            var.evaluate(0, y0).shape,
                            model.rhs[rhs_var].evaluate(0, y0).shape,
                            var,
                        )
                    )
