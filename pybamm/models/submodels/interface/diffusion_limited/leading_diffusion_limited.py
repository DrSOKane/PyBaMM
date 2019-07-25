#
# Leading-order diffusion limited kinetics
#
from .base_diffusion_limited import BaseModel


class LeadingOrderDiffusionLimited(BaseModel):
    """
    Leading-order submodel for diffusion-limited kinetics

    Parameters
    ----------
    param :
        model parameters
    domain : str
        The domain to implement the model, either: 'Negative' or 'Positive'.


    **Extends:** :class:`pybamm.interface.diffusion_limited.BaseModel`
    """

    def __init__(self, param, domain):
        super().__init__(param, domain)

    def _get_diffusion_limited_current_density(self, variables):
        if self.domain == "Negative":
            j_p = variables[
                "Positive electrode"
                + self.reaction_name
                + " interfacial current density"
            ].orphans[0]
            j = -self.param.l_p * j_p / self.param.l_n

        return j
