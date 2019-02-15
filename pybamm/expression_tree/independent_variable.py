#
# IndependentVariable class
#
import pybamm


class IndependentVariable(pybamm.Symbol):
    """A node in the expression tree representing an independent variable

    Used for expressing functions depending on a spatial variable or time

    Parameters
    ----------
    name : str
        name of the node
    domain : iterable of str
        list of domains that this variable is valid over

    *Extends:* :class:`Symbol`
    """

    def __init__(self, name, domain=[]):
        super().__init__(name, domain=domain)


class Time(IndependentVariable):
    """A node in the expression tree representing time

    *Extends:* :class:`Symbol`
    """

    def __init__(self):
        super().__init__("time")

    def evaluate(self, t, y=None):
        """ See :meth:`pybamm.Symbol.evaluate()`. """
        if t is None:
            raise ValueError("t must be provided")
        return t


class Space(IndependentVariable):
    """A node in the expression tree representing time

    Parameters
    ----------
    name : str
        name of the node
    domain : iterable of str
        list of domains that this variable is valid over

    *Extends:* :class:`Symbol`
    """

    def __init__(self, domain):
        if domain is []:
            raise ValueError("domain must be provided")
        name = "space ({})".format(domain)
        super().__init__(name, domain=domain)


# the independent variable time
t = Time()
