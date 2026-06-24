"""
Item selection algorithm: Weighted Maximum Information with Content Balancing.

Selects the next item to administer by combining:
1. Fisher Information at current theta (psychometric efficiency)
2. Domain deficit relative to blueprint weights (content coverage)
3. Sympson-Hetter exposure control (item security)
"""

import random
import numpy as np
from dataclasses import dataclass

from app.irt.models import fisher_information_vector


@dataclass
class ItemCandidate:
    """An eligible item with its selection metadata."""
    item_id: str
    domain_id: int
    discrimination: float
    difficulty: float
    sympson_hetter_k: float


def compute_domain_deficit(
    domain_id: int,
    domain_counts: dict[str, int],
    total_administered: int,
    domain_weights: dict[str, float],
) -> float:
    """
    Compute how under-represented a domain is relative to blueprint target.

    Positive = under-represented (should select from this domain)
    Negative = over-represented (should avoid this domain)
    Zero = perfectly on target

    Args:
        domain_id: The domain of the candidate item
        domain_counts: Current count of items administered per domain
        total_administered: Total items administered so far
        domain_weights: Blueprint target weights per domain

    Returns:
        Deficit value (higher = more needed from this domain)
    """
    domain_key = str(domain_id)
    target_weight = domain_weights.get(domain_key, 0.0)

    if total_administered == 0:
        # First item — all domains equally needed, weighted by target
        return target_weight

    current_count = domain_counts.get(domain_key, 0)
    current_proportion = current_count / total_administered
    deficit = target_weight - current_proportion

    return deficit


def select_next_item(
    eligible_items: list[ItemCandidate],
    theta_hat: float,
    domain_counts: dict[str, int],
    total_administered: int,
    domain_weights: dict[str, float],
    w_info: float = 0.7,
    w_content: float = 0.3,
    max_exposure_rate: float = 0.25,
) -> ItemCandidate | None:
    """
    Select the next item using weighted maximum information + content balance.

    Algorithm:
    1. Compute Fisher Information for each eligible item at current theta
    2. Compute domain deficit for each item's domain
    3. Apply exposure control gate (Sympson-Hetter)
    4. Compute composite score = w_info * norm_info + w_content * norm_deficit
    5. Return the item with highest composite score

    Early-exam boost: For the first 8 items, w_content is boosted to 0.5
    to ensure broad domain sampling before information maximization takes over.

    Args:
        eligible_items: Items that haven't been administered, aren't retired, etc.
        theta_hat: Current ability estimate
        domain_counts: Items administered per domain so far
        total_administered: Total items administered
        domain_weights: Blueprint target proportions per domain
        w_info: Weight for information component
        w_content: Weight for content balance component
        max_exposure_rate: Not used directly here (Sympson-Hetter k is per-item)

    Returns:
        Selected ItemCandidate, or None if no eligible items pass exposure gate
    """
    if not eligible_items:
        return None

    # Early-exam boost: first 8 items prioritize domain coverage
    if total_administered < 8:
        w_content = max(w_content, 0.5)
        w_info = 1.0 - w_content

    # Vectorize item parameters
    a_values = np.array([item.discrimination for item in eligible_items])
    b_values = np.array([item.difficulty for item in eligible_items])

    # 1. Fisher Information at current theta
    info_scores = fisher_information_vector(theta_hat, a_values, b_values)
    max_info = info_scores.max()
    if max_info > 0:
        info_normalized = info_scores / max_info
    else:
        info_normalized = np.zeros_like(info_scores)

    # 2. Domain deficit scores
    deficit_scores = np.array([
        compute_domain_deficit(
            item.domain_id, domain_counts, total_administered, domain_weights
        )
        for item in eligible_items
    ])
    # Normalize deficits to [0, 1]
    deficit_min = deficit_scores.min()
    deficit_max = deficit_scores.max()
    deficit_range = deficit_max - deficit_min
    if deficit_range > 0:
        deficit_normalized = (deficit_scores - deficit_min) / deficit_range
    else:
        deficit_normalized = np.ones_like(deficit_scores) * 0.5

    # 3. Composite score
    composite = w_info * info_normalized + w_content * deficit_normalized

    # 4. Exposure control gate (Sympson-Hetter)
    # For each item, draw a random number; if > k, exclude the item
    for i, item in enumerate(eligible_items):
        if random.random() > item.sympson_hetter_k:
            composite[i] = -float("inf")  # Excluded

    # 5. Select highest composite score
    best_idx = int(np.argmax(composite))

    # Check if all items were gated out
    if composite[best_idx] == -float("inf"):
        # Fallback: select any random item ignoring exposure control
        # This ensures the exam can always continue
        best_idx = random.randint(0, len(eligible_items) - 1)

    return eligible_items[best_idx]
