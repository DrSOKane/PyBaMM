#
# Finite Element discretisation class which uses fenics
#
import pybamm

from scipy.sparse import csr_matrix
import autograd.numpy as np

import importlib

dolfin_spec = importlib.util.find_spec("dolfin")
if dolfin_spec is not None:
    dolfin = importlib.util.module_from_spec(dolfin_spec)
    dolfin_spec.loader.exec_module(dolfin)


class FiniteElementFenics(pybamm.SpatialMethod):
    """
    A class which implements the steps specific to the finite element method during
    discretisation. The class uses fenics to discretise the problem to obtain
    the mass and stifnness matrices. At present, this class is only used for
    solving the Poisson problem -grad^2 u = f in the y-z plane (i.e. not the
    through-cell direction).

    For broadcast we follow the default behaviour from SpatialMethod.

    Parameters
    ----------
    mesh : :class:`pybamm.Mesh`
        Contains all the submeshes for discretisation

    **Extends:"": :class:`pybamm.SpatialMethod`
    """

    def __init__(self, mesh):
        if dolfin_spec is None:
            raise ImportError("dolfin is not installed")

        super().__init__(mesh)
        # add npts_for_broadcast to mesh domains for this particular discretisation
        for dom in mesh.keys():
            for i in range(len(mesh[dom])):
                mesh[dom][i].npts_for_broadcast = mesh[dom][i].npts

    def spatial_variable(self, symbol):
        """
        Creates a discretised spatial variable compatible with
        the FiniteVolume method.

        Parameters
        -----------
        symbol : :class:`pybamm.SpatialVariable`
            The spatial variable to be discretised.

        Returns
        -------
        :class:`pybamm.Vector`
            Contains the discretised spatial variable
        """
        # only implemented in y-z plane
        if symbol.name in ["y", "z"]:
            symbol_mesh = self.mesh
            return pybamm.Vector(symbol_mesh[0].npts, domain=symbol.domain)
        else:
            raise NotImplementedError(
                "FiniteElementFenics only implemented in the y-z plane"
            )

    def gradient(self, symbol, discretised_symbol, boundary_conditions):
        """Matrix-vector multiplication to implement the gradient operator.
        See :meth:`pybamm.SpatialMethod.gradient`
        """
        raise NotImplementedError

    def divergence(self, symbol, discretised_symbol, boundary_conditions):
        """Matrix-vector multiplication to implement the divergence operator.
        See :meth:`pybamm.SpatialMethod.divergence`
        """
        raise NotImplementedError

    def laplacian(self, symbol, discretised_symbol, boundary_conditions):
        """Matrix-vector multiplication to implement the laplacian operator.

        Parameters
        ----------
        symbol: :class:`pybamm.Symbol`
            The symbol that we will take the laplacian of.
        discretised_symbol: :class:`pybamm.Symbol`
            The discretised symbol of the correct size
        boundary_conditions : dict
            The boundary conditions of the model
            ({symbol.id: {"left": left bc, "right": right bc}})

        Returns
        -------
        :class: `pybamm.Array`
            Contains the result of acting the discretised gradient on
            the child discretised_symbol
        """
        domain = symbol.domain[0]
        mesh = self.mesh[domain][0]

        stiffness_matrix = self.stiffness_matrix(symbol, boundary_conditions)

        # get boundary conditions and type, here lbc: negative tab, rbc: positive tab
        lbc_value, lbc_type = boundary_conditions[symbol.id]["left"]
        rbc_value, rbc_type = boundary_conditions[symbol.id]["right"]
        boundary_load = pybamm.Vector(np.zeros(mesh.npts))

        if lbc_type == "Neumann":
            # make form for the boundary conditions
            lbc_form = dolfin.Constant(1) * mesh.TestFunction * mesh.ds(1)
            lbc_load = lbc_value * pybamm.Vector(
                dolfin.assemble(lbc_form).get_local()[:]
            )
            boundary_load = boundary_load + lbc_load
        elif lbc_type == "Dirichlet":
            # make unit source which will be adjusted to give the dirichlet value
            # in the correct entries
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(1), mesh.negativetab
            )
            lbc_vec = dolfin.assemble(dolfin.Constant(1) * mesh.TestFunction * mesh.dx)
            bc.apply(lbc_vec)
            # multiply by the lbc value
            lbc_load = lbc_value * pybamm.Vector(lbc_vec.get_local()[:])
            boundary_load = boundary_load + lbc_load
        else:
            raise ValueError(
                "boundary condition must be Dirichlet or Neumann, not '{}'".format(
                    lbc_type
                )
            )

        if rbc_type == "Neumann":
            # make form for the boundary conditions
            rbc_form = dolfin.Constant(1) * mesh.TestFunction * mesh.ds(2)
            rbc_load = rbc_value * pybamm.Vector(
                dolfin.assemble(rbc_form).get_local()[:]
            )
            boundary_load = boundary_load + rbc_load
        elif rbc_type == "Dirichlet":
            # make unit source which will be adjusted to give the dirichlet value
            # in the correct entries
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(1), mesh.positivetab
            )
            rbc_vec = dolfin.assemble(dolfin.Constant(1) * mesh.TestFunction * mesh.dx)
            bc.apply(rbc_vec)
            # multiply by the rbc value
            rbc_load = rbc_value * pybamm.Vector(rbc_vec.get_local()[:])
            boundary_load = boundary_load + rbc_load
        else:
            raise ValueError(
                "boundary condition must be Dirichlet or Neumann, not '{}'".format(
                    rbc_type
                )
            )

        return -stiffness_matrix @ discretised_symbol + boundary_load

    def stiffness_matrix(self, symbol, boundary_conditions):
        """
        Laplacian (stiffness) matrix for finite elements in the appropriate domain.

        Parameters
        ----------
        symbol: :class:`pybamm.Symbol`
            The symbol for which we want to calculate the laplacian matrix
        boundary_conditions : dict
            The boundary conditions of the model
            ({symbol.id: {"left": left bc, "right": right bc}})

        Returns
        -------
        :class:`pybamm.Matrix`
            The (sparse) finite element stiffness matrix for the domain
        """
        domain = symbol.domain[0]
        mesh = self.mesh[domain][0]

        # make form for the stiffness
        stiffness_form = (
            dolfin.inner(
                dolfin.grad(mesh.TrialFunction), dolfin.grad(mesh.TestFunction)
            )
            * mesh.dx
        )

        # assemble the stifnness matrix
        stiffness = dolfin.assemble(stiffness_form)

        # get boundary conditions and type, here lbc: negative tab, rbc: positive tab
        _, lbc_type = boundary_conditions[symbol.id]["left"]
        _, rbc_type = boundary_conditions[symbol.id]["right"]

        if lbc_type == "Dirichlet":
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(0), mesh.negativetab
            )
            bc.apply(stiffness)
        if rbc_type == "Dirichlet":
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(0), mesh.positivetab
            )
            bc.apply(stiffness)

        # get assembled mass matrix entries and convert to csr matrix
        stiffness = csr_matrix(stiffness.array())

        return pybamm.Matrix(stiffness)

    def integral(self, domain, symbol, discretised_symbol):
        """Vector-vector dot product to implement the integral operator.
        See :meth:`pybamm.BaseDiscretisation.integral`
        """

        # Calculate integration vector
        integration_vector = self.definite_integral_vector(domain[0])

        out = integration_vector @ discretised_symbol
        out.domain = []
        return out

    def definite_integral_vector(self, domain):
        """
        Vector for finite-element implementation of the definite integral over
        the entire domain

        .. math::
            I = \\int_{\Omega}\\!f(s)\\,dx

        for where :math:`\Omega` is the domain.

        Parameters
        ----------
        domain : list
            The domain(s) of integration

        Returns
        -------
        :class:`pybamm.Vector`
            The finite volume integral vector for the domain
        """
        # get primary mesh
        mesh = self.mesh[domain][0]
        vector = dolfin.assemble(mesh.TrialFunction * mesh.dx).get_local()[:]
        return pybamm.Matrix(vector[np.newaxis, :])

    def indefinite_integral(self, domain, symbol, discretised_symbol):
        """Implementation of the indefinite integral operator. The
        input discretised symbol must be defined on the internal mesh edges.
        See :meth:`pybamm.BaseDiscretisation.indefinite_integral`
        """
        raise NotImplementedError

    def boundary_value_or_flux(self, symbol, discretised_child):
        """
        Uses linear extrapolation to get the boundary value or flux of a variable in the
        Finite Element Method.

        See :meth:`pybamm.SpatialMethod.boundary_value`
        """
        raise NotImplementedError

    def mass_matrix(self, symbol, boundary_conditions):
        """
        Calculates the mass matrix for the finite element method.

        Parameters
        ----------
        symbol: :class:`pybamm.Variable`
            The variable corresponding to the equation for which we are
            calculating the mass matrix.
        boundary_conditions : dict
            The boundary conditions of the model
            ({symbol.id: {"left": left bc, "right": right bc}})

        Returns
        -------
        :class:`pybamm.Matrix`
            The (sparse) mass matrix for the spatial method.
        """
        # get primary domain mesh
        domain = symbol.domain[0]
        mesh = self.mesh[domain][0]

        # create form for mass
        mass_form = mesh.TrialFunction * mesh.TestFunction * mesh.dx

        # assemble mass matrix
        mass = dolfin.assemble(mass_form)

        # get boundary conditions and type, here lbc: negative tab, rbc: positive tab
        _, lbc_type = boundary_conditions[symbol.id]["left"]
        _, rbc_type = boundary_conditions[symbol.id]["right"]

        if lbc_type == "Dirichlet":
            # set source terms to zero on boundary
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(0), mesh.negativetab
            )
            bc.zero(mass)
        if rbc_type == "Dirichlet":
            # set source terms to zero on boundary
            bc = dolfin.DirichletBC(
                mesh.FunctionSpace, dolfin.Constant(0), mesh.positivetab
            )
            bc.zero(mass)

        # get assembled mass matrix entries and convert to csr matrix
        mass = csr_matrix(mass.array())

        return pybamm.Matrix(mass)
