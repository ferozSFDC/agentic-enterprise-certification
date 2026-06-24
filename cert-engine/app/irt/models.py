"""
2-Parameter Logistic (2PL) IRT model functions.

The 2PL model defines the probability of a correct response as:
    P(X=1 | theta, a, b) = 1 / (1 + exp(-a * (theta - b)))

Where:
    theta = candidate ability (logit scale, typically -4 to +4)
    a = item discrimination (how sharply the item separates candidates; typically 0.2 to 3.0)
    b = item difficulty (the theta value where P(correct) = 0.5; typically -4 to +4)
"""

import math
import numpy as np
from numpy.typing import NDArray


def probability_2pl(theta: float, a: float, b: float) -> float:
    """
    Probability of correct response under the 2PL model.

    Args:
        theta: Candidate ability estimate
        a: Item discrimination parameter
        b: Item difficulty parameter

    Returns:
        P(correct | theta, a, b) in range (0, 1)
    """
    exponent = a * (theta - b)
    # Clamp to prevent overflow
    exponent = max(-30.0, min(30.0, exponent))
    return 1.0 / (1.0 + math.exp(-exponent))


def probability_2pl_vector(
    thetas: NDArray[np.float64], a: float, b: float
) -> NDArray[np.float64]:
    """
    Vectorized probability computation across multiple theta values.
    Used for EAP quadrature.

    Args:
        thetas: Array of theta values (quadrature points)
        a: Item discrimination
        b: Item difficulty

    Returns:
        Array of P(correct) at each theta
    """
    exponents = a * (thetas - b)
    exponents = np.clip(exponents, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-exponents))


def fisher_information(theta: float, a: float, b: float) -> float:
    """
    Fisher Information of a 2PL item at a given theta.

    I(theta) = a^2 * P(theta) * Q(theta)

    Maximum information occurs at theta = b (where P = Q = 0.5).
    Higher discrimination (a) means more information.

    Args:
        theta: Point at which to evaluate information
        a: Item discrimination
        b: Item difficulty

    Returns:
        Fisher Information value (always >= 0)
    """
    p = probability_2pl(theta, a, b)
    q = 1.0 - p
    return (a ** 2) * p * q


def fisher_information_vector(
    theta: float, a_values: NDArray[np.float64], b_values: NDArray[np.float64]
) -> NDArray[np.float64]:
    """
    Compute Fisher Information for multiple items at a single theta.

    Args:
        theta: Candidate ability estimate
        a_values: Array of discrimination values
        b_values: Array of difficulty values

    Returns:
        Array of Fisher Information values
    """
    exponents = a_values * (theta - b_values)
    exponents = np.clip(exponents, -30.0, 30.0)
    p = 1.0 / (1.0 + np.exp(-exponents))
    q = 1.0 - p
    return (a_values ** 2) * p * q


def log_likelihood(
    theta: float,
    responses: list[tuple[float, float, bool]],
) -> float:
    """
    Log-likelihood of a response pattern given theta.

    Args:
        theta: Candidate ability
        responses: List of (a, b, is_correct) tuples

    Returns:
        Log-likelihood value
    """
    ll = 0.0
    for a, b, correct in responses:
        p = probability_2pl(theta, a, b)
        if correct:
            ll += math.log(max(p, 1e-10))
        else:
            ll += math.log(max(1.0 - p, 1e-10))
    return ll


def total_test_information(
    theta: float,
    items: list[tuple[float, float]],
) -> float:
    """
    Total test information at theta (sum of item informations).

    Args:
        theta: Point at which to evaluate
        items: List of (a, b) tuples for administered items

    Returns:
        Sum of Fisher Information across all items
    """
    return sum(fisher_information(theta, a, b) for a, b in items)


def standard_error(theta: float, items: list[tuple[float, float]]) -> float:
    """
    Standard Error of theta estimate = 1 / sqrt(test_information).

    Args:
        theta: Current ability estimate
        items: List of (a, b) tuples for administered items

    Returns:
        SE value (smaller = more precise)
    """
    info = total_test_information(theta, items)
    if info <= 0:
        return 10.0  # Very uncertain
    return 1.0 / math.sqrt(info)
