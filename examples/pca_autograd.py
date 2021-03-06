import autograd.numpy as np

import pymanopt
from pymanopt.manifolds import Stiefel
from pymanopt.solvers import TrustRegions


if __name__ == "__main__":
    # Generate random data with highest variance in first 2 dimensions
    X = np.diag([3, 2, 1]).dot(np.random.randn(3, 200))

    # Cost function is the squared reconstruction error
    @pymanopt.function.Autograd
    def cost(w):
        return np.sum(np.sum((X - np.dot(w, np.dot(w.T, X))) ** 2))

    # A solver that involves the hessian
    solver = TrustRegions()

    # Projection matrices onto a two dimensional subspace
    manifold = Stiefel(3, 2)

    # Solve the problem with pymanopt
    problem = pymanopt.Problem(manifold, cost)
    wopt = solver.solve(problem)

    print('The following projection matrix was found to minimise '
          'the squared reconstruction error: ')
    print(wopt)
