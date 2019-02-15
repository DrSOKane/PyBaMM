#
# Unary operator classes and methods
#
import pybamm
import numpy as np


class UnaryOperator(pybamm.Symbol):
    """A node in the expression tree representing a unary operator
    (e.g. '-', grad, div)

    Derived classes will specify the particular operator

    **Extends:** :class:`Symbol`

    Parameters
    ----------

    name : str
        name of the node
    child : :class:`Symbol`
        child node

    """

    def __init__(self, name, child):
        super().__init__(name, children=[child], domain=child.domain)

    def __str__(self):
        """ See :meth:`pybamm.Symbol.__str__()`. """
        return "{}({!s})".format(self.name, self.children[0])


class Negate(UnaryOperator):
    """A node in the expression tree representing a `-` negation operator

    **Extends:** :class:`UnaryOperator`
    """

    def __init__(self, child):
        """ See :meth:`pybamm.UnaryOperator.__init__()`. """
        super().__init__("-", child)

    def evaluate(self, t=None, y=None):
        """ See :meth:`pybamm.Symbol.evaluate()`. """
        return -self.children[0].evaluate(t, y)

    def __str__(self):
        """ See :meth:`pybamm.Symbol.__str__()`. """
        return "{}{!s}".format(self.name, self.children[0])


class AbsoluteValue(UnaryOperator):
    """A node in the expression tree representing an `abs` operator

    **Extends:** :class:`UnaryOperator`
    """

    def __init__(self, child):
        """ See :meth:`pybamm.UnaryOperator.__init__()`. """
        super().__init__("abs", child)

    def evaluate(self, t=None, y=None):
        """ See :meth:`pybamm.Symbol.evaluate()`. """
        return np.abs(self.children[0].evaluate(t, y))


class SpatialOperator(UnaryOperator):
    """A node in the expression tree representing a unary spatial operator
    (e.g. grad, div)

    Derived classes will specify the particular operator

    This type of node will be replaced by the :class:`BaseDiscretisation`
    class with a :class:`Matrix`

    **Extends:** :class:`UnaryOperator`

    Parameters
    ----------

    name : str
        name of the node
    child : :class:`Symbol`
        child node

    """

    def __init__(self, name, child):
        super().__init__(name, child)


class Gradient(SpatialOperator):
    """A node in the expression tree representing a grad operator

    **Extends:** :class:`SpatialOperator`
    """

    def __init__(self, child):
        super().__init__("grad", child)


class Divergence(SpatialOperator):
    """A node in the expression tree representing a div operator

    **Extends:** :class:`SpatialOperator`
    """

    def __init__(self, child):
        super().__init__("div", child)


class Broadcast(SpatialOperator):
    """A node in the expression tree representing a broadcasting operator.
    Broadcasts a child (which *must* have empty domain) to a specified domain. After
    discretisation, this will evaluate to an array of the right shape for the specified
    domain.

    Parameters
    ----------
    child : :class:`Symbol`
        child node
    domain : iterable of string
        the domain to broadcast the child to
    name : string
        name of the node

    **Extends:** :class:`SpatialOperator`
    """

    def __init__(self, child, domain, name=None):
        if child.domain != []:
            raise pybamm.DomainError(
                """Domain of a broadcasted child must be [] but is '{}'""".format(
                    child.domain
                )
            )
        if name is None:
            name = "broadcast"
        super().__init__(name, child)
        # overwrite child domain ([]) with specified broadcasting domain
        self.domain = domain


class NumpyBroadcast(Broadcast):
    """A node in the expression tree implementing a broadcasting operator using numpy.
    Broadcasts a child (which *must* have empty domain) to a specified domain. To do
    this, creates a np array of ones of the same shape as the submesh domain, and then
    multiplies the child by that array upon evaluation

    Parameters
    ----------
    child : :class:`Symbol`
        child node
    domain : iterable of string
        the domain to broadcast the child to
    mesh : mesh class
        the mesh used for discretisation

    **Extends:** :class:`SpatialOperator`
    """

    def __init__(self, child, domain, mesh):
        super().__init__(child, domain, name="numpy broadcast")
        # determine broadcasting vector size (size 1 if the domain is empty)
        if domain == []:
            self.broadcasting_vector_size = 1
        else:
            self.broadcasting_vector_size = sum([mesh[dom].npts for dom in domain])
        # create broadcasting vector (vector of ones with shape determined by the
        # domain)
        self.broadcasting_vector = np.ones(self.broadcasting_vector_size)

    def evaluate(self, t=None, y=None):
        """ See :meth:`pybamm.Symbol.evaluate()`. """
        child = self.children[0]
        child_eval = child.evaluate(t, y)
        # if child is a vector, add a dimension for broadcasting
        if isinstance(child, pybamm.Vector):
            return child_eval[:, np.newaxis] * self.broadcasting_vector
        # if child is a state vector, check that it has the right shape and then
        # broadcast
        elif isinstance(child, pybamm.StateVector):
            assert child_eval.shape[0] == 1, ValueError(
                """child_eval should have shape (1,n), not {}""".format(
                    child_eval.shape
                )
            )
            return np.repeat(child_eval, self.broadcasting_vector_size, axis=0)
        # otherwise just do normal multiplication
        else:
            return child_eval * self.broadcasting_vector


#
# Methods to call Gradient and Divergence
#


def grad(expression):
    """convenience function for creating a :class:`Gradient`

    Parameters
    ----------

    expression : :class:`Symbol`
        the gradient will be performed on this sub-expression

    Returns
    -------

    :class:`Gradient`
        the gradient of ``expression``
    """

    return Gradient(expression)


def div(expression):
    """convenience function for creating a :class:`Divergence`

    Parameters
    ----------

    expression : :class:`Symbol`
        the divergence will be performed on this sub-expression

    Returns
    -------

    :class:`Divergence`
        the divergence of ``expression``
    """

    return Divergence(expression)
