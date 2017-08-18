from __future__ import print_function, division

import time
from copy import deepcopy

from pymanopt.solvers.solver import Solver
from pymanopt import tools


Strategy = tools.make_enum("Strategy", "direct inverse alternate".split())


def get_strategy_name(strategy):
    return Strategy._fields[strategy]


class BarzilaiBorwein(Solver):
    """
    Riemannian Barzilai-Borwein solver with non-monotone line-search based on
    barzilaiborwein.m from the manopt MATLAB package.
    """

    def __init__(self, lambdamax=1e3, lambdamin=1e-3, lambda0=1e-1,
                 strategy=Strategy.direct, *args, **kwargs):
        super(BarzilaiBorwein, self).__init__(*args, **kwargs)

        # Upper and lower bound for the Barzilai-Borwein stepsize
        self._lambdamax = lambdamax
        self._lambdamin = lambdamin
        # Initial Barzilai-Borwein stepsize
        self._lambda0 = lambda0

        # Barzilai-Borwein strategy (direct, inverse or alternate)
        self._strategy = strategy
        if strategy == Strategy.direct:
            self._apply_strategy = self._apply_direct_strategy
        elif strategy == Strategy.inverse:
            self._apply_strategy = self._apply_inverse_strategy
        elif strategy == Strategy.alternate:
            self._apply_strategy = self._apply_alternate_strategy
        else:
            raise ValueError("Invalid strategy parameter '%s'" % strategy)

        # Define the line-search parameters.
        self._linesearch = lambda *x: 1
        # The Armijo sufficient decrease parameter.
        self._ls_suff_decr = 1e-4
        # The previous steps checked in the non-monotone line-search strategy.
        self._ls_nmsteps = 10

    def solve(self, problem, x=None):
        man = problem.manifold
        verbosity = problem.verbosity
        objective = problem.cost
        gradient = problem.grad

        # TODO: Implement linesearch hint.
        linesearch = self._linesearch

        # If no starting point is specified, generate one at random.
        if x is None:
            x = man.rand()

        # Initialize iteration counter and timer
        iter = 0
        stepsize = np.nan
        time0 = time.time()

        if verbosity >= 1:
            print("Optimizing...")
        if verbosity >= 2:
            print(" iter\t\t   cost val\t    grad. norm")

        cost = objective(x)
        grad = gradient(x)
        gradnorm = man.norm(x, grad)

        # TODO: Add memoization.

        lambda_ = self._lambda0

        self._start_optlog(
            extraiterfields=["gradnorm"],
            solverparams={"lambdamax": self._lambdamax,
                          "lambdamin": self._lambdamin,
                          "lambda0": self._lambda0,
                          "strategy": get_strategy_name(self._strategy)})

        while True:
            if verbosity >= 2:
                print("%5d\t%+.16e\t%.8e" % (iter, cost, gradnorm))

            if self._logverbosity >= 2:
                self._append_optlog(iter, x, cost, gradnorm=gradnorm)

            stop_reason = self._check_stopping_criterion(
                time0, gradnorm=gradnorm, iter=iter + 1, stepsize=stepsize)

            if stop_reason:
                if verbosity >= 1:
                    print(stop_reason)
                    print("")
                break

            # Pick the descent direction
            # XXX: Is this right?
            desc_dir = x - lambda_ * grad

            k = iter + 1
            start = np.max(1, k - self._ls_nmsteps + 1)
            df0 = man.inner(x, grad, desc_dir)
            stepsize, newx = linesearch(objective, man, x, desc_dir, cost, df0)

            # XXX: What is alpha?
            # lambda_ = lambda_ * alpha

            newcost = objective(newx)
            newgrad = gradient(newx)
            newgradnorm = man.norm(newx, newgrad)

            # Barzilai-Borwein strategy
            # TODO: Memoize newcost.

            # Transport the old gradient to newx.
            grad_transp = man.transp(x, newx, grad)

            # Compute teh difference between gradients.
            Y = newx + newgrad - grad_transp

            # Compute the transported step.
            Stransp = x - lambda_ * grad_transp

            # Compute the new Barzilai-Borwein step.
            lambda_ = self._apply_strategy(man, newx, Stransp, Y, iter)

            # Update iterates.
            x = newx
            cost = newcost
            grad = newgrad
            gradnorm = newgradnorm

            iter += 1

        if self._logverbosity <= 0:
            return x
        else:
            self._stop_optlog(x, cost, stop_reason, time0,
                              stepsize=stepsize, gradnorm=gradnorm,
                              iter=iter)
            return x, self._optlog

    @staticmethod
    def _apply_direct_strategy(man, x, Stransp, Y, iter)
        num = man.norm(x, Stransp) ** 2
        den = man.inner(x, Stransp, Y)
        if den > 0
            lambda_ = np.min(
                self._lambdamax, np.max(self._lambdamin, num / den))
        else
            lambda_ = self._lambdamax
        return lambda_

    @staticmethod
    def _apply_inverse_strategy(man, x, Stransp, Y, iter):
        num = man.inner(x, Stransp, y)
        den = man.norm(x, Y) ** 2
        if num > 0
            lambda_ = np.min(
                self._lambdamax, np.max(self._lambdamin, num / den))
        else
            lambda_ = self._lambdamax
        return lambda_

    @staticmethod
    def _apply_alternate_strategy(man, x, Stransp, Y, iter):
        num = man.norm(x, Stransp) ** 2
        den = man.inner(x, Stransp, Y)
        den2 = man.norm(x, Y) ** 2
        if den > 0:
            if iter % 2 == 0:
                lambda_ = np.min(
                    self._lambdamax, np.max(self._lambdamin, num / den))
            else:
                lambda_ = np.min(
                    self._lambdamax, np.max(self._lambdamin, den / den2))
        else:
            lambda_ = self._lambdamax
        return lambda_
