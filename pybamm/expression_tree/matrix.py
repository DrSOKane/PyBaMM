#
# Matrix class
#
import pybamm


class Matrix(pybamm.Array):
    """node in the expression tree that holds a matrix type (e.g. :class:`numpy.array`)

    **Extends:** :class:`Array`

    Parameters
    ----------

    entries : numpy.array
        the array associated with the node
    name : str, optional
        the name of the node

    """

    def __init__(self, entries, name=None, domain=[]):
        if name is None:
            name = "Matrix of shape {!s}".format(entries.shape)
        super().__init__(entries, name=name, domain=domain)
