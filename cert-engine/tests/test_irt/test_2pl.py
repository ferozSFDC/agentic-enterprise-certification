"""Unit tests for 2PL IRT model functions."""

import math
import pytest
import numpy as np

from app.irt.models import (
    probability_2pl,
    probability_2pl_vector,
    fisher_information,
    fisher_information_vector,
    log_likelihood,
    total_test_information,
    standard_error,
)


class TestProbability2PL:
    """Tests for the 2PL probability function."""

    def test_at_difficulty_equals_fifty_percent(self):
        """When theta = b, probability should be 0.5 regardless of discrimination."""
        assert probability_2pl(theta=1.0, a=1.0, b=1.0) == pytest.approx(0.5)
        assert probability_2pl(theta=0.0, a=2.0, b=0.0) == pytest.approx(0.5)
        assert probability_2pl(theta=-1.5, a=0.5, b=-1.5) == pytest.approx(0.5)

    def test_above_difficulty_greater_than_fifty(self):
        """When theta > b, probability should exceed 0.5."""
        p = probability_2pl(theta=1.0, a=1.0, b=0.0)
        assert p > 0.5

    def test_below_difficulty_less_than_fifty(self):
        """When theta < b, probability should be below 0.5."""
        p = probability_2pl(theta=-1.0, a=1.0, b=0.0)
        assert p < 0.5

    def test_higher_discrimination_steeper_curve(self):
        """Higher a should make the curve steeper around b."""
        # At theta = b + 1 (one logit above difficulty)
        p_low_a = probability_2pl(theta=1.0, a=0.5, b=0.0)
        p_high_a = probability_2pl(theta=1.0, a=2.0, b=0.0)
        # Higher discrimination means more probability mass above difficulty
        assert p_high_a > p_low_a

    def test_output_range_zero_to_one(self):
        """Probability must always be in (0, 1)."""
        for theta in [-4.0, -2.0, 0.0, 2.0, 4.0]:
            for a in [0.2, 1.0, 3.0]:
                for b in [-3.0, 0.0, 3.0]:
                    p = probability_2pl(theta, a, b)
                    assert 0.0 < p < 1.0

    def test_extreme_theta_does_not_overflow(self):
        """Very large/small theta should not cause overflow."""
        p_high = probability_2pl(theta=100.0, a=3.0, b=0.0)
        p_low = probability_2pl(theta=-100.0, a=3.0, b=0.0)
        assert p_high == pytest.approx(1.0, abs=1e-6)
        assert p_low == pytest.approx(0.0, abs=1e-6)

    def test_vector_matches_scalar(self):
        """Vectorized version should match scalar for each element."""
        thetas = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        a, b = 1.5, 0.5
        vector_result = probability_2pl_vector(thetas, a, b)
        scalar_results = [probability_2pl(t, a, b) for t in thetas]
        np.testing.assert_allclose(vector_result, scalar_results, atol=1e-10)


class TestFisherInformation:
    """Tests for Fisher Information."""

    def test_maximum_at_theta_equals_b(self):
        """Fisher Information is maximized when theta = b."""
        a, b = 1.5, 0.0
        info_at_b = fisher_information(0.0, a, b)
        info_away = fisher_information(2.0, a, b)
        assert info_at_b > info_away

    def test_maximum_value_formula(self):
        """At theta = b: I = a^2 * 0.5 * 0.5 = a^2 / 4."""
        a, b = 2.0, 1.0
        expected = (a ** 2) / 4.0
        actual = fisher_information(1.0, a, b)
        assert actual == pytest.approx(expected)

    def test_scales_with_discrimination_squared(self):
        """Information scales with a^2."""
        info_a1 = fisher_information(0.0, 1.0, 0.0)
        info_a2 = fisher_information(0.0, 2.0, 0.0)
        assert info_a2 == pytest.approx(4.0 * info_a1)

    def test_always_non_negative(self):
        """Fisher Information is always >= 0."""
        for theta in np.linspace(-4, 4, 20):
            assert fisher_information(theta, 1.0, 0.0) >= 0

    def test_vector_matches_scalar(self):
        """Vectorized version should match scalar computation."""
        theta = 0.5
        a_vals = np.array([0.5, 1.0, 1.5, 2.0])
        b_vals = np.array([-1.0, 0.0, 0.5, 1.0])
        vector_result = fisher_information_vector(theta, a_vals, b_vals)
        scalar_results = [fisher_information(theta, a, b) for a, b in zip(a_vals, b_vals)]
        np.testing.assert_allclose(vector_result, scalar_results, atol=1e-10)


class TestLogLikelihood:
    """Tests for log-likelihood computation."""

    def test_all_correct_at_high_theta(self):
        """All-correct pattern should have high LL at high theta."""
        responses = [(1.0, 0.0, True), (1.0, 0.0, True), (1.0, 0.0, True)]
        ll_high = log_likelihood(3.0, responses)
        ll_low = log_likelihood(-3.0, responses)
        assert ll_high > ll_low

    def test_all_incorrect_at_low_theta(self):
        """All-incorrect pattern should have higher LL at low theta."""
        responses = [(1.0, 0.0, False), (1.0, 0.0, False), (1.0, 0.0, False)]
        ll_low = log_likelihood(-3.0, responses)
        ll_high = log_likelihood(3.0, responses)
        assert ll_low > ll_high

    def test_always_negative(self):
        """Log-likelihood should always be negative (log of probabilities < 1)."""
        responses = [(1.0, 0.0, True), (1.0, 1.0, False)]
        for theta in np.linspace(-4, 4, 10):
            assert log_likelihood(theta, responses) < 0


class TestTestInformation:
    """Tests for total test information."""

    def test_additive(self):
        """Test information is sum of item informations."""
        items = [(1.0, 0.0), (1.5, 0.5), (0.8, -0.5)]
        theta = 0.0
        total = total_test_information(theta, items)
        manual_sum = sum(fisher_information(theta, a, b) for a, b in items)
        assert total == pytest.approx(manual_sum)

    def test_standard_error_decreases_with_more_items(self):
        """More items = more information = smaller SE."""
        items_5 = [(1.0, i * 0.5) for i in range(5)]
        items_10 = [(1.0, i * 0.5) for i in range(10)]
        se_5 = standard_error(0.0, items_5)
        se_10 = standard_error(0.0, items_10)
        assert se_10 < se_5
