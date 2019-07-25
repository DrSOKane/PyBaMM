#
# Base solver class
#
import pybamm
import numpy as np


class OdeSolver(pybamm.BaseSolver):
    """Solve a discretised model.

    Parameters
    ----------
    tolerance : float, optional
        The tolerance for the solver (default is 1e-8).
    """

    def __init__(self, method=None, tol=1e-8):
        super().__init__(method, tol)

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
        concatenated_rhs, y0, model_events, jac_rhs = self.set_up(model)
        set_up_time = timer.time() - start_time

        # Create function to evaluate rhs
        def dydt(t, y):
            pybamm.logger.debug("Evaluating RHS for {} at t={}".format(model.name, t))
            y = y[:, np.newaxis]
            dy = concatenated_rhs.evaluate(t, y, known_evals={})[0]
            return dy[:, 0]

        # Create event-dependent function to evaluate events
        def event_fun(event):
            def eval_event(t, y):
                return event.evaluate(t, y)

            return eval_event

        events = [event_fun(event) for event in model_events.values()]

        # Create function to evaluate jacobian
        if jac_rhs is not None:

            def jacobian(t, y):
                return jac_rhs.evaluate(t, y, known_evals={})[0]

        else:
            jacobian = None

        # Solve
        solve_start_time = timer.time()
        pybamm.logger.info("Calling ODE solver")
        solution = self.integrate(
            dydt,
            y0,
            t_eval,
            events=events,
            mass_matrix=model.mass_matrix.entries,
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
        y0 : :class:`numpy.array`
            Vector of initial conditions
        events : dict
            Dictionary of events at which the model should terminate
        jac_rhs : :class:`pybamm.SparseStack`
            Jacobian matrix for the differential equations

        Raises
        ------
        :class:`pybamm.SolverError`
            If the model contains any algebraic equations (in which case a DAE solver
            should be used instead)

        """
        if len(model.algebraic) > 0:
            raise pybamm.SolverError(
                """Cannot use ODE solver to solve model with DAEs"""
            )

        concatenated_rhs = model.concatenated_rhs
        events = model.events
        if model.use_simplify:
            # set up simplification object, for re-use of dict
            simp = pybamm.Simplification()
            # create simplified rhs and event expressions
            pybamm.logger.info("Simplifying RHS")
            concatenated_rhs = simp.simplify(concatenated_rhs)

            pybamm.logger.info("Simplifying events")
            events = {name: simp.simplify(event) for name, event in events.items()}

        y0 = model.concatenated_initial_conditions[:, 0]

        if model.use_jacobian:
            # Create Jacobian from simplified rhs
            y = pybamm.StateVector(slice(0, np.size(y0)))

            pybamm.logger.info("Calculating jacobian")
            jac_rhs = concatenated_rhs.jac(y)
            if model.use_simplify:
                pybamm.logger.info("Simplifying jacobian")
                jac_rhs = simp.simplify(jac_rhs)

            if model.use_to_python:
                pybamm.logger.info("Converting jacobian to python")
                jac_rhs = pybamm.EvaluatorPython(jac_rhs)

        else:
            jac_rhs = None

        if model.use_to_python:
            pybamm.logger.info("Converting RHS to python")
            concatenated_rhs = pybamm.EvaluatorPython(concatenated_rhs)
            pybamm.logger.info("Converting events to python")
            events = {
                name: pybamm.EvaluatorPython(event) for name, event in events.items()
            }

        return concatenated_rhs, y0, events, jac_rhs

    def integrate(
        self, derivs, y0, t_eval, events=None, mass_matrix=None, jacobian=None
    ):
        """
        Solve a model defined by dydt with initial conditions y0.

        Parameters
        ----------
        derivs : method
            A function that takes in t and y and returns the time-derivative dydt
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
            A function that takes in t and y and returns the Jacobian
        """
        raise NotImplementedError
