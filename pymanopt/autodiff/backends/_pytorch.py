"""
Module containing functions to differentiate functions using pytorch.
"""
import functools

try:
    import torch
except ImportError:
    torch = None
else:
    from torch import autograd

from ._backend import Backend
from .. import make_tracing_backend_decorator
from ...tools import flatten_arguments, group_return_values


class _PyTorchBackend(Backend):
    def __init__(self):
        super().__init__("PyTorch")

    @staticmethod
    def is_available():
        return torch is not None and torch.__version__ >= "0.4.1"

    @Backend._assert_backend_available
    def is_compatible(self, function, arguments):
        return callable(function)

    @Backend._assert_backend_available
    def compile_function(self, function, arguments):
        flattened_arguments = flatten_arguments(arguments)

        if len(flattened_arguments) == 1:
            @functools.wraps(function)
            def unary_function(argument):
                return function(torch.from_numpy(argument)).numpy()
            return unary_function

        @functools.wraps(function)
        def nary_function(arguments):
            return function(
                *map(torch.from_numpy, flatten_arguments(arguments))).numpy()
        return nary_function

    def _sanitize_gradient(self, tensor):
        if tensor.grad is None:
            return torch.zeros(tensor.shape, dtype=tensor.dtype).numpy()
        return tensor.grad.numpy()

    def _sanitize_gradients(self, tensors):
        return list(map(self._sanitize_gradient, tensors))

    @Backend._assert_backend_available
    def compute_gradient(self, function, arguments):
        flattened_arguments = flatten_arguments(arguments)

        if len(flattened_arguments) == 1:
            def unary_gradient(argument):
                torch_argument = torch.from_numpy(argument)
                torch_argument.requires_grad_()
                function(torch_argument).backward()
                return self._sanitize_gradient(torch_argument)
            return unary_gradient

        def nary_gradient(arguments):
            torch_arguments = []
            for argument in flatten_arguments(arguments):
                torch_argument = torch.from_numpy(argument)
                torch_argument.requires_grad_()
                torch_arguments.append(torch_argument)
            function(*torch_arguments).backward()
            return self._sanitize_gradients(torch_arguments)
        return group_return_values(nary_gradient, arguments)

    @Backend._assert_backend_available
    def compute_hessian(self, function, arguments):
        flattened_arguments = flatten_arguments(arguments)

        if len(flattened_arguments) == 1:
            def unary_hessian(point, vector):
                x = torch.from_numpy(point)
                v = torch.from_numpy(vector)
                x.requires_grad_()
                fx = function(x)
                (grad_fx,) = autograd.grad(fx, x, create_graph=True,
                                           allow_unused=True)
                (grad_fx * v).sum().backward()
                return self._sanitize_gradient(x)
            return unary_hessian

        def nary_hessian(points, vectors):
            xs = []
            for point in flatten_arguments(points):
                x = torch.from_numpy(point)
                x.requires_grad_()
                xs.append(x)
            vs = [torch.from_numpy(vector)
                  for vector in flatten_arguments(vectors)]
            fx = function(*xs)
            fx.requires_grad_()
            gradients = autograd.grad(fx, xs, create_graph=True,
                                      allow_unused=True)
            dot_product = 0
            for gradient, vector in zip(gradients, vs):
                dot_product += (gradient * vector).sum()
            dot_product.backward()
            return self._sanitize_gradients(xs)
        return group_return_values(nary_hessian, arguments)


PyTorch = make_tracing_backend_decorator(_PyTorchBackend)
