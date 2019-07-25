#
# First-order Butler-Volmer kinetics
#

from ..kinetics.base_first_order_kinetics import BaseFirstOrderKinetics


class BaseInverseFirstOrderKinetics(BaseFirstOrderKinetics):
    """
    Base inverse first-order kinetics

    Parameters
    ----------
    param :
        model parameters
    domain : str
        The domain to implement the model, either: 'Negative' or 'Positive'.


    **Extends:** :class:`pybamm.interface.kinetics.BaseFirstOrderKinetics`
    """

    def __init__(self, param, domain):
        super().__init__(param, domain)

    def get_coupled_variables(self, variables):
        # Unpack
        delta_phi_0 = variables[
            "Leading-order average "
            + self.domain.lower()
            + " electrode surface potential difference"
        ]
        c_e_0 = variables["Leading-order average electrolyte concentration"]
        c_e_av = variables[
            "Average " + self.domain.lower() + " electrolyte concentration"
        ]
        c_e_1_av = (c_e_av - c_e_0) / self.param.C_e

        # Get derivatives of leading-order terms
        dj_dc_0 = sum(
            reaction_submodel._get_dj_dc(variables)
            for reaction_submodel in self.reaction_submodels
        )
        dj_ddeltaphi_0 = sum(
            reaction_submodel._get_dj_ddeltaphi(variables)
            for reaction_submodel in self.reaction_submodels
        )

        delta_phi_1_av = -dj_dc_0 * c_e_1_av / dj_ddeltaphi_0
        delta_phi = delta_phi_0 + self.param.C_e * delta_phi_1_av

        # Update variables dictionary
        variables.update(
            self._get_standard_surface_potential_difference_variables(delta_phi)
        )

        return variables
