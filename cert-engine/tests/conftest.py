"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_items():
    """A small item bank for testing."""
    from app.services.item_selection import ItemCandidate

    return [
        ItemCandidate(
            item_id=f"item-{i:03d}",
            domain_id=(i % 8) + 1,
            discrimination=1.0 + (i % 5) * 0.2,
            difficulty=-2.0 + i * 0.2,
            sympson_hetter_k=1.0,
        )
        for i in range(40)
    ]


@pytest.fixture
def default_config():
    """Default session configuration for testing."""
    from app.services.cat_engine import SessionConfig

    return SessionConfig(
        theta_c=0.0,
        delta=0.2,
        alpha=0.05,
        beta=0.05,
        max_items=40,
        min_items=5,
        w_info=0.7,
        w_content=0.3,
        starting_theta=0.0,
        domain_weights={
            "1": 0.15, "2": 0.12, "3": 0.20, "4": 0.15,
            "5": 0.12, "6": 0.10, "7": 0.10, "8": 0.06,
        },
        max_exposure_rate=0.25,
        time_limit_minutes=120,
    )


@pytest.fixture
def default_domain_weights():
    """Blueprint domain weights."""
    return {
        "1": 0.15, "2": 0.12, "3": 0.20, "4": 0.15,
        "5": 0.12, "6": 0.10, "7": 0.10, "8": 0.06,
    }
