"""Unit tests for ability estimation (EAP)."""

import pytest
import numpy as np

from app.irt.estimation import estimate_theta_eap, estimate_theta_mle


class TestEAPEstimation:
    """Tests for Expected A Posteriori theta estimation."""

    def test_no_responses_returns_prior(self):
        """With no responses, EAP should return the prior mean."""
        theta, se = estimate_theta_eap([], prior_mean=0.0, prior_sd=1.0)
        assert theta == pytest.approx(0.0, abs=0.01)
        assert se == pytest.approx(1.0, abs=0.05)

    def test_all_correct_shifts_theta_up(self):
        """All correct responses should push theta above 0."""
        responses = [(1.0, 0.0, True)] * 5
        theta, se = estimate_theta_eap(responses)
        assert theta > 0.5

    def test_all_incorrect_shifts_theta_down(self):
        """All incorrect responses should push theta below 0."""
        responses = [(1.0, 0.0, False)] * 5
        theta, se = estimate_theta_eap(responses)
        assert theta < -0.5

    def test_mixed_responses_near_zero(self):
        """50/50 responses on items at b=0 should estimate near 0."""
        responses = [(1.0, 0.0, True), (1.0, 0.0, False)] * 3
        theta, se = estimate_theta_eap(responses)
        assert abs(theta) < 0.5

    def test_se_decreases_with_more_items(self):
        """More items should reduce the posterior standard deviation."""
        responses_5 = [(1.0, 0.0, True), (1.0, 0.0, False)] * 2 + [(1.0, 0.0, True)]
        responses_10 = responses_5 * 2

        _, se_5 = estimate_theta_eap(responses_5)
        _, se_10 = estimate_theta_eap(responses_10)
        assert se_10 < se_5

    def test_high_ability_candidate(self):
        """Candidate answering hard items correctly should estimate high."""
        # Hard items (b = 1.5, 2.0, 2.5) answered correctly
        responses = [
            (1.0, 1.5, True),
            (1.0, 2.0, True),
            (1.0, 2.5, True),
            (1.0, 0.5, True),
            (1.0, 1.0, True),
        ]
        theta, se = estimate_theta_eap(responses)
        assert theta > 1.5

    def test_low_ability_candidate(self):
        """Candidate failing easy items should estimate low."""
        # Easy items (b = -1.5, -1.0, -0.5) answered incorrectly
        responses = [
            (1.0, -1.5, False),
            (1.0, -1.0, False),
            (1.0, -0.5, False),
            (1.0, 0.0, False),
            (1.0, 0.5, False),
        ]
        theta, se = estimate_theta_eap(responses)
        assert theta < -1.5

    def test_prior_influences_early_estimates(self):
        """A non-zero prior should shift early estimates."""
        responses = [(1.0, 0.0, True)]

        theta_prior_0, _ = estimate_theta_eap(responses, prior_mean=0.0)
        theta_prior_2, _ = estimate_theta_eap(responses, prior_mean=2.0)

        # With prior at 2.0, estimate should be higher
        assert theta_prior_2 > theta_prior_0

    def test_always_within_bounds(self):
        """EAP should always return values within the theta range."""
        # Extreme case: all correct on hard items
        responses = [(2.0, 3.0, True)] * 20
        theta, se = estimate_theta_eap(responses, theta_range=(-4.0, 4.0))
        assert -4.0 <= theta <= 4.0


class TestMLEEstimation:
    """Tests for Maximum Likelihood Estimation (reference implementation)."""

    def test_converges_for_mixed_pattern(self):
        """MLE should converge for a mixed response pattern."""
        responses = [
            (1.0, -1.0, True),
            (1.0, 0.0, True),
            (1.0, 0.5, False),
            (1.0, 1.0, False),
            (1.0, 1.5, False),
        ]
        theta, se = estimate_theta_mle(responses)
        # Should be near the difficulty where 50/50 transition happens
        assert -0.5 < theta < 1.0
        assert se > 0

    def test_all_correct_returns_upper_bound(self):
        """MLE with all correct should return upper bound (degenerate case)."""
        responses = [(1.0, 0.0, True)] * 5
        theta, se = estimate_theta_mle(responses, theta_bounds=(-4.0, 4.0))
        assert theta == pytest.approx(4.0)

    def test_all_incorrect_returns_lower_bound(self):
        """MLE with all incorrect should return lower bound."""
        responses = [(1.0, 0.0, False)] * 5
        theta, se = estimate_theta_mle(responses, theta_bounds=(-4.0, 4.0))
        assert theta == pytest.approx(-4.0)
