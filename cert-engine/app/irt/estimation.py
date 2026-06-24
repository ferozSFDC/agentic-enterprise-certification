"""
Ability (theta) estimation using Expected A Posteriori (EAP).

EAP uses Gaussian quadrature with a normal prior to compute
the posterior mean of theta given a response pattern. Unlike MLE,
EAP is always well-defined (even with 0 or all correct responses)
because the prior regularizes the estimate.
"""

import numpy as np
from scipy.stats import norm
from numpy.typing import NDArray

from app.irt.models import probability_2pl_vector


def estimate_theta_eap(
    responses: list[tuple[float, float, bool]],
    prior_mean: float = 0.0,
    prior_sd: float = 1.0,
    n_quadrature: int = 49,
    theta_range: tuple[float, float] = (-4.0, 4.0),
) -> tuple[float, float]:
    """
    Estimate theta using Expected A Posteriori (EAP) with normal prior.

    Uses Gaussian quadrature: evaluate posterior at discrete points,
    compute weighted mean and SD.

    Args:
        responses: List of (discrimination, difficulty, is_correct) tuples
        prior_mean: Mean of the normal prior on theta
        prior_sd: SD of the normal prior on theta
        n_quadrature: Number of quadrature points (odd number for symmetry)
        theta_range: Range of theta values to evaluate

    Returns:
        (theta_hat, posterior_sd) - posterior mean and standard deviation
    """
    if not responses:
        return prior_mean, prior_sd

    # Quadrature points evenly spaced across range
    thetas = np.linspace(theta_range[0], theta_range[1], n_quadrature)

    # Prior weights (normal PDF at each quadrature point)
    prior_weights = norm.pdf(thetas, loc=prior_mean, scale=prior_sd)

    # Log-likelihood at each quadrature point
    log_likelihoods = np.zeros(n_quadrature)

    for a, b, correct in responses:
        p = probability_2pl_vector(thetas, a, b)
        if correct:
            log_likelihoods += np.log(np.maximum(p, 1e-10))
        else:
            log_likelihoods += np.log(np.maximum(1.0 - p, 1e-10))

    # Log-posterior (unnormalized)
    log_posterior = log_likelihoods + np.log(np.maximum(prior_weights, 1e-10))

    # Numerical stability: subtract max before exponentiating
    log_posterior -= np.max(log_posterior)
    posterior = np.exp(log_posterior)

    # Normalize to get proper posterior distribution
    total = np.sum(posterior)
    if total <= 0:
        # Degenerate case — fall back to prior
        return prior_mean, prior_sd

    posterior /= total

    # EAP: posterior mean
    theta_hat = float(np.sum(thetas * posterior))

    # Posterior SD
    variance = float(np.sum((thetas - theta_hat) ** 2 * posterior))
    posterior_sd = float(np.sqrt(max(variance, 1e-10)))

    return theta_hat, posterior_sd


def estimate_theta_mle(
    responses: list[tuple[float, float, bool]],
    initial_theta: float = 0.0,
    max_iterations: int = 50,
    convergence: float = 0.001,
    theta_bounds: tuple[float, float] = (-4.0, 4.0),
) -> tuple[float, float]:
    """
    Maximum Likelihood Estimation of theta via Newton-Raphson.

    WARNING: MLE is undefined when all responses are correct or all incorrect.
    Use EAP as the primary estimator. MLE is provided for reference/comparison.

    Args:
        responses: List of (discrimination, difficulty, is_correct) tuples
        initial_theta: Starting value for iteration
        max_iterations: Maximum Newton-Raphson iterations
        convergence: Stop when |delta_theta| < this
        theta_bounds: Hard bounds on theta estimate

    Returns:
        (theta_hat, se) - MLE estimate and standard error
        Returns (initial_theta, 10.0) if estimation fails
    """
    from app.irt.models import probability_2pl, fisher_information

    if not responses:
        return initial_theta, 10.0

    # Check for all-correct or all-incorrect (MLE undefined)
    all_correct = all(correct for _, _, correct in responses)
    all_incorrect = all(not correct for _, _, correct in responses)
    if all_correct:
        return theta_bounds[1], 0.5
    if all_incorrect:
        return theta_bounds[0], 0.5

    theta = initial_theta

    for _ in range(max_iterations):
        # First derivative of log-likelihood
        d1 = 0.0
        # Second derivative (negative = information)
        d2 = 0.0

        for a, b, correct in responses:
            p = probability_2pl(theta, a, b)
            q = 1.0 - p
            u = 1.0 if correct else 0.0

            d1 += a * (u - p)
            d2 -= (a ** 2) * p * q

        if abs(d2) < 1e-10:
            break

        # Newton-Raphson update
        delta = d1 / d2
        theta -= delta

        # Enforce bounds
        theta = max(theta_bounds[0], min(theta_bounds[1], theta))

        if abs(delta) < convergence:
            break

    # Standard error from information
    info = sum(fisher_information(theta, a, b) for a, b, _ in responses)
    se = 1.0 / max(np.sqrt(info), 0.01) if info > 0 else 10.0

    return theta, float(se)
