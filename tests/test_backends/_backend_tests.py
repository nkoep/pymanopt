import unittest

import numpy as np
from numpy import random as rnd, testing as np_testing


class TestUnaryFunction(unittest.TestCase):
    """Test cost function, gradient and Hessian for a simple unary function.
    """

    def setUp(self):
        self.n = 10
        self.cost = None

    def test_unary_function(self):
        cost = self.cost
        assert cost is not None
        n = self.n

        x = rnd.randn(n)

        # Test whether cost function accepts single argument.
        self.assertAlmostEqual(np.sum(x ** 2), cost(x))

        # Test whether gradient accepts single argument.
        egrad = cost.compute_gradient()
        np_testing.assert_allclose(2 * x, egrad(x))

        # Test the Hessian.
        u = rnd.randn(self.n)

        # Test whether Hessian accepts two regular arguments.
        ehess = cost.compute_hessian()
        # Test whether Hessian-vector product is correct.
        np_testing.assert_allclose(2 * u, ehess(x, u))


class TestNaryFunction(unittest.TestCase):
    """Test cost function, gradient and Hessian for cost functions accepting
    multiple arguments. This situation arises e.g. when optimizing over the
    FixedRankEmbedded manifold where points on the manifold are represented as
    a 3-tuple making up a truncated SVD.
    """

    def setUp(self):
        self.n = 10
        self.cost = None

    def test_nary_function(self):
        cost = self.cost
        assert cost is not None
        n = self.n

        x = rnd.randn(n)
        y = rnd.randn(n)

        # The argument signature of the cost function implies we are NOT on the
        # product manifold so solvers would call the wrapped cost function with
        # one argument, in this case a tuple of vectors.
        self.assertAlmostEqual(np.dot(x, y), cost((x, y)))

        egrad = cost.compute_gradient()
        g = egrad((x, y))
        # Since we treat the tuple (x, y) as one argument, we expect the result
        # of a call to the gradient function to be a tuple with two elements.
        self.assertIsInstance(g, (list, tuple))
        self.assertEqual(len(g), 2)
        for gi in g:
            self.assertIsInstance(gi, np.ndarray)
        g_x, g_y = g
        np_testing.assert_allclose(g_x, y)
        np_testing.assert_allclose(g_y, x)

        # Test the Hessian-vector product.
        u = rnd.randn(n)
        v = rnd.randn(n)

        ehess = cost.compute_hessian()
        h = ehess((x, y), (u, v))
        self.assertIsInstance(h, (list, tuple))
        self.assertEqual(len(h), 2)
        for hi in h:
            self.assertIsInstance(hi, np.ndarray)

        # Test whether the Hessian-vector product is correct.
        h_x, h_y = h
        np_testing.assert_allclose(h_x, v)
        np_testing.assert_allclose(h_y, u)


class TestNaryParameterGrouping(unittest.TestCase):
    """Test cost function, gradient and Hessian for a complex cost function one
    would define on product manifolds where one of the underlying manifolds
    represents points as a tuple of numpy.ndarrays.
    """

    def setUp(self):
        self.n = 10
        self.cost = None

    def test_nary_parameter_grouping(self):
        cost = self.cost
        assert cost is not None
        n = self.n

        x = rnd.randn(n)
        y = rnd.randn(n)
        z = rnd.randn(n)

        # The signature of the cost function now implies that we are on the
        # product manifold, so we mimic the behavior of solvers by calling the
        # cost function with a single argument: a tuple containing a tuple (x,
        # y) and a single vector z.
        self.assertAlmostEqual(np.sum(x ** 2 + y + z ** 3), cost(((x, y), z)))

        egrad = cost.compute_gradient()
        g = egrad(((x, y), z))

        # We defined the cost function signature to treat the first two
        # arguments as one parameter, so a call to the gradient must produce
        # two elements.
        self.assertIsInstance(g, (list, tuple))
        self.assertEqual(len(g), 2)
        g_xy, g_z = g
        self.assertIsInstance(g_xy, (list, tuple))
        self.assertEqual(len(g_xy), 2)
        self.assertIsInstance(g_z, np.ndarray)

        # Verify correctness of the gradient.
        np_testing.assert_allclose(g_xy[0], 2 * x)
        np_testing.assert_allclose(g_xy[1], 1)
        np_testing.assert_allclose(g_z, 3 * z ** 2)

        # Test the Hessian.
        u = rnd.randn(n)
        v = rnd.randn(n)
        w = rnd.randn(n)

        ehess = cost.compute_hessian()
        h = ehess(((x, y), z), ((u, v), w))

        # Test the type composition of the return value.
        self.assertIsInstance(h, (list, tuple))
        self.assertEqual(len(h), 2)
        h_xy, h_z = h
        self.assertIsInstance(h_xy, (list, tuple))
        self.assertEqual(len(h_xy), 2)
        self.assertIsInstance(h_z, np.ndarray)

        # Test whether the Hessian-vector product is correct.
        np_testing.assert_allclose(h_xy[0], 2 * u)
        np_testing.assert_allclose(h_xy[1], 0)
        np_testing.assert_allclose(h_z, 6 * z * w)


class TestVector(unittest.TestCase):
    def setUp(self):
        np.seterr(all='raise')

        n = self.n = 15

        Y = self.Y = rnd.randn(n)
        A = self.A = rnd.randn(n)

        # Calculate correct cost and grad...
        self.correct_cost = np.exp(np.sum(Y ** 2))
        self.correct_grad = 2 * Y * np.exp(np.sum(Y ** 2))

        # ... and hess
        # First form hessian matrix H
        # Convert Y and A into matrices (row vectors)
        Ymat = np.matrix(Y)
        Amat = np.matrix(A)

        diag = np.eye(n)

        H = np.exp(np.sum(Y ** 2)) * (4 * Ymat.T.dot(Ymat) + 2 * diag)

        # Then 'left multiply' H by A
        self.correct_hess = np.squeeze(np.array(Amat.dot(H)))

    def test_compile(self):
        np_testing.assert_allclose(self.correct_cost, self.cost(self.Y))

    def test_grad(self):
        grad = self.cost.compute_gradient()
        np_testing.assert_allclose(self.correct_grad, grad(self.Y))

    def test_hessian(self):
        hess = self.cost.compute_hessian()

        # Now test hess
        np_testing.assert_allclose(self.correct_hess, hess(self.Y, self.A))


class TestMatrix(unittest.TestCase):
    def setUp(self):
        np.seterr(all='raise')

        m = self.m = 10
        n = self.n = 15

        Y = self.Y = rnd.randn(m, n)
        A = self.A = rnd.randn(m, n)

        # Calculate correct cost and grad...
        self.correct_cost = np.exp(np.sum(Y ** 2))
        self.correct_grad = 2 * Y * np.exp(np.sum(Y ** 2))

        # ... and hess
        # First form hessian tensor H (4th order)
        Y1 = Y.reshape(m, n, 1, 1)
        Y2 = Y.reshape(1, 1, m, n)

        # Create an m x n x m x n array with diag[i,j,k,l] == 1 iff
        # (i == k and j == l), this is a 'diagonal' tensor.
        diag = np.eye(m * n).reshape(m, n, m, n)

        H = np.exp(np.sum(Y ** 2)) * (4 * Y1 * Y2 + 2 * diag)

        # Then 'right multiply' H by A
        Atensor = A.reshape(1, 1, m, n)

        self.correct_hess = np.sum(H * Atensor, axis=(2, 3))

    def test_compile(self):
        np_testing.assert_allclose(self.correct_cost, self.cost(self.Y))

    def test_grad(self):
        grad = self.cost.compute_gradient()
        np_testing.assert_allclose(self.correct_grad, grad(self.Y))

    def test_hessian(self):
        hess = self.cost.compute_hessian()

        # Now test hess
        np_testing.assert_allclose(self.correct_hess, hess(self.Y, self.A))


class TestTensor3(unittest.TestCase):
    def setUp(self):
        np.seterr(all='raise')

        n1 = self.n1 = 3
        n2 = self.n2 = 4
        n3 = self.n3 = 5

        Y = self.Y = rnd.randn(n1, n2, n3)
        A = self.A = rnd.randn(n1, n2, n3)

        # Calculate correct cost and grad...
        self.correct_cost = np.exp(np.sum(Y ** 2))
        self.correct_grad = 2 * Y * np.exp(np.sum(Y ** 2))

        # ... and hess
        # First form hessian tensor H (6th order)
        Y1 = Y.reshape(n1, n2, n3, 1, 1, 1)
        Y2 = Y.reshape(1, 1, 1, n1, n2, n3)

        # Create an n1 x n2 x n3 x n1 x n2 x n3 diagonal tensor
        diag = np.eye(n1 * n2 * n3).reshape(n1, n2, n3, n1, n2, n3)

        H = np.exp(np.sum(Y ** 2)) * (4 * Y1 * Y2 + 2 * diag)

        # Then 'right multiply' H by A
        Atensor = A.reshape(1, 1, 1, n1, n2, n3)

        self.correct_hess = np.sum(H * Atensor, axis=(3, 4, 5))

    def test_compile(self):
        np_testing.assert_allclose(self.correct_cost, self.cost(self.Y))

    def test_grad(self):
        grad = self.cost.compute_gradient()
        np_testing.assert_allclose(self.correct_grad, grad(self.Y))

    def test_hessian(self):
        hess = self.cost.compute_hessian()

        # Now test hess
        np_testing.assert_allclose(self.correct_hess, hess(self.Y, self.A))


class TestMixed(unittest.TestCase):
    # Test autograd on a tuple containing vector, matrix and tensor3.
    def setUp(self):
        np.seterr(all='raise')

        n1 = self.n1 = 3
        n2 = self.n2 = 4
        n3 = self.n3 = 5
        n4 = self.n4 = 6
        n5 = self.n5 = 7
        n6 = self.n6 = 8

        self.y = y = (rnd.randn(n1), rnd.randn(n2, n3), rnd.randn(n4, n5, n6))
        self.a = a = (rnd.randn(n1), rnd.randn(n2, n3), rnd.randn(n4, n5, n6))

        self.correct_cost = (np.exp(np.sum(y[0] ** 2)) +
                             np.exp(np.sum(y[1] ** 2)) +
                             np.exp(np.sum(y[2] ** 2)))

        # Calculate correct grad
        g1 = 2 * y[0] * np.exp(np.sum(y[0] ** 2))
        g2 = 2 * y[1] * np.exp(np.sum(y[1] ** 2))
        g3 = 2 * y[2] * np.exp(np.sum(y[2] ** 2))

        self.correct_grad = (g1, g2, g3)

        # Calculate correct hess
        # 1. Vector
        Ymat = np.matrix(y[0])
        Amat = np.matrix(a[0])

        diag = np.eye(n1)

        H = np.exp(np.sum(y[0] ** 2)) * (4 * Ymat.T.dot(Ymat) + 2 * diag)

        # Then 'left multiply' H by A
        h1 = np.array(Amat.dot(H)).flatten()

        # 2. MATRIX
        # First form hessian tensor H (4th order)
        Y1 = y[1].reshape(n2, n3, 1, 1)
        Y2 = y[1].reshape(1, 1, n2, n3)

        # Create an m x n x m x n array with diag[i,j,k,l] == 1 iff
        # (i == k and j == l), this is a 'diagonal' tensor.
        diag = np.eye(n2 * n3).reshape(n2, n3, n2, n3)

        H = np.exp(np.sum(y[1] ** 2)) * (4 * Y1 * Y2 + 2 * diag)

        # Then 'right multiply' H by A
        Atensor = a[1].reshape(1, 1, n2, n3)

        h2 = np.sum(H * Atensor, axis=(2, 3))

        # 3. Tensor3
        # First form hessian tensor H (6th order)
        Y1 = y[2].reshape(n4, n5, n6, 1, 1, 1)
        Y2 = y[2].reshape(1, 1, 1, n4, n5, n6)

        # Create an n1 x n2 x n3 x n1 x n2 x n3 diagonal tensor
        diag = np.eye(n4 * n5 * n6).reshape(n4, n5, n6, n4, n5, n6)

        H = np.exp(np.sum(y[2] ** 2)) * (4 * Y1 * Y2 + 2 * diag)

        # Then 'right multiply' H by A
        Atensor = a[2].reshape(1, 1, 1, n4, n5, n6)

        h3 = np.sum(H * Atensor, axis=(3, 4, 5))

        self.correct_hess = (h1, h2, h3)

    def test_compile(self):
        np_testing.assert_allclose(self.correct_cost, self.cost(self.y))

    def test_grad(self):
        grad = self.cost.compute_gradient()
        g = grad(self.y)
        for k in range(len(g)):
            np_testing.assert_allclose(self.correct_grad[k], g[k])

    def test_hessian(self):
        hess = self.cost.compute_hessian()

        # Now test hess
        h = hess(self.y, self.a)
        for k in range(len(h)):
            np_testing.assert_allclose(self.correct_hess[k], h[k])
