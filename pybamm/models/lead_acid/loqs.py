#
# Lead-acid LOQS model
#
import pybamm

import os


class LOQS(pybamm.BaseModel):
    """Leading-Order Quasi-Static model for lead-acid.

    Attributes
    ----------

    rhs: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the rhs
    initial_conditions: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the initial conditions
    boundary_conditions: dict
        A dictionary that maps expressions (variables) to expressions that represent
        the boundary conditions
    variables: dict
        A dictionary that maps strings to expressions that represent
        the useful variables

    """

    def __init__(self):
        super().__init__()

        whole_cell = ["negative electrode", "separator", "positive electrode"]
        # Variables
        c = pybamm.Variable("c", domain=[])
        epsn = pybamm.Variable("epsn", domain=[])
        epss = pybamm.Variable("epss", domain=[])
        epsp = pybamm.Variable("epsp", domain=[])

        # Current function
        icell = pybamm.standard_parameters_lead_acid.current_with_time
        # Parameters and functions
        ln = pybamm.standard_parameters.ln
        ls = pybamm.standard_parameters.ls
        lp = pybamm.standard_parameters.lp
        sn = pybamm.standard_parameters_lead_acid.sn
        sp = pybamm.standard_parameters_lead_acid.sp
        beta_surf_n = pybamm.standard_parameters_lead_acid.beta_surf_n
        beta_surf_p = pybamm.standard_parameters_lead_acid.beta_surf_p
        iota_ref_n = pybamm.standard_parameters_lead_acid.iota_ref_n
        iota_ref_p = pybamm.standard_parameters_lead_acid.iota_ref_p
        U_Pb = pybamm.standard_parameters_lead_acid.U_Pb_ref
        U_PbO2 = pybamm.standard_parameters_lead_acid.U_PbO2_ref
        # Initial conditions
        c_init = pybamm.standard_parameters_lead_acid.c_init
        epsn_init = pybamm.standard_parameters_lead_acid.epsn_init
        epss_init = pybamm.standard_parameters_lead_acid.epss_init
        epsp_init = pybamm.standard_parameters_lead_acid.epsp_init

        # ODEs
        jn = icell / ln
        jp = -icell / lp
        depsndt = -beta_surf_n * jn
        depspdt = -beta_surf_p * jp
        dcdt = (
            1
            / (ln * epsn + ls * epss + lp * epsp)
            * ((sn - sp) * icell - c * (ln * depsndt + lp * depspdt))
        )
        self.rhs = {c: dcdt, epsn: depsndt, epss: pybamm.Scalar(0), epsp: depspdt}
        # Initial conditions
        self.initial_conditions = {
            c: c_init,
            epsn: epsn_init,
            epss: epss_init,
            epsp: epsp_init,
        }
        # ODE model -> no boundary conditions
        self.boundary_conditions = {}

        # Variables
        Phi = -U_Pb - jn / (2 * iota_ref_n * c)
        V = Phi + U_PbO2 - jp / (2 * iota_ref_p * c)
        # Phisn = pybamm.Scalar(0)
        # Phisp = V
        # Concatenate variables
        # eps = pybamm.Concatenation(epsn, epss, epsp)
        # Phis = pybamm.Concatenation(Phisn, pybamm.Scalar(0), Phisp)
        # self.variables = {"c": c, "eps": eps, "Phi": Phi, "Phis": Phis, "V": V}
        self.variables = {
            "c": pybamm.Broadcast(c, whole_cell),
            "Phi": pybamm.Broadcast(Phi, whole_cell),
            "V": V,
            "int(epsilon_times_c)dx": (ln * epsn + ls * epss + lp * epsp) * c,
        }

        # Overwrite default parameter values
        self.default_parameter_values = pybamm.ParameterValues(
            "input/parameters/lead-acid/default.csv",
            {
                "current scale": 1,
                "current function": os.path.join(
                    os.getcwd(),
                    "pybamm",
                    "parameters",
                    "standard_current_functions",
                    "constant_current.py",
                ),
            },
        )
