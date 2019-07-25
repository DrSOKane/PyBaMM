#
# Base battery model class
#

import pybamm
import os
from collections import OrderedDict


class BaseBatteryModel(pybamm.BaseModel):
    """
    Base model class with some default settings and required variables

    **Extends:** :class:`pybamm.BaseModel`
    """

    def __init__(self, options=None, name="Unnamed battery model"):
        super().__init__(name)
        self.options = options
        self.set_standard_output_variables()
        self.submodels = OrderedDict()  # ordered dict not default in 3.5
        self._built = False

    @property
    def default_parameter_values(self):
        # Default parameter values, geometry, submesh, spatial methods and solver
        # Lion parameters left as default parameter set for tests
        input_path = os.path.join(
            pybamm.root_dir(), "input", "parameters", "lithium-ion"
        )
        return pybamm.ParameterValues(
            os.path.join(
                input_path, "mcmb2528_lif6-in-ecdmc_lico2_parameters_Dualfoil.csv"
            ),
            {
                "Typical current [A]": 1,
                "Typical voltage [V]": 3.5,
                "Current function": pybamm.GetConstantCurrent(
                    pybamm.standard_parameters_lithium_ion.I_typ
                ),
                "Voltage function": pybamm.GetConstantVoltage(
                    pybamm.standard_parameters_lithium_ion.V_typ
                ),
                "Electrolyte diffusivity": os.path.join(
                    input_path, "electrolyte_diffusivity_Capiglia1999.py"
                ),
                "Electrolyte conductivity": os.path.join(
                    input_path, "electrolyte_conductivity_Capiglia1999.py"
                ),
                "Negative electrode OCV": os.path.join(
                    input_path, "graphite_mcmb2528_ocp_Dualfoil.py"
                ),
                "Positive electrode OCV": os.path.join(
                    input_path, "lico2_ocp_Dualfoil.py"
                ),
                "Negative electrode diffusivity": os.path.join(
                    input_path, "graphite_mcmb2528_diffusivity_Dualfoil.py"
                ),
                "Positive electrode diffusivity": os.path.join(
                    input_path, "lico2_diffusivity_Dualfoil.py"
                ),
                "Negative electrode reaction rate": os.path.join(
                    input_path, "graphite_electrolyte_reaction_rate.py"
                ),
                "Positive electrode reaction rate": os.path.join(
                    input_path, "lico2_electrolyte_reaction_rate.py"
                ),
                "Negative electrode OCV entropic change": os.path.join(
                    input_path, "graphite_entropic_change_Moura.py"
                ),
                "Positive electrode OCV entropic change": os.path.join(
                    input_path, "lico2_entropic_change_Moura.py"
                ),
            },
        )

    @property
    def default_geometry(self):
        return pybamm.Geometry("1D macro", "1+1D micro")

    @property
    def default_var_pts(self):
        var = pybamm.standard_spatial_vars
        return {
            var.x_n: 40,
            var.x_s: 25,
            var.x_p: 35,
            var.r_n: 10,
            var.r_p: 10,
            var.y: 10,
            var.z: 10,
        }

    @property
    def default_submesh_types(self):
        return {
            "negative electrode": pybamm.Uniform1DSubMesh,
            "separator": pybamm.Uniform1DSubMesh,
            "positive electrode": pybamm.Uniform1DSubMesh,
            "negative particle": pybamm.Uniform1DSubMesh,
            "positive particle": pybamm.Uniform1DSubMesh,
            "current collector": pybamm.Uniform1DSubMesh,
        }

    @property
    def default_spatial_methods(self):
        return {
            "macroscale": pybamm.FiniteVolume,
            "negative particle": pybamm.FiniteVolume,
            "positive particle": pybamm.FiniteVolume,
            "current collector": pybamm.FiniteVolume,
        }

    @property
    def default_solver(self):
        """
        Create and return the default solver for this model
        """
        try:
            default_solver = pybamm.ScikitsOdeSolver()
        except ImportError:
            default_solver = pybamm.ScipySolver()

        return default_solver

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, extra_options):
        default_options = {
            "bc_options": {"dimensionality": 0},
            "surface form": False,
            "convection": False,
            "thermal": None,
            "first-order potential": "linear",
            "side reactions": [],
            "interfacial surface area": "constant",
            "higher-order concentration": "composite",
            "problem type": "galvanostatic",
        }
        options = default_options
        # any extra options overwrite the default options
        if extra_options is not None:
            for name, opt in extra_options.items():
                if name in default_options:
                    options[name] = opt
                else:
                    raise pybamm.OptionError("option {} not recognised".format(name))

        # Some standard checks to make sure options are compatible
        if (
            isinstance(self, (pybamm.lead_acid.LOQS, pybamm.lead_acid.Composite))
            and options["surface form"] is False
        ):
            if options["bc_options"]["dimensionality"] == 1:
                raise pybamm.ModelError(
                    "must use surface formulation to solve {!s} in 2D".format(self)
                )
            if len(options["side reactions"]) > 0:
                raise pybamm.ModelError(
                    """
                    must use surface formulation to solve {!s} with side reactions
                    """.format(
                        self
                    )
                )

        self._options = options

    def set_standard_output_variables(self):
        # Standard output variables

        # Interfacial current
        self.variables.update(
            {
                "Negative electrode current density": None,
                "Positive electrode current density": None,
                "Electrolyte current density": None,
                "Interfacial current density": None,
                "Exchange current density": None,
            }
        )
        self.variables.update(
            {
                "Negative electrode current density [A.m-2]": None,
                "Positive electrode current density [A.m-2]": None,
                "Electrolyte current density [A.m-2]": None,
                "Interfacial current density [A.m-2]": None,
                "Exchange current density [A.m-2]": None,
            }
        )

        # Voltage
        self.variables.update(
            {
                "Negative electrode open circuit potential": None,
                "Positive electrode open circuit potential": None,
                "Average negative electrode open circuit potential": None,
                "Average positive electrode open circuit potential": None,
                "Average open circuit voltage": None,
                "Measured open circuit voltage": None,
                "Terminal voltage": None,
            }
        )
        self.variables.update(
            {
                "Negative electrode open circuit potential [V]": None,
                "Positive electrode open circuit potential [V]": None,
                "Average negative electrode open circuit potential [V]": None,
                "Average positive electrode open circuit potential [V]": None,
                "Average open circuit voltage [V]": None,
                "Measured open circuit voltage [V]": None,
                "Terminal voltage [V]": None,
            }
        )

        # Overpotentials
        self.variables.update(
            {
                "Negative reaction overpotential": None,
                "Positive reaction overpotential": None,
                "Average negative reaction overpotential": None,
                "Average positive reaction overpotential": None,
                "Average reaction overpotential": None,
                "Average electrolyte overpotential": None,
                "Average solid phase ohmic losses": None,
            }
        )
        self.variables.update(
            {
                "Negative reaction overpotential [V]": None,
                "Positive reaction overpotential [V]": None,
                "Average negative reaction overpotential [V]": None,
                "Average positive reaction overpotential [V]": None,
                "Average reaction overpotential [V]": None,
                "Average electrolyte overpotential [V]": None,
                "Average solid phase ohmic losses [V]": None,
            }
        )

        # Concentration
        self.variables.update(
            {
                "Electrolyte concentration": None,
                "Electrolyte concentration [mol.m-3]": None,
            }
        )

        # Potential
        self.variables.update(
            {
                "Negative electrode potential": None,
                "Positive electrode potential": None,
                "Electrolyte potential": None,
            }
        )

        self.variables = {}

        # Current
        icell = pybamm.electrical_parameters.current_density_with_time
        icell_dim = pybamm.electrical_parameters.dimensional_current_density_with_time
        I = pybamm.electrical_parameters.dimensional_current_with_time
        self.variables.update(
            {
                "Total current density": icell,
                "Total current density [A.m-2]": icell_dim,
                "Current [A]": I,
            }
        )

        # Time
        time_scale = pybamm.electrical_parameters.timescale
        self.variables.update(
            {
                "Time [s]": pybamm.t * time_scale,
                "Time [min]": pybamm.t * time_scale / 60,
                "Time [h]": pybamm.t * time_scale / 3600,
                "Discharge capacity [A.h]": I * pybamm.t * time_scale / 3600,
            }
        )

        # Spatial
        var = pybamm.standard_spatial_vars
        L_x = pybamm.geometric_parameters.L_x
        L_y = pybamm.geometric_parameters.L_y
        L_z = pybamm.geometric_parameters.L_z
        self.variables.update(
            {
                "x": var.x,
                "x [m]": var.x * L_x,
                "x_n": var.x_n,
                "x_n [m]": var.x_n * L_x,
                "x_s": var.x_s,
                "x_s [m]": var.x_s * L_x,
                "x_p": var.x_p,
                "x_p [m]": var.x_p * L_x,
            }
        )
        if self.options["bc_options"]["dimensionality"] == 1:
            self.variables.update({"y": var.y, "y [m]": var.y * L_y})
        elif self.options["bc_options"]["dimensionality"] == 2:
            self.variables.update(
                {"y": var.y, "y [m]": var.y * L_y, "z": var.z, "z [m]": var.z * L_z}
            )

    def build_model(self):
        pybamm.logger.info("Building {}".format(self.name))

        # Get the fundamental variables
        for submodel_name, submodel in self.submodels.items():
            pybamm.logger.debug(
                "Getting fundamental variables for {} submodel ({})".format(
                    submodel_name, self.name
                )
            )
            self.variables.update(submodel.get_fundamental_variables())

        # Get coupled variables
        for submodel_name, submodel in self.submodels.items():
            pybamm.logger.debug(
                "Getting coupled variables for {} submodel ({})".format(
                    submodel_name, self.name
                )
            )
            self.variables.update(submodel.get_coupled_variables(self.variables))

            # Set model equations
        for submodel_name, submodel in self.submodels.items():
            pybamm.logger.debug(
                "Setting rhs for {} submodel ({})".format(submodel_name, self.name)
            )
            submodel.set_rhs(self.variables)
            pybamm.logger.debug(
                "Setting algebraic for {} submodel ({})".format(
                    submodel_name, self.name
                )
            )
            submodel.set_algebraic(self.variables)
            pybamm.logger.debug(
                "Setting boundary conditions for {} submodel ({})".format(
                    submodel_name, self.name
                )
            )
            submodel.set_boundary_conditions(self.variables)
            pybamm.logger.debug(
                "Setting initial conditions for {} submodel ({})".format(
                    submodel_name, self.name
                )
            )
            submodel.set_initial_conditions(self.variables)
            submodel.set_events(self.variables)
            pybamm.logger.debug(
                "Updating {} submodel ({})".format(submodel_name, self.name)
            )
            self.update(submodel)

        pybamm.logger.debug("Setting voltage variables")
        self.set_voltage_variables()

        if self.options["problem type"] == "potentiostatic":
            pybamm.logger.debug("Setting cell current variables")
            self.set_cell_current_variables()

        pybamm.logger.debug("Setting SoC variables")
        self.set_soc_variables()

        self._built = True

    def set_thermal_submodel(self):

        if self.options["thermal"] is None:
            thermal_submodel = pybamm.thermal.Isothermal(self.param)
        elif self.options["thermal"] == "full":
            thermal_submodel = pybamm.thermal.Full(self.param)
        elif self.options["thermal"] == "lumped":
            thermal_submodel = pybamm.thermal.Lumped(self.param)
        else:
            raise KeyError("Unknown type of thermal model")

        self.submodels["thermal"] = thermal_submodel

    def set_voltage_variables(self):

        ocp_n = self.variables["Negative electrode open circuit potential"]
        ocp_p = self.variables["Positive electrode open circuit potential"]
        ocp_n_av = self.variables["Average negative electrode open circuit potential"]
        ocp_p_av = self.variables["Average positive electrode open circuit potential"]

        ocp_n_dim = self.variables["Negative electrode open circuit potential [V]"]
        ocp_p_dim = self.variables["Positive electrode open circuit potential [V]"]
        ocp_n_av_dim = self.variables[
            "Average negative electrode open circuit potential [V]"
        ]
        ocp_p_av_dim = self.variables[
            "Average positive electrode open circuit potential [V]"
        ]

        ocp_n_left = pybamm.BoundaryValue(ocp_n, "left")
        ocp_n_left_dim = pybamm.BoundaryValue(ocp_n_dim, "left")
        ocp_p_right = pybamm.BoundaryValue(ocp_p, "right")
        ocp_p_right_dim = pybamm.BoundaryValue(ocp_p_dim, "right")

        ocv_av = ocp_p_av - ocp_n_av
        ocv_av_dim = ocp_p_av_dim - ocp_n_av_dim
        ocv = ocp_p_right - ocp_n_left
        ocv_dim = ocp_p_right_dim - ocp_n_left_dim

        # overpotentials
        eta_r_n_av = self.variables["Average negative electrode reaction overpotential"]
        eta_r_n_av_dim = self.variables[
            "Average negative electrode reaction overpotential [V]"
        ]
        eta_r_p_av = self.variables["Average positive electrode reaction overpotential"]
        eta_r_p_av_dim = self.variables[
            "Average positive electrode reaction overpotential [V]"
        ]

        delta_phi_s_n_av = self.variables["Average negative electrode ohmic losses"]
        delta_phi_s_n_av_dim = self.variables[
            "Average negative electrode ohmic losses [V]"
        ]
        delta_phi_s_p_av = self.variables["Average positive electrode ohmic losses"]
        delta_phi_s_p_av_dim = self.variables[
            "Average positive electrode ohmic losses [V]"
        ]

        delta_phi_s_av = delta_phi_s_p_av - delta_phi_s_n_av
        delta_phi_s_av_dim = delta_phi_s_p_av_dim - delta_phi_s_n_av_dim

        eta_r_av = eta_r_p_av - eta_r_n_av
        eta_r_av_dim = eta_r_p_av_dim - eta_r_n_av_dim

        # terminal voltage
        if self.options["bc_options"]["dimensionality"] == 0:
            phi_s_p = self.variables["Positive electrode potential"]
            phi_s_p_dim = self.variables["Positive electrode potential [V]"]
            V = pybamm.BoundaryValue(phi_s_p, "right")
            V_dim = pybamm.BoundaryValue(phi_s_p_dim, "right")
        elif self.options["bc_options"]["dimensionality"] == 1:
            # TO DO: add terminal voltage in 1plus1D
            phi_s_p = self.variables["Positive electrode potential"]
            phi_s_p_dim = self.variables["Positive electrode potential [V]"]
            V = pybamm.BoundaryValue(phi_s_p, "right")
            V_dim = pybamm.BoundaryValue(phi_s_p_dim, "right")
        elif self.options["bc_options"]["dimensionality"] == 2:
            phi_s_cn = self.variables["Negative current collector potential"]
            phi_s_cp = self.variables["Positive current collector potential"]
            phi_s_cn_dim = self.variables["Negative current collector potential [V]"]
            phi_s_cp_dim = self.variables["Positive current collector potential [V]"]
            # In 2D left corresponds to the negative tab and right the positive tab
            V = pybamm.BoundaryValue(phi_s_cp, "right") - pybamm.BoundaryValue(
                phi_s_cn, "left"
            )
            V_dim = pybamm.BoundaryValue(phi_s_cp_dim, "right") - pybamm.BoundaryValue(
                phi_s_cn_dim, "left"
            )
        else:
            raise pybamm.ModelError(
                "Dimension of current collectors must be 0, 1, or 2, not {}".format(
                    self.options["bc_options"]["dimensionality"]
                )
            )

        self.variables.update(
            {
                "Average open circuit voltage": ocv_av,
                "Measured open circuit voltage": ocv,
                "Average open circuit voltage [V]": ocv_av_dim,
                "Measured open circuit voltage [V]": ocv_dim,
                "Average reaction overpotential": eta_r_av,
                "Average reaction overpotential [V]": eta_r_av_dim,
                "Average solid phase ohmic losses": delta_phi_s_av,
                "Average solid phase ohmic losses [V]": delta_phi_s_av_dim,
                "Terminal voltage": V,
                "Terminal voltage [V]": V_dim,
            }
        )

        # Battery-wide variables
        eta_e_av_dim = self.variables.get("Average electrolyte ohmic losses [V]", 0)
        eta_c_av_dim = self.variables.get("Average concentration overpotential [V]", 0)
        num_cells = pybamm.Parameter(
            "Number of cells connected in series to make a battery"
        )

        self.variables.update(
            {
                "Average battery open circuit voltage [V]": ocv_av_dim * num_cells,
                "Measured battery open circuit voltage [V]": ocv_dim * num_cells,
                "Average battery reaction overpotential [V]": eta_r_av_dim * num_cells,
                "Average battery solid phase ohmic losses [V]": delta_phi_s_av_dim
                * num_cells,
                "Average battery electrolyte ohmic losses [V]": eta_e_av_dim
                * num_cells,
                "Average battery concentration overpotential [V]": eta_c_av_dim
                * num_cells,
                "Battery voltage [V]": V_dim * num_cells,
            }
        )

        # Cut-off voltage
        voltage = self.variables["Terminal voltage"]
        self.events["Minimum voltage"] = voltage - self.param.voltage_low_cut
        self.events["Maximum voltage"] = voltage - self.param.voltage_high_cut

    def set_cell_current_variables(self):
        """
        Set variables relating to the cell current.
        """

        i_s = self.variables["Electrode current density"]
        i_e = self.variables["Electrolyte current density"]

        # probably better to average but cannot because of
        # shape errors at the moement. Also cannot take indexes
        # different than 0 as will try to evaluate...

        # tolerances in tests have been increased for now to allow for
        # this form
        i_boundary_cc = pybamm.Index(i_s, 0) + pybamm.Index(i_e, 0)

        self.variables["Current collector current density"] = i_boundary_cc

    def set_soc_variables(self):
        """
        Set variables relating to the state of charge.
        This function is overriden by the base battery models
        """
        pass

    def process_parameters_and_discretise(self, symbol):
        """
        Process parameters and discretise a symbol using default parameter values,
        geometry, etc. Note that the model needs to be built first for this to be
        possible.

        Parameters
        ----------
        symbol : :class:`pybamm.Symbol`
            Symbol to be processed

        Returns
        -------
        :class:`pybamm.Symbol`
            Processed symbol
        """
        if not self._built:
            self.build_model()

        # Set up parameters
        geometry = self.default_geometry
        parameter_values = self.default_parameter_values
        parameter_values.process_geometry(geometry)

        # Set up discretisation
        mesh = pybamm.Mesh(geometry, self.default_submesh_types, self.default_var_pts)
        disc = pybamm.Discretisation(mesh, self.default_spatial_methods)
        variables = list(self.rhs.keys()) + list(self.algebraic.keys())
        disc.set_variable_slices(variables)

        # Process
        param_symbol = parameter_values.process_symbol(symbol)
        disc_symbol = disc.process_symbol(param_symbol)

        return disc_symbol
