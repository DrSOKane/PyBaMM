#
# Base solver class
#
import pybamm
import numpy as np
from scipy import optimize


class DaeSolver(pybamm.BaseSolver):
    """Solve a discretised model.

    Parameters
    ----------
    tolerance : float, optional
        The tolerance for the solver (default is 1e-8).
    root_method : str, optional
        The method to use to find initial conditions (default is "lm")
    tolerance : float, optional
        The tolerance for the initial-condition solver (default is 1e-8).
    max_steps: int, optional
        The maximum number of steps the solver will take before terminating
        (defualt is 1000).
    """

    def __init__(
        self, method=None, tol=1e-8, root_method="lm", root_tol=1e-6, max_steps=1000
    ):
        super().__init__(method, tol)
        self.root_method = root_method
        self.root_tol = root_tol
        self.max_steps = max_steps

    @property
    def root_method(self):
        return self._root_method

    @root_method.setter
    def root_method(self, method):
        self._root_method = method

    @property
    def root_tol(self):
        return self._root_tol

    @root_tol.setter
    def root_tol(self, tol):
        self._root_tol = tol

    @property
    def max_steps(self):
        return self._max_steps

    @max_steps.setter
    def max_steps(self, max_steps):
        self._max_steps = max_steps

    def solve(self, model, t_eval):
        """Calculate the solution of the model at specified times.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            The model whose solution to calculate. Must have attributes rhs and
            initial_conditions
        t_eval : numeric type
            The times at which to compute the solution

        """
        pybamm.logger.info("Start solving {}".format(model.name))

        # Set up
        timer = pybamm.Timer()
        start_time = timer.time()
        concatenated_rhs, concatenated_algebraic, y0, model_events, jac = self.set_up(
            model
        )
        set_up_time = timer.time() - start_time

        # get mass matrix entries
        mass_matrix = model.mass_matrix.entries

        def residuals(t, y, ydot):
            pybamm.logger.debug(
                "Evaluating residuals for {} at t={}".format(model.name, t)
            )
            y = y[:, np.newaxis]
            rhs_eval, known_evals = concatenated_rhs.evaluate(t, y, known_evals={})
            # reuse known_evals
            alg_eval = concatenated_algebraic.evaluate(t, y, known_evals=known_evals)[0]
            # turn into 1D arrays
            rhs_eval = rhs_eval[:, 0]
            alg_eval = alg_eval[:, 0]
            return np.concatenate((rhs_eval, alg_eval)) - mass_matrix @ ydot

        # Create event-dependent function to evaluate events
        def event_fun(event):
            def eval_event(t, y):
                return event.evaluate(t, y)

            return eval_event

        events = [event_fun(event) for event in model_events.values()]

        # Create function to evaluate jacobian
        if jac is not None:

            def jacobian(t, y):
                return jac.evaluate(t, y, known_evals={})[0]

        else:
            jacobian = None

        # Solve
        solve_start_time = timer.time()
        pybamm.logger.info("Calling DAE solver")
        solution = self.integrate(
            residuals,
            y0,
            t_eval,
            events=events,
            mass_matrix=mass_matrix,
            jacobian=jacobian,
        )
        # Assign times
        solution.solve_time = timer.time() - solve_start_time
        solution.total_time = timer.time() - start_time
        solution.set_up_time = set_up_time

        # Identify the event that caused termination
        termination = self.get_termination_reason(solution, model_events)

        pybamm.logger.info("Finish solving {} ({})".format(model.name, termination))
        pybamm.logger.info(
            "Set-up time: {}, Solve time: {}, Total time: {}".format(
                timer.format(solution.set_up_time),
                timer.format(solution.solve_time),
                timer.format(solution.total_time),
            )
        )
        return solution

    def set_up(self, model):
        """Unpack model, perform checks, simplify and calculate jacobian.

        Parameters
        ----------
        model : :class:`pybamm.BaseModel`
            The model whose solution to calculate. Must have attributes rhs and
            initial_conditions

        Returns
        -------
        concatenated_rhs : :class:`pybamm.Concatenation`
            Right-hand side of differential equations
        concatenated_algebraic : :class:`pybamm.Concatenation`
            Algebraic equations, which should evaluate to zero
        y0 : :class:`numpy.array`
            Vector of initial conditions
        events : dict
            Dicitonary of events at which the model should terminate
        jac : :class:`pybamm.SparseStack`
            Jacobian matrix for the differential and algebraic equations

        Raises
        ------
        :class:`pybamm.SolverError`
            If the model contains any algebraic equations (in which case a DAE solver
            should be used instead)
        """
        # create simplified rhs algebraic and event expressions
        concatenated_rhs = model.concatenated_rhs
        concatenated_algebraic = model.concatenated_algebraic
        events = model.events

        if model.use_simplify:
            # set up simplification object, for re-use of dict
            simp = pybamm.Simplification()
            pybamm.logger.info("Simplifying RHS")
            concatenated_rhs = simp.simplify(concatenated_rhs)
            pybamm.logger.info("Simplifying algebraic")
            concatenated_algebraic = simp.simplify(concatenated_algebraic)
            pybamm.logger.info("Simplifying events")
            events = {name: simp.simplify(event) for name, event in events.items()}

        if model.use_jacobian:
            # Create Jacobian from simplified rhs
            y = pybamm.StateVector(
                slice(0, np.size(model.concatenated_initial_conditions))
            )
            pybamm.logger.info("Calculating jacobian")
            jac_rhs = concatenated_rhs.jac(y)
            jac_algebraic = concatenated_algebraic.jac(y)
            jac = pybamm.SparseStack(jac_rhs, jac_algebraic)

            if model.use_simplify:
                pybamm.logger.info("Simplifying jacobian")
                jac = jac.simplify()

            if model.use_to_python:
                pybamm.logger.info("Converting jacobian to python")
                jac = pybamm.EvaluatorPython(jac)

        else:
            jac = None

        if model.use_to_python:
            pybamm.logger.info("Converting RHS to python")
            concatenated_rhs = pybamm.EvaluatorPython(concatenated_rhs)
            pybamm.logger.info("Converting algebraic to python")
            concatenated_algebraic = pybamm.EvaluatorPython(concatenated_algebraic)
            pybamm.logger.info("Converting events to python")
            events = {
                name: pybamm.EvaluatorPython(event) for name, event in events.items()
            }

        # Calculate consistent initial conditions for the algebraic equations
        def rhs(t, y):
            return concatenated_rhs.evaluate(t, y, known_evals={})[0][:, 0]

        def algebraic(t, y):
            return concatenated_algebraic.evaluate(t, y, known_evals={})[0][:, 0]

        if len(model.algebraic) > 0:
            y0 = self.calculate_consistent_initial_conditions(
                rhs, algebraic, model.concatenated_initial_conditions[:, 0]
            )
        else:
            # can use DAE solver to solve ODE model
            y0 = model.concatenated_initial_conditions[:, 0]

        return concatenated_rhs, concatenated_algebraic, y0, events, jac

    def calculate_consistent_initial_conditions(self, rhs, algebraic, y0_guess):
        """
        Calculate consistent initial conditions for the algebraic equations through
        root-finding

        Parameters
        ----------
        rhs : method
            Function that takes in t and y and returns the value of the differential
            equations
        algebraic : method
            Function that takes in t and y and returns the value of the algebraic
            equations
        y0_guess : array-like
            Array of the user's guess for the initial conditions, used to initialise
            the root finding algorithm

        Returns
        -------
        y0_consistent : array-like, same shape as y0_guess
            Initial conditions that are consistent with the algebraic equations (roots
            of the algebraic equations)
        """
        pybamm.logger.info("Start calculating consistent initial conditions")

        # Split y0_guess into differential and algebraic
        len_rhs = rhs(0, y0_guess).shape[0]
        y0_diff, y0_alg_guess = np.split(y0_guess, [len_rhs])

        def root_fun(y0_alg):
            "Evaluates algebraic using y0_diff (fixed) and y0_alg (changed by algo)"
            y0 = np.concatenate([y0_diff, y0_alg])
            out = algebraic(0, y0)
            pybamm.logger.debug(
                "Evaluating algebraic equations at t=0, L2-norm is {}".format(
                    np.linalg.norm(out)
                )
            )
            return out

        # Find the values of y0_alg that are roots of the algebraic equations
        sol = optimize.root(
            root_fun, y0_alg_guess, method=self.root_method, tol=self.root_tol
        )
        # Return full set of consistent initial conditions (y0_diff unchanged)
        y0_consistent = np.concatenate([y0_diff, sol.x])

        if sol.success and np.all(sol.fun < self.root_tol * len(sol.x)):
            pybamm.logger.info("Finish calculating consistent initial conditions")
            return y0_consistent
        elif not sol.success:
            raise pybamm.SolverError(
                "Could not find consistent initial conditions: {}".format(sol.message)
            )
        else:
            raise pybamm.SolverError(
                """
                Could not find consistent initial conditions: solver terminated
                successfully, but maximum solution error ({}) above tolerance ({})
                """.format(
                    np.max(sol.fun), self.root_tol * len(sol.x)
                )
            )

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
            A function that takes in t, y and ydot and returns the Jacobian
        """
        raise NotImplementedError
