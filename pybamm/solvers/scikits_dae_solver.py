#
# Solver class using Scipy's adaptive time stepper
#
import pybamm

import numpy as np
import importlib
import scipy.sparse as sparse

scikits_odes_spec = importlib.util.find_spec("scikits")
if scikits_odes_spec is not None:
    scikits_odes_spec = importlib.util.find_spec("scikits.odes")
    if scikits_odes_spec is not None:
        scikits_odes = importlib.util.module_from_spec(scikits_odes_spec)
        scikits_odes_spec.loader.exec_module(scikits_odes)


class ScikitsDaeSolver(pybamm.DaeSolver):
    """Solve a discretised model, using scikits.odes.

    Parameters
    ----------
    method : str, optional
        The method to use in solve_ivp (default is "BDF")
    tolerance : float, optional
        The tolerance for the solver (default is 1e-8). Set as the both reltol and
        abstol in solve_ivp.
    root_method : str, optional
        The method to use to find initial conditions (default is "lm")
    tolerance : float, optional
        The tolerance for the initial-condition solver (default is 1e-8).
    """

    def __init__(self, method="ida", tol=1e-8, root_method="lm", root_tol=1e-6):
        if scikits_odes_spec is None:
            raise ImportError("scikits.odes is not installed")

        super().__init__(method, tol, root_method, root_tol)

    def integrate(
        self, residuals, y0, t_eval, events=None, mass_matrix=None, jacobian=None
    ):
        """
        Solve a DAE model defined by residuals with initial conditions y0.

        Parameters
        ----------
        residuals : method
            A function that takes in t, y and ydot and returns the residuals of the
            equations
        y0 : numeric type
            The initial conditions
        t_eval : numeric type
            The times at which to compute the solution
        events : method, optional
            A function that takes in t and y and returns conditions for the solver to
            stop
        mass_matrix : array_like, optional
            The (sparse) mass matrix for the chosen spatial method.
        jacobian : method, optional
            A function that takes in t and y and returns the Jacobian. If
            None, the solver will approximate the Jacobian.
            (see `SUNDIALS docs. <https://computation.llnl.gov/projects/sundials>`).
        """

        def eqsres(t, y, ydot, return_residuals):
            return_residuals[:] = residuals(t, y, ydot)

        def rootfn(t, y, ydot, return_root):
            return_root[:] = [event(t, y) for event in events]

        extra_options = {"old_api": False, "rtol": self.tol, "atol": self.tol}

        if jacobian:
            jac_y0_t0 = jacobian(t_eval[0], y0)
            if sparse.issparse(jac_y0_t0):

                def jacfn(t, y, ydot, residuals, cj, J):
                    jac_eval = jacobian(t, y) - cj * mass_matrix
                    J[:][:] = jac_eval.toarray()

            else:

                def jacfn(t, y, ydot, residuals, cj, J):
                    jac_eval = jacobian(t, y) - cj * mass_matrix
                    J[:][:] = jac_eval

            extra_options.update({"jacfn": jacfn})

        if events:
            extra_options.update({"rootfn": rootfn, "nr_rootfns": len(events)})

        # solver works with ydot0 set to zero
        ydot0 = np.zeros_like(y0)

        # set up and solve
        dae_solver = scikits_odes.dae(self.method, eqsres, **extra_options)
        sol = dae_solver.solve(t_eval, y0, ydot0)

        # return solution, we need to tranpose y to match scipy's interface
        if sol.flag in [0, 2]:
            # 0 = solved for all t_eval
            # 2 = found root(s)
            return pybamm.Solution(sol.values.t, np.transpose(sol.values.y))
        else:
            raise pybamm.SolverError(sol.message)
