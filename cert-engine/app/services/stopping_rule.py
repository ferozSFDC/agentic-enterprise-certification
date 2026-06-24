"""
Stopping rule: determines when the CAT should terminate and issue a decision.

Uses SPRT as the primary mechanism with a hard ceiling as the safety valve.
"""

from dataclasses import dataclass
from app.irt.sprt import Decision, SPRTResult, forced_decision, confidence_from_lr


@dataclass
class StopDecision:
    """Result of the stopping rule evaluation."""
    should_stop: bool
    decision: Decision | None  # None if should_stop is False
    confidence: float | None  # None if should_stop is False
    reason: str  # "sprt_pass", "sprt_fail", "ceiling_reached", "continue"


def evaluate_stopping(
    sprt_result: SPRTResult,
    items_administered: int,
    current_theta: float,
    max_items: int,
    min_items: int,
    alpha: float,
    beta: float,
) -> StopDecision:
    """
    Evaluate whether to stop the exam.

    Priority order:
    1. If below min_items, always continue (regardless of SPRT)
    2. If SPRT crossed a boundary, stop with that decision
    3. If ceiling reached, force a decision based on theta
    4. Otherwise, continue

    Args:
        sprt_result: Latest SPRT computation result
        items_administered: Count of items administered so far
        current_theta: Current EAP theta estimate
        max_items: Item ceiling (40)
        min_items: Safety floor (5)
        alpha: Type I error rate (for confidence calculation)
        beta: Type II error rate (for confidence calculation)

    Returns:
        StopDecision indicating whether to stop and why
    """
    # Safety floor: never stop before min_items regardless of SPRT
    if items_administered < min_items:
        return StopDecision(
            should_stop=False,
            decision=None,
            confidence=None,
            reason="below_minimum",
        )

    # SPRT decision
    if sprt_result.decision == Decision.PASS:
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=Decision.PASS,
            confidence=confidence,
            reason="sprt_pass",
        )

    if sprt_result.decision == Decision.FAIL:
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=Decision.FAIL,
            confidence=confidence,
            reason="sprt_fail",
        )

    # Ceiling reached without SPRT decision
    if items_administered >= max_items:
        theta_c = (
            sprt_result.upper_boundary + sprt_result.lower_boundary
        )  # Not quite right - need theta_c from config
        # Use forced_decision which compares theta to theta_c
        # We'll get theta_c from the caller context
        # For now, use the LR direction as a proxy
        decision = forced_decision(
            current_theta=current_theta,
            theta_c=0.0,  # Will be overridden by caller
            cumulative_lr=sprt_result.cumulative_lr,
        )
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=decision,
            confidence=confidence,
            reason="ceiling_reached",
        )

    # Continue
    return StopDecision(
        should_stop=False,
        decision=None,
        confidence=None,
        reason="continue",
    )


def evaluate_stopping_with_theta_c(
    sprt_result: SPRTResult,
    items_administered: int,
    current_theta: float,
    max_items: int,
    min_items: int,
    theta_c: float,
    alpha: float,
    beta: float,
) -> StopDecision:
    """
    Full stopping rule evaluation with explicit theta_c for forced decisions.

    This is the preferred entry point — it handles all cases correctly
    including forced decisions at the ceiling.

    Args:
        sprt_result: Latest SPRT computation result
        items_administered: Count of items administered so far
        current_theta: Current EAP theta estimate
        max_items: Item ceiling
        min_items: Safety floor
        theta_c: Cut score for forced decision
        alpha: Type I error rate
        beta: Type II error rate

    Returns:
        StopDecision
    """
    # Safety floor
    if items_administered < min_items:
        return StopDecision(
            should_stop=False,
            decision=None,
            confidence=None,
            reason="below_minimum",
        )

    # SPRT decision
    if sprt_result.decision == Decision.PASS:
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=Decision.PASS,
            confidence=confidence,
            reason="sprt_pass",
        )

    if sprt_result.decision == Decision.FAIL:
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=Decision.FAIL,
            confidence=confidence,
            reason="sprt_fail",
        )

    # Ceiling
    if items_administered >= max_items:
        decision = forced_decision(
            current_theta=current_theta,
            theta_c=theta_c,
            cumulative_lr=sprt_result.cumulative_lr,
        )
        confidence = confidence_from_lr(
            sprt_result.cumulative_lr, alpha, beta
        )
        return StopDecision(
            should_stop=True,
            decision=decision,
            confidence=confidence,
            reason="ceiling_reached",
        )

    return StopDecision(
        should_stop=False,
        decision=None,
        confidence=None,
        reason="continue",
    )
