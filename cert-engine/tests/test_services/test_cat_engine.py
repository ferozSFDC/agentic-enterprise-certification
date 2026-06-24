"""Integration tests for the CAT engine orchestrator."""

import pytest
from app.services.cat_engine import (
    EngineState,
    SessionConfig,
    ItemCandidate,
    process_response,
    select_first_item,
)
from app.irt.sprt import Decision


class TestSelectFirstItem:
    """Tests for first item selection."""

    def test_selects_an_item(self, sample_items, default_config):
        state = EngineState.new_session(default_config)
        item = select_first_item(state, sample_items)
        assert item is not None
        assert item.item_id in [i.item_id for i in sample_items]

    def test_returns_none_for_empty_bank(self, default_config):
        state = EngineState.new_session(default_config)
        item = select_first_item(state, [])
        assert item is None


class TestProcessResponse:
    """Tests for the response processing pipeline."""

    def test_correct_response_increases_theta(self, sample_items, default_config):
        state = EngineState.new_session(default_config)
        item = sample_items[20]  # Middle difficulty item

        result = process_response(
            state=state,
            item=item,
            response_index=0,
            correct_index=0,  # Correct
            eligible_items=sample_items,
        )

        assert result.is_correct is True
        assert result.new_theta > default_config.starting_theta

    def test_incorrect_response_decreases_theta(self, sample_items, default_config):
        state = EngineState.new_session(default_config)
        item = sample_items[20]

        result = process_response(
            state=state,
            item=item,
            response_index=1,
            correct_index=0,  # Incorrect
            eligible_items=sample_items,
        )

        assert result.is_correct is False
        assert result.new_theta < default_config.starting_theta

    def test_tracks_domain_counts(self, sample_items, default_config):
        state = EngineState.new_session(default_config)
        item = sample_items[0]  # Domain 1

        process_response(
            state=state, item=item,
            response_index=0, correct_index=0,
            eligible_items=sample_items,
        )

        assert state.domain_counts[str(item.domain_id)] == 1

    def test_increments_items_administered(self, sample_items, default_config):
        state = EngineState.new_session(default_config)

        process_response(
            state=state, item=sample_items[0],
            response_index=0, correct_index=0,
            eligible_items=sample_items,
        )

        assert state.items_administered == 1

    def test_does_not_stop_below_minimum(self, sample_items, default_config):
        """Even if SPRT crosses boundary, don't stop below min_items."""
        state = EngineState.new_session(default_config)

        # One very informative correct response
        high_disc_item = ItemCandidate(
            item_id="high-disc",
            domain_id=1,
            discrimination=3.0,
            difficulty=0.0,
            sympson_hetter_k=1.0,
        )

        result = process_response(
            state=state, item=high_disc_item,
            response_index=0, correct_index=0,
            eligible_items=sample_items,
        )

        # Should continue even if LR moved a lot (only 1 item < min_items=5)
        assert result.stop_decision.should_stop is False

    def test_eventually_terminates_all_correct(self, sample_items, default_config):
        """All correct responses should eventually reach PASS."""
        state = EngineState.new_session(default_config)
        decision = None

        for i, item in enumerate(sample_items[:40]):
            remaining = [it for it in sample_items if it.item_id not in state.administered_item_ids]
            result = process_response(
                state=state, item=item,
                response_index=0, correct_index=0,
                eligible_items=remaining,
            )
            if result.stop_decision.should_stop:
                decision = result.decision
                break

        assert decision == Decision.PASS

    def test_eventually_terminates_all_incorrect(self, sample_items, default_config):
        """All incorrect responses should eventually reach FAIL."""
        state = EngineState.new_session(default_config)
        decision = None

        for i, item in enumerate(sample_items[:40]):
            remaining = [it for it in sample_items if it.item_id not in state.administered_item_ids]
            result = process_response(
                state=state, item=item,
                response_index=1, correct_index=0,
                eligible_items=remaining,
            )
            if result.stop_decision.should_stop:
                decision = result.decision
                break

        assert decision == Decision.FAIL

    def test_next_item_not_already_administered(self, sample_items, default_config):
        """Next item should never be one already seen."""
        state = EngineState.new_session(default_config)

        result = process_response(
            state=state, item=sample_items[0],
            response_index=0, correct_index=0,
            eligible_items=sample_items,
        )

        if result.next_item:
            assert result.next_item.item_id != sample_items[0].item_id
            assert result.next_item.item_id not in state.administered_item_ids
