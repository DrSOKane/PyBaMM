from pybamm import Parameter, Scalar, FullBroadcast


def outer_SEI_limited_dead_lithium_OKane2022(L_outer):
    """
    Dead lithium decay rate [s-1].
    References
    ----------
    .. [1] O’Kane, Simon EJ, Ian D. Campbell, Mohamed WJ Marzook, Gregory J. Offer, and
    Monica Marinescu. "Physical origin of the differential voltage minimum associated
    with lithium plating in Li-ion batteries." Journal of The Electrochemical Society
    167, no. 9 (2020): 090540.
    Parameters
    ----------
    L_outer : :class:`pybamm.Symbol`
        Outer SEI thickness [m]
    Returns
    -------
    :class:`pybamm.Symbol`
        Dead lithium decay rate [s-1]
    """

    gamma_0 = Parameter("Dead lithium decay constant [s-1]")
    L_outer_0 = Parameter("Initial outer SEI thickness [m]")
    zero = FullBroadcast(
            Scalar(0), "negative electrode", "current collector"
        )

    if L_outer == zero:  # Avoid division by zero error if no outer SEI
        gamma = gamma_0
    else:
        gamma = gamma_0 * L_outer_0 / L_outer

    return gamma
