import functools
import itertools

try:
    import theano
    import theano.tensor as T
    from theano.gradient import disconnected_grad
except ImportError:
    theano = None
    T = None

from ._backend import Backend
from .. import make_graph_backend_decorator
from ...tools import flatten_arguments, group_return_values, unpack_arguments


class _TheanoBackend(Backend):
    def __init__(self):
        super().__init__("Theano")

    @staticmethod
    def is_available():
        return theano is not None

    @Backend._assert_backend_available
    def is_compatible(self, function, arguments):
        if not isinstance(function, T.TensorVariable):
            return False
        flattened_arguments = flatten_arguments(arguments)
        return all([isinstance(argument, T.TensorVariable)
                    for argument in flattened_arguments])

    def _compile_function_without_warnings(self, *args, **kwargs):
        return theano.function(*args, **kwargs, on_unused_input="ignore")

    @Backend._assert_backend_available
    def compile_function(self, function, arguments):
        """Compiles a Theano graph into a python function."""
        flattened_arguments = flatten_arguments(arguments)
        compiled_function = self._compile_function_without_warnings(
            flattened_arguments, function)
        if len(flattened_arguments) == 1:
            return compiled_function
        return unpack_arguments(compiled_function)

    @Backend._assert_backend_available
    def compute_gradient(self, function, arguments):
        """Returns a compiled function computing the gradient of `function`
        with respect to 'arguments'.
        """
        flattened_arguments = flatten_arguments(arguments)

        if len(flattened_arguments) == 1:
            (argument,) = flattened_arguments
            gradient = T.grad(function, argument)
            return self._compile_function_without_warnings(
                flattened_arguments, gradient)

        gradient = T.grad(function, flattened_arguments)
        compiled_gradient = self._compile_function_without_warnings(
            flattened_arguments, gradient)
        return group_return_values(
            unpack_arguments(compiled_gradient), arguments)

    def _compute_unary_hessian_vector_product(self, gradient, argument):
        """Returns a function accepting two arguments to compute a
        Hessian-vector product of a scalar-valued unary function.
        """
        argument_type = argument.type()
        try:
            Rop = T.Rop(gradient, argument, argument_type)
        except NotImplementedError:
            proj = T.sum(gradient * disconnected_grad(argument_type))
            Rop = T.grad(proj, argument)
        return self._compile_function_without_warnings(
            [argument, argument_type], Rop)

    def _compute_nary_hessian_vector_product(self, gradients, arguments):
        """Returns a function accepting `2 * len(arguments)` arguments to
        compute a Hessian-vector product of a multivariate function.

        Notes
        -----
        The implementation is based on TensorFlow's '_hessian_vector_product'
        function in 'tensorflow.python.ops.gradients_impl'.
        """
        argument_types = [argument.type() for argument in arguments]
        try:
            Rop = T.Rop(gradients, arguments, argument_types)
        except NotImplementedError:
            proj = [T.sum(gradient * disconnected_grad(argument_type))
                    for gradient, argument_type in zip(gradients,
                                                       argument_types)]
            proj_grad = [T.grad(proj_elem, arguments,
                                disconnected_inputs="ignore",
                                return_disconnected="None")
                         for proj_elem in proj]
            proj_grad_transpose = map(list, zip(*proj_grad))
            proj_grad_stack = [
                T.stacklists([c for c in row if c is not None])
                for row in proj_grad_transpose]
            Rop = [T.sum(stack, axis=0) for stack in proj_grad_stack]
        return self._compile_function_without_warnings(
            list(itertools.chain(arguments, argument_types)), Rop)

    @Backend._assert_backend_available
    def compute_hessian(self, function, arguments):
        """Computes the directional derivative of the gradient, which is
        equivalent to computing a Hessian-vector product with the direction
        vector.
        """
        flattened_arguments = flatten_arguments(arguments)

        if len(flattened_arguments) == 1:
            (argument,) = flattened_arguments
            gradient = T.grad(function, argument)
            return self._compute_unary_hessian_vector_product(
                gradient, argument)

        gradients = T.grad(function, flattened_arguments)
        hessian_vector_product = self._compute_nary_hessian_vector_product(
            gradients, flattened_arguments)

        @functools.wraps(hessian_vector_product)
        def wrapper(points, vectors):
            return hessian_vector_product(*flatten_arguments(points),
                                          *flatten_arguments(vectors))
        return group_return_values(wrapper, arguments)


Theano = make_graph_backend_decorator(_TheanoBackend)
