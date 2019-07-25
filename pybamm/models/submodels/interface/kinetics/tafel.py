#
# Bulter volmer class
#

import pybamm
from .base_kinetics import BaseModel


class ForwardTafel(BaseModel):
    """
    Base submodel which implements the forward Tafel equation:

    .. math::
        j = j_0(c) * \\exp(\\eta_r(c))

    Parameters
    ----------
    param :
        model parameters
    domain : str
        The domain to implement the model, either: 'Negative' or 'Positive'.


    **Extends:** :class:`pybamm.interface.kinetics.BaseModel`
    """

    def __init__(self, param, domain):
        super().__init__(param, domain)

    def _get_kinetics(self, j0, ne, eta_r):
        return j0 * pybamm.exp((ne / 2) * eta_r)


class BackwardTafel(BaseModel):
    """
    Base submodel which implements the backward Tafel equation:

    .. math::
        j = -j_0(c) * \\exp(-\\eta_r(c))

    Parameters
    ----------
    param :
        model parameters
    domain : str
        The domain to implement the model, either: 'Negative' or 'Positive'.


    **Extends:** :class:`pybamm.interface.kinetics.BaseModel`
    """

    def __init__(self, param, domain):
        super().__init__(param, domain)

    def _get_kinetics(self, j0, ne, eta_r):
        return -j0 * pybamm.exp(-(ne / 2) * eta_r)
