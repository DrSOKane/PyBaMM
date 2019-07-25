#
# Single Particle Model with Electrolyte (SPMe)
#
import pybamm
from .base_lithium_ion_model import BaseModel


class SPMe(BaseModel):
    """Single Particle Model with Electrolyte (SPMe) of a lithium-ion battery.

    **Extends:** :class:`pybamm.lithium_ion.BaseModel`
    """

    def __init__(self, options=None, name="Single Particle Model with electrolyte"):
        super().__init__(options, name)

        self.set_reactions()
        self.set_current_collector_submodel()
        self.set_porosity_submodel()
        self.set_convection_submodel()
        self.set_interfacial_submodel()
        self.set_particle_submodel()
        self.set_negative_electrode_submodel()
        self.set_electrolyte_submodel()
        self.set_positive_electrode_submodel()
        self.set_thermal_submodel()

        self.build_model()

        # Massive hack for consistent delta_phi = phi_s - phi_e
        # This needs to be corrected
        for domain in ["Negative", "Positive"]:
            phi_s = self.variables[domain + " electrode potential"]
            phi_e = self.variables[domain + " electrolyte potential"]
            delta_phi = phi_s - phi_e
            s = self.submodels[domain.lower() + " interface"]
            var = s._get_standard_surface_potential_difference_variables(delta_phi)
            self.variables.update(var)

    def set_current_collector_submodel(self):

        if self.options["bc_options"]["dimensionality"] == 0:
            self.submodels["current collector"] = pybamm.current_collector.Uniform(
                self.param
            )
        elif self.options["bc_options"]["dimensionality"] == 1:
            raise NotImplementedError(
                "One-dimensional current collector submodel not implemented."
            )
        elif self.options["bc_options"]["dimensionality"] == 2:
            self.submodels[
                "current collector"
            ] = pybamm.current_collector.SingleParticlePotentialPair(self.param)
        else:
            raise pybamm.ModelError(
                "Dimension of current collectors must be 0, 1, or 2, not {}".format(
                    self.options["bc_options"]["dimensionality"]
                )
            )

    def set_porosity_submodel(self):

        self.submodels["porosity"] = pybamm.porosity.Constant(self.param)

    def set_convection_submodel(self):

        self.submodels["convection"] = pybamm.convection.NoConvection(self.param)

    def set_interfacial_submodel(self):

        self.submodels[
            "negative interface"
        ] = pybamm.interface.lithium_ion.InverseButlerVolmer(self.param, "Negative")
        self.submodels[
            "positive interface"
        ] = pybamm.interface.lithium_ion.InverseButlerVolmer(self.param, "Positive")

    def set_particle_submodel(self):

        self.submodels["negative particle"] = pybamm.particle.fickian.SingleParticle(
            self.param, "Negative"
        )
        self.submodels["positive particle"] = pybamm.particle.fickian.SingleParticle(
            self.param, "Positive"
        )

    def set_negative_electrode_submodel(self):

        self.submodels["negative electrode"] = pybamm.electrode.ohm.Composite(
            self.param, "Negative"
        )

    def set_positive_electrode_submodel(self):

        self.submodels["positive electrode"] = pybamm.electrode.ohm.Composite(
            self.param, "Positive"
        )

    def set_electrolyte_submodel(self):

        electrolyte = pybamm.electrolyte.stefan_maxwell

        self.submodels["electrolyte conductivity"] = electrolyte.conductivity.Composite(
            self.param
        )
        self.submodels["electrolyte diffusion"] = electrolyte.diffusion.Full(
            self.param, self.reactions
        )

    @property
    def default_geometry(self):
        dimensionality = self.options["bc_options"]["dimensionality"]
        if dimensionality == 0:
            return pybamm.Geometry("1D macro", "1D micro")
        elif dimensionality == 1:
            return pybamm.Geometry("1+1D macro", "(1+0)+1D micro")
        elif dimensionality == 2:
            return pybamm.Geometry("2+1D macro", "(2+0)+1D micro")

    @property
    def default_submesh_types(self):
        base_submeshes = {
            "negative electrode": pybamm.Uniform1DSubMesh,
            "separator": pybamm.Uniform1DSubMesh,
            "positive electrode": pybamm.Uniform1DSubMesh,
            "negative particle": pybamm.Uniform1DSubMesh,
            "positive particle": pybamm.Uniform1DSubMesh,
            "current collector": pybamm.Uniform1DSubMesh,
        }
        dimensionality = self.options["bc_options"]["dimensionality"]
        if dimensionality in [0, 1]:
            return base_submeshes
        elif dimensionality == 2:
            base_submeshes["current collector"] = pybamm.Scikit2DSubMesh
            return base_submeshes

    @property
    def default_spatial_methods(self):
        base_spatial_methods = {
            "macroscale": pybamm.FiniteVolume,
            "negative particle": pybamm.FiniteVolume,
            "positive particle": pybamm.FiniteVolume,
            "current collector": pybamm.FiniteVolume,
        }
        dimensionality = self.options["bc_options"]["dimensionality"]
        if dimensionality in [0, 1]:
            return base_spatial_methods
        elif dimensionality == 2:
            base_spatial_methods["current collector"] = pybamm.ScikitFiniteElement
            return base_spatial_methods

    @property
    def default_solver(self):
        """
        Create and return the default solver for this model
        """
        # Different solver depending on whether we solve ODEs or DAEs
        dimensionality = self.options["bc_options"]["dimensionality"]
        if dimensionality == 0:
            return pybamm.ScipySolver()
        else:
            return pybamm.ScikitsDaeSolver()
