#
# Finite Volume discretisation class
#
import pybamm

import numpy as np
from scipy.sparse import spdiags


class FiniteVolumeDiscretisation(pybamm.BaseDiscretisation):
    """Discretisation using Finite Volumes.

    Parameters
    ----------
    mesh : :class:`pybamm.BaseMesh` (or subclass)
        The underlying mesh for discretisation

    **Extends:** :class:`pybamm.BaseDiscretisation`
    """

    def __init__(self, mesh):
        super().__init__(mesh)

    def compute_diffusivity(self, symbol):
        """
        Compute the diffusivity at cell edges, based on the diffusivity at cell nodes.
        For now we just take the arithemtic mean, though it may be better to take the
        harmonic mean based on [1].

        [1] Recktenwald, Gerald. "The control-volume finite-difference approximation to
        the diffusion equation." (2012).

        Parameters
        ----------
        symbol : :class:`pybamm.Symbol`
            Symbol to be averaged. When evaluated, this symbol returns either a scalar
            or an array of shape (n,), where n is the number of points in the mesh for
            the symbol's domain (n = self.mesh[symbol.domain].npts)

        Returns
        -------
        :class:`pybamm.NodeToEdge`
            Averaged symbol. When evaluated, this returns either a scalar or an array of
            shape (n-1,) as appropriate.
        """

        def arithmetic_mean(array):
            """Calculate the arithemetic mean of an array"""
            return (array[1:] + array[:-1]) / 2

        return pybamm.NodeToEdge(symbol, arithmetic_mean)

    def gradient(self, symbol, y_slices, boundary_conditions):
        """Matrix-vector multiplication to implement the gradient operator.
        See :meth:`pybamm.BaseDiscretisation.gradient`
        """
        # Check that boundary condition keys are hashes (ids)
        for key in boundary_conditions.keys():
            assert isinstance(key, int), TypeError(
                "boundary condition keys should be hashes, not {}".format(type(key))
            )
        # Discretise symbol
        discretised_symbol = self.process_symbol(symbol, y_slices, boundary_conditions)
        domain = symbol.domain
        # Add Dirichlet boundary conditions, if defined
        if symbol.id in boundary_conditions:
            lbc = boundary_conditions[symbol.id]["left"]
            rbc = boundary_conditions[symbol.id]["right"]
            discretised_symbol = self.add_ghost_nodes(discretised_symbol, lbc, rbc)
            domain = (
                [domain[0] + "_left ghost cell"]
                + domain
                + [domain[-1] + "_right ghost cell"]
            )

        # note in 1D spherical grad and normal grad are the same
        gradient_matrix = self.gradient_matrix(domain)
        return gradient_matrix * discretised_symbol

    def add_ghost_nodes(self, discretised_symbol, lbc, rbc):
        """
        Add Dirichlet boundary conditions via ghost nodes.

        For a boundary condition "y = a at the left-hand boundary",
        we concatenate a ghost node to the start of the vector y with value "2*a - y1"
        where y1 is the value of the first node.
        Similarly for the right-hand boundary condition.

        Currently, Dirichlet boundary conditions can only be applied on state
        variables (e.g. concentration, temperature), and not on expressions.
        To access the value of the first node (y1), we create a "first_node" object
        which is a StateVector whose y_slice is the start of the y_slice of
        discretised_symbol.
        Similarly, the last node is a StateVector whose y_slice is the end of the
        y_slice of discretised_symbol

        Parameters
        ----------
        discretised_symbol : :class:`pybamm.StateVector` (size n)
            The discretised variable (a state vector) to which to add ghost nodes
        lbc : :class:`pybamm.Scalar`
            Dirichlet bouncary condition on the left-hand side
        rbc : :class:`pybamm.Scalar`
            Dirichlet bouncary condition on the right-hand side

        Returns
        -------
        :class:`pybamm.Concatenation` (size n+2)
            Concatenation of the variable (a state vector) and ghost nodes

        """
        assert isinstance(discretised_symbol, pybamm.StateVector), NotImplementedError(
            """discretised_symbol must be a StateVector, not {}""".format(
                type(discretised_symbol)
            )
        )
        # left ghost cell
        y_slice_start = discretised_symbol.y_slice.start
        first_node = pybamm.StateVector(slice(y_slice_start, y_slice_start + 1))
        left_ghost_cell = 2 * lbc - first_node
        # right ghost cell
        y_slice_stop = discretised_symbol.y_slice.stop
        last_node = pybamm.StateVector(slice(y_slice_stop - 1, y_slice_stop))
        right_ghost_cell = 2 * rbc - last_node
        # concatenate
        return self.concatenate(left_ghost_cell, discretised_symbol, right_ghost_cell)

    def gradient_matrix(self, domain):
        """
        Gradient matrix for finite volumes in the appropriate domain.
        Equivalent to grad(y) = (y[1:] - y[:-1])/dx

        Parameters
        ----------
        domain : list
            The domain(s) in which to compute the gradient matrix

        Returns
        -------
        :class:`pybamm.Matrix`
            The (sparse) finite volume gradient matrix for the domain
        """
        # Create appropriate submesh by combining submeshes in domain
        submesh = self.mesh.combine_submeshes(*domain)

        # Create matrix using submesh
        n = submesh.npts
        e = 1 / submesh.d_nodes
        data = np.vstack(
            [np.concatenate([-e, np.array([0])]), np.concatenate([np.array([0]), e])]
        )
        diags = np.array([0, 1])
        matrix = spdiags(data, diags, n - 1, n)
        return pybamm.Matrix(matrix)

    def divergence(self, symbol, y_slices, boundary_conditions):
        """Matrix-vector multiplication to implement the divergence operator.
        See :meth:`pybamm.BaseDiscretisation.gradient`
        """
        # Check that boundary condition keys are hashes (ids)
        for key in boundary_conditions.keys():
            assert isinstance(key, int), TypeError(
                "boundary condition keys should be hashes, not {}".format(type(key))
            )
        # Discretise symbol
        discretised_symbol = self.process_symbol(symbol, y_slices, boundary_conditions)
        # Add Neumann boundary conditions if defined
        if symbol.id in boundary_conditions:
            # for the particles there will be a "negative particle" "left" and "right"
            # and also a "positive particle" left and right.
            lbc = boundary_conditions[symbol.id]["left"]
            rbc = boundary_conditions[symbol.id]["right"]
            discretised_symbol = self.concatenate(lbc, discretised_symbol, rbc)

        domain = symbol.domain
        # check for
        if ("negative particle" or "positive particle") in domain:

            # implement spherical operator
            divergence_matrix = self.divergence_matrix(domain)

            submesh = self.mesh.combine_submeshes(*domain)
            r = pybamm.Vector(submesh.nodes)
            r_edges = pybamm.Vector(submesh.edges)

            out = (1 / (r ** 2)) * (
                divergence_matrix * ((r_edges ** 2) * discretised_symbol)
            )

        else:
            divergence_matrix = self.divergence_matrix(domain)
            out = divergence_matrix * discretised_symbol
        return out

    def divergence_matrix(self, domain):
        """
        Divergence matrix for finite volumes in the appropriate domain.
        Equivalent to div(N) = (N[1:] - N[:-1])/dx

        Parameters
        ----------
        domain : list
            The domain(s) in which to compute the divergence matrix

        Returns
        -------
        :class:`pybamm.Matrix`
            The (sparse) finite volume divergence matrix for the domain
        """
        # Create appropriate submesh by combining submeshes in domain
        submesh = self.mesh.combine_submeshes(*domain)

        # Create matrix using submesh
        n = submesh.npts + 1
        e = 1 / submesh.d_edges
        data = np.vstack(
            [np.concatenate([-e, np.array([0])]), np.concatenate([np.array([0]), e])]
        )
        diags = np.array([0, 1])
        matrix = spdiags(data, diags, n - 1, n)
        return pybamm.Matrix(matrix)


class NodeToEdge(pybamm.SpatialOperator):
    """A node in the expression tree representing a unary operator that evaluates the
    value of its child at cell edges by averaging the value at cell nodes.

    Parameters
    ----------

    name : str
        name of the node
    child : :class:`Symbol`
        child node
    node_to_edge_function : method
        the function used to average; only acts if the child evaluates to a
        one-dimensional numpy array

    **Extends:** :class:`pybamm.SpatialOperator`
    """

    def __init__(self, child, node_to_edge_function):
        """ See :meth:`pybamm.UnaryOperator.__init__()`. """
        super().__init__(
            "node to edge ({})".format(node_to_edge_function.__name__), child
        )
        self._node_to_edge_function = node_to_edge_function

    def evaluate(self, t=None, y=None):
        """ See :meth:`pybamm.Symbol.evaluate()`. """
        evaluated_child = self.children[0].evaluate(t, y)
        # If the evaluated child is a numpy array of shape (n,), do the averaging
        # NOTE: Doing this check every time might be slow?
        # NOTE: Will need to deal with 2D arrays at some point
        if isinstance(evaluated_child, np.ndarray) and len(evaluated_child.shape) == 1:
            return self._node_to_edge_function(evaluated_child)
        # If not, no need to average
        else:
            return evaluated_child
