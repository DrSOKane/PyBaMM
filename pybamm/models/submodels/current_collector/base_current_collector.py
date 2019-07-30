#
# Base class for current collector submodels
#
import pybamm


class BaseModel(pybamm.BaseSubModel):
    """Base class for current collector submodels

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel


    **Extends:** :class:`pybamm.BaseSubModel`
    """

    def __init__(self, param):
        super().__init__(param)

    def _get_standard_potential_variables(self, phi_s_cn, phi_s_cp):
        """
        A private function to obtain the standard variables which
        can be derived from the potential in the current collector.

        Parameters
        ----------
        phi_cc : :class:`pybamm.Symbol`
            The potential in the current collector.

        Returns
        -------
        variables : dict
            The variables which can be derived from the potential in the
            current collector.
        """

        param = self.param

        V_cc = phi_s_cp - phi_s_cn

        # add more to this
        variables = {
            "Negative current collector potential": phi_s_cn,
            "Negative current collector potential [V]": phi_s_cn
            * param.potential_scale,
            "Positive current collector potential": phi_s_cp,
            "Positive current collector potential [V]": param.U_p_ref
            - param.U_n_ref
            + phi_s_cp * param.potential_scale,
            "Local current collector potential difference": V_cc,
            "Local current collector potential difference [V]": param.U_p_ref
            - param.U_n_ref
            + V_cc * param.potential_scale,
        }

        return variables

    def _get_standard_current_variables(self, i_cc, i_boundary_cc):
        """
        A private function to obtain the standard variables which
        can be derived from the current in the current collector.

        Parameters
        ----------
        i_cc : :class:`pybamm.Symbol`
            The current in the current collector.
        i_boundary_cc : :class:`pybamm.Symbol`
            The current leaving the current collector and going into the cell

        Returns
        -------
        variables : dict
            The variables which can be derived from the current in the current
            collector.
        """

        # TO DO: implement grad in 2D to get i_cc
        # just need this to get 1D models working for now
        variables = {"Current collector current density": i_boundary_cc}

        return variables
