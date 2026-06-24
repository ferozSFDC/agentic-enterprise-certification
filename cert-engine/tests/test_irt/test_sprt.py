"""Unit tests for SPRT classification logic."""

import math
import pytest

from app.irt.sprt import (
    compute_wald_boundaries,
    sprt_log_likelihood_increment,
    sprt_update,
    forced_decision,
    confidence_from_lr,
    Decision,
    SPRTResult,
)


class TestWaldBoundaries:
    """Tests for Wald boundary computation."""

    def test_default_boundaries(self):
        """Standard alpha=0.05, beta=0.05 should give symmetric boundaries."""
        upper, lower = compute_wald_boundaries(alpha=0.05, beta=0.05)
        # A = log(0.95 / 0.05) = log(19) ≈ 2.944
        assert upper == pytest.approx(math.log(19), abs=0.01)
        # B = log(0.05 / 0.95) = log(1/19) ≈ -2.944
        assert lower == pytest.approx(-math.log(19), abs=0.01)
        # Should be symmetric
        assert upper == pytest.approx(-lower, abs=0.01)

    def test_upper_is_positive_lower_is_negative(self):
        """Upper boundary should be positive, lower should be negative."""
        upper, lower = compute_wald_boundaries(alpha=0.05, beta=0.05)
        assert upper > 0
        assert lower < 0

    def test_tighter_error_rates_wider_boundaries(self):
        """Smaller alpha/beta should produce wider boundaries (harder to cross)."""
        upper_loose, lower_loose = compute_wald_boundaries(0.10, 0.10)
        upper_tight, lower_tight = compute_wald_boundaries(0.01, 0.01)
        assert upper_tight > upper_loose
        assert lower_tight < lower_loose


class TestSPRTLogLikelihoodIncrement:
    """Tests for the per-item LR increment."""

    def test_correct_response_above_cut_positive_increment(self):
        """Correct on an item where P(pass) > P(fail) should favor PASS."""
        # Item at difficulty = theta_c (0.0), so P_pass > P_fail when delta > 0
        increment = sprt_log_likelihood_increment(
            a=1.0, b=0.0, is_correct=True, theta_c=0.0, delta=0.2
        )
        assert increment > 0  # Favors PASS

    def test_incorrect_response_below_cut_negative_increment(self):
        """Incorrect response should favor FAIL."""
        increment = sprt_log_likelihood_increment(
            a=1.0, b=0.0, is_correct=False, theta_c=0.0, delta=0.2
        )
        assert increment < 0  # Favors FAIL

    def test_increment_magnitude_depends_on_discrimination(self):
        """Higher discrimination items should produce larger increments."""
        inc_low_a = abs(sprt_log_likelihood_increment(
            a=0.5, b=0.0, is_correct=True, theta_c=0.0, delta=0.2
        ))
        inc_high_a = abs(sprt_log_likelihood_increment(
            a=2.0, b=0.0, is_correct=True, theta_c=0.0, delta=0.2
        ))
        assert inc_high_a > inc_low_a


class TestSPRTUpdate:
    """Tests for the full SPRT update step."""

    def test_starts_at_continue(self):
        """First response should almost never cross a boundary."""
        result = sprt_update(
            cumulative_lr=0.0,
            a=1.0, b=0.0,
            is_correct=True,
            theta_c=0.0, delta=0.2,
            alpha=0.05, beta=0.05,
        )
        # Single item rarely crosses boundary (need ~3 logits)
        assert result.decision == Decision.CONTINUE

    def test_accumulates_to_pass(self):
        """Many correct responses should eventually cross upper boundary."""
        lr = 0.0
        for _ in range(30):
            result = sprt_update(lr, 1.0, 0.0, True, 0.0, 0.2, 0.05, 0.05)
            lr = result.cumulative_lr
            if result.decision == Decision.PASS:
                break
        assert result.decision == Decision.PASS

    def test_accumulates_to_fail(self):
        """Many incorrect responses should eventually cross lower boundary."""
        lr = 0.0
        for _ in range(30):
            result = sprt_update(lr, 1.0, 0.0, False, 0.0, 0.2, 0.05, 0.05)
            lr = result.cumulative_lr
            if result.decision == Decision.FAIL:
                break
        assert result.decision == Decision.FAIL

    def test_mixed_responses_stays_continue(self):
        """Alternating correct/incorrect should stay undecided."""
        lr = 0.0
        for i in range(10):
            is_correct = i % 2 == 0
            result = sprt_update(lr, 1.0, 0.0, is_correct, 0.0, 0.2, 0.05, 0.05)
            lr = result.cumulative_lr
        assert result.decision == Decision.CONTINUE

    def test_boundaries_in_result(self):
        """Result should include the computed boundaries."""
        result = sprt_update(0.0, 1.0, 0.0, True, 0.0, 0.2, 0.05, 0.05)
        assert result.upper_boundary > 0
        assert result.lower_boundary < 0


class TestForcedDecision:
    """Tests for forced decision at item ceiling."""

    def test_theta_above_cut_passes(self):
        """Theta above cut score should produce PASS."""
        decision = forced_decision(current_theta=0.5, theta_c=0.0, cumulative_lr=0.5)
        assert decision == Decision.PASS

    def test_theta_below_cut_fails(self):
        """Theta below cut score should produce FAIL."""
        decision = forced_decision(current_theta=-0.5, theta_c=0.0, cumulative_lr=-0.3)
        assert decision == Decision.FAIL

    def test_theta_at_cut_uses_lr_direction(self):
        """Exact tie uses LR direction."""
        assert forced_decision(0.0, 0.0, 0.1) == Decision.PASS
        assert forced_decision(0.0, 0.0, -0.1) == Decision.FAIL


class TestConfidence:
    """Tests for confidence computation."""

    def test_at_boundary_returns_high_confidence(self):
        """At exactly the boundary, confidence should be near 1 - error_rate."""
        upper, _ = compute_wald_boundaries(0.05, 0.05)
        confidence = confidence_from_lr(upper, 0.05, 0.05)
        assert confidence >= 0.9

    def test_between_boundaries_lower_confidence(self):
        """Between boundaries (forced decision), confidence should be lower."""
        confidence = confidence_from_lr(0.0, 0.05, 0.05)
        assert confidence < 0.9
        assert confidence >= 0.5

    def test_beyond_boundary_high_confidence(self):
        """Well beyond boundary should approach near-1.0."""
        upper, _ = compute_wald_boundaries(0.05, 0.05)
        confidence = confidence_from_lr(upper * 2, 0.05, 0.05)
        assert confidence > 0.95
