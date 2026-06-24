"""
Sequential Probability Ratio Test (SPRT) for pass/fail classification.

The SPRT accumulates evidence for or against the hypothesis that a candidate's
ability is above the cut score (theta_c). It decides PASS, FAIL, or CONTINUE
after each item response.

Two composite hypotheses:
    H_pass: theta = theta_c + delta  (candidate is above the cut)
    H_fail: theta = theta_c - delta  (candidate is below the cut)

The indifference region [theta_c - delta, theta_c + delta] prevents the test
from oscillating indefinitely for candidates exactly at the cut score.
"""

import math
from dataclasses import dataclass
from enum import Enum

from app.irt.models import probability_2pl


class Decision(str, Enum):
    CONTINUE = "continue"
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class SPRTResult:
    """Result of an SPRT update step."""
    cumulative_lr: float
    decision: Decision
    upper_boundary: float
    lower_boundary: float


def compute_wald_boundaries(alpha: float, beta: float) -> tuple[float, float]:
    """
    Compute Wald's sequential boundaries for SPRT.

    Args:
        alpha: Type I error rate (P(pass | true fail)) - passing someone who should fail
        beta: Type II error rate (P(fail | true pass)) - failing someone who should pass

    Returns:
        (upper_boundary_A, lower_boundary_B) on log-likelihood ratio scale

    Note:
        Upper boundary A = log((1 - beta) / alpha)  → cross this to PASS
        Lower boundary B = log(beta / (1 - alpha))  → cross this to FAIL
        B is negative, A is positive (assuming alpha, beta < 0.5)
    """
    upper_a = math.log((1.0 - beta) / alpha)
    lower_b = math.log(beta / (1.0 - alpha))
    return upper_a, lower_b


def sprt_log_likelihood_increment(
    a: float,
    b: float,
    is_correct: bool,
    theta_c: float,
    delta: float,
) -> float:
    """
    Compute the log-likelihood ratio increment for a single item response.

    LR_j = log(P(u_j | H_pass) / P(u_j | H_fail))

    Where:
        P(u_j=1 | H_pass) = P(correct | theta_c + delta, a, b)
        P(u_j=1 | H_fail) = P(correct | theta_c - delta, a, b)

    Args:
        a: Item discrimination
        b: Item difficulty
        is_correct: Whether the candidate answered correctly
        theta_c: Cut score
        delta: Indifference region half-width

    Returns:
        Log-likelihood ratio increment (positive favors PASS, negative favors FAIL)
    """
    p_pass = probability_2pl(theta_c + delta, a, b)
    p_fail = probability_2pl(theta_c - delta, a, b)

    if is_correct:
        # Favor PASS if P(correct | above cut) > P(correct | below cut)
        numerator = max(p_pass, 1e-10)
        denominator = max(p_fail, 1e-10)
    else:
        # Favor FAIL if P(incorrect | below cut) > P(incorrect | above cut)
        numerator = max(1.0 - p_pass, 1e-10)
        denominator = max(1.0 - p_fail, 1e-10)

    return math.log(numerator / denominator)


def sprt_update(
    cumulative_lr: float,
    a: float,
    b: float,
    is_correct: bool,
    theta_c: float,
    delta: float,
    alpha: float,
    beta: float,
) -> SPRTResult:
    """
    Update SPRT state after one item response.

    Computes the new cumulative log-likelihood ratio and checks
    whether it has crossed either Wald boundary.

    Args:
        cumulative_lr: Current cumulative log-likelihood ratio (before this response)
        a: Item discrimination
        b: Item difficulty
        is_correct: Whether the candidate answered correctly
        theta_c: Cut score on the logit (theta) scale
        delta: Indifference region half-width (typically 0.1-0.3)
        alpha: Type I error rate (incorrectly PASSING a fail candidate)
        beta: Type II error rate (incorrectly FAILING a pass candidate)

    Returns:
        SPRTResult with updated LR, decision, and boundary values
    """
    # Compute increment
    increment = sprt_log_likelihood_increment(a, b, is_correct, theta_c, delta)
    new_lr = cumulative_lr + increment

    # Wald boundaries
    upper_a, lower_b = compute_wald_boundaries(alpha, beta)

    # Classification check
    if new_lr >= upper_a:
        decision = Decision.PASS
    elif new_lr <= lower_b:
        decision = Decision.FAIL
    else:
        decision = Decision.CONTINUE

    return SPRTResult(
        cumulative_lr=new_lr,
        decision=decision,
        upper_boundary=upper_a,
        lower_boundary=lower_b,
    )


def forced_decision(
    current_theta: float,
    theta_c: float,
    cumulative_lr: float,
) -> Decision:
    """
    Make a forced decision when the item ceiling is reached.

    When max_items are administered and SPRT hasn't crossed a boundary,
    classify based on the current theta estimate relative to cut score.
    The cumulative LR is used as a tiebreaker when theta ≈ theta_c.

    Args:
        current_theta: EAP estimate of candidate ability
        theta_c: Cut score
        cumulative_lr: Final cumulative LR (indicates direction of evidence)

    Returns:
        Decision.PASS or Decision.FAIL
    """
    if current_theta > theta_c:
        return Decision.PASS
    elif current_theta < theta_c:
        return Decision.FAIL
    else:
        # Exact tie (extremely rare) — use LR direction
        return Decision.PASS if cumulative_lr >= 0 else Decision.FAIL


def confidence_from_lr(cumulative_lr: float, alpha: float, beta: float) -> float:
    """
    Convert cumulative LR to a confidence measure in [0, 1].

    Maps the LR position relative to the Wald boundaries to a
    normalized confidence value. At the boundary, confidence = 1 - error_rate.
    Between boundaries, confidence < threshold.

    Args:
        cumulative_lr: Final cumulative LR
        alpha: Type I error rate
        beta: Type II error rate

    Returns:
        Confidence value in (0, 1) — higher means more confident in the decision
    """
    upper_a, lower_b = compute_wald_boundaries(alpha, beta)

    if cumulative_lr >= upper_a:
        # PASS decision — confidence based on how far past boundary
        # At boundary: confidence = 1 - alpha
        # Beyond: approaches 1.0
        ratio = cumulative_lr / upper_a
        return min(1.0 - alpha * (1.0 / max(ratio, 1.0)), 0.999)
    elif cumulative_lr <= lower_b:
        # FAIL decision — confidence based on how far past boundary
        ratio = cumulative_lr / lower_b
        return min(1.0 - beta * (1.0 / max(ratio, 1.0)), 0.999)
    else:
        # Forced decision (between boundaries) — lower confidence
        # Map LR position to [0.5, threshold]
        total_span = upper_a - lower_b
        position = (cumulative_lr - lower_b) / total_span  # 0 to 1
        # Closer to a boundary = more confident
        distance_to_nearest = min(
            abs(cumulative_lr - upper_a),
            abs(cumulative_lr - lower_b),
        )
        max_distance = total_span / 2.0
        return 0.5 + 0.3 * (1.0 - distance_to_nearest / max_distance)
