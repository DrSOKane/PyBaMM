#
# Standard electrical parameters
#
import pybamm
import numpy as np


def abs_non_zero(x):
    if x == 0:  # pragma: no cover
        return 1
    else:
        return abs(x)


# --------------------------------------------------------------------------------------
# Dimensional Parameters
I_typ = pybamm.Parameter("Typical current [A]")
Q = pybamm.Parameter("Cell capacity [A.h]")
C_rate = abs(I_typ / Q)
n_electrodes_parallel = pybamm.Parameter(
    "Number of electrodes connected in parallel to make a cell"
)
i_typ = pybamm.Function(
    abs_non_zero, (I_typ / (n_electrodes_parallel * pybamm.geometric_parameters.A_cc))
)
voltage_low_cut_dimensional = pybamm.Parameter("Lower voltage cut-off [V]")
voltage_high_cut_dimensional = pybamm.Parameter("Upper voltage cut-off [V]")
current_with_time = pybamm.FunctionParameter(
    "Current function", pybamm.t
) * pybamm.Function(np.sign, I_typ)
dimensional_current_density_with_time = i_typ * current_with_time
dimensional_current_with_time = I_typ * current_with_time
