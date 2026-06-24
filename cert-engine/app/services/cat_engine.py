"""
Core CAT Engine orchestrator.

Manages the exam session lifecycle:
1. Start session → select first item
2. Receive response → score → estimate theta → update SPRT → check stop → select next
3. Terminate → record decision

This module ties together IRT estimation, SPRT classification,
item selection, and session state management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.irt.estimation import estimate_theta_eap
from app.irt.sprt import sprt_update, Decision, confidence_from_lr
from app.services.item_selection import ItemCandidate, select_next_item
from app.services.stopping_rule import evaluate_stopping_with_theta_c, StopDecision


@dataclass
class SessionConfig:
    """Frozen exam configuration for a session."""
    theta_c: float
    delta: float
    alpha: float
    beta: float
    max_items: int
    min_items: int
    w_info: float
    w_content: float
    starting_theta: float
    domain_weights: dict[str, float]
    max_exposure_rate: float
    time_limit_minutes: int

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "SessionConfig":
        return cls(
            theta_c=snapshot["theta_c"],
            delta=snapshot["delta"],
            alpha=snapshot["alpha"],
            beta=snapshot["beta"],
            max_items=snapshot["max_items"],
            min_items=snapshot["min_items"],
            w_info=snapshot["w_info"],
            w_content=snapshot["w_content"],
            starting_theta=snapshot["starting_theta"],
            domain_weights=snapshot["domain_weights"],
            max_exposure_rate=snapshot["max_exposure_rate"],
            time_limit_minutes=snapshot["time_limit_minutes"],
        )


@dataclass
class ResponseRecord:
    """A scored response in the session history."""
    item_id: str
    domain_id: int
    discrimination: float
    difficulty: float
    is_correct: bool


@dataclass
class EngineState:
    """Running state of the CAT engine for a session."""
    config: SessionConfig
    responses: list[ResponseRecord]
    current_theta: float
    theta_se: float
    cumulative_lr: float
    domain_counts: dict[str, int]
    items_administered: int
    administered_item_ids: set[str]

    @classmethod
    def new_session(cls, config: SessionConfig) -> "EngineState":
        return cls(
            config=config,
            responses=[],
            current_theta=config.starting_theta,
            theta_se=1.0,
            cumulative_lr=0.0,
            domain_counts={},
            items_administered=0,
            administered_item_ids=set(),
        )


@dataclass
class SelectionResult:
    """Result of the item selection step."""
    item: ItemCandidate | None
    stop_decision: StopDecision | None


@dataclass
class ProcessResponseResult:
    """Result of processing a candidate's response."""
    is_correct: bool
    new_theta: float
    new_se: float
    new_cumulative_lr: float
    stop_decision: StopDecision
    next_item: ItemCandidate | None  # None if exam is over
    decision: Decision | None  # None if continuing
    confidence: float | None  # None if continuing


def process_response(
    state: EngineState,
    item: ItemCandidate,
    response_index: int,
    correct_index: int,
    eligible_items: list[ItemCandidate],
) -> ProcessResponseResult:
    """
    Process a candidate's response and advance the CAT.

    Steps:
    1. Score the response
    2. Update response history
    3. Re-estimate theta (EAP)
    4. Update SPRT cumulative LR
    5. Check stopping rule
    6. If continuing, select next item

    Args:
        state: Current engine state (mutated in place)
        item: The item that was administered
        response_index: The option index the candidate selected (0-based)
        correct_index: The correct option index
        eligible_items: Pool of items available for next selection

    Returns:
        ProcessResponseResult with all updated values and next step
    """
    # 1. Score
    is_correct = response_index == correct_index

    # 2. Update history
    record = ResponseRecord(
        item_id=item.item_id,
        domain_id=item.domain_id,
        discrimination=item.discrimination,
        difficulty=item.difficulty,
        is_correct=is_correct,
    )
    state.responses.append(record)
    state.administered_item_ids.add(item.item_id)
    state.items_administered += 1

    # Update domain counts
    domain_key = str(item.domain_id)
    state.domain_counts[domain_key] = state.domain_counts.get(domain_key, 0) + 1

    # 3. Re-estimate theta (EAP)
    response_tuples = [
        (r.discrimination, r.difficulty, r.is_correct)
        for r in state.responses
    ]
    new_theta, new_se = estimate_theta_eap(response_tuples)
    state.current_theta = new_theta
    state.theta_se = new_se

    # 4. Update SPRT
    sprt_result = sprt_update(
        cumulative_lr=state.cumulative_lr,
        a=item.discrimination,
        b=item.difficulty,
        is_correct=is_correct,
        theta_c=state.config.theta_c,
        delta=state.config.delta,
        alpha=state.config.alpha,
        beta=state.config.beta,
    )
    state.cumulative_lr = sprt_result.cumulative_lr

    # 5. Check stopping rule
    stop_decision = evaluate_stopping_with_theta_c(
        sprt_result=sprt_result,
        items_administered=state.items_administered,
        current_theta=state.current_theta,
        max_items=state.config.max_items,
        min_items=state.config.min_items,
        theta_c=state.config.theta_c,
        alpha=state.config.alpha,
        beta=state.config.beta,
    )

    # 6. Select next item (only if continuing)
    next_item = None
    if not stop_decision.should_stop:
        # Filter out already-administered items
        remaining = [
            i for i in eligible_items
            if i.item_id not in state.administered_item_ids
        ]
        next_item = select_next_item(
            eligible_items=remaining,
            theta_hat=state.current_theta,
            domain_counts=state.domain_counts,
            total_administered=state.items_administered,
            domain_weights=state.config.domain_weights,
            w_info=state.config.w_info,
            w_content=state.config.w_content,
            max_exposure_rate=state.config.max_exposure_rate,
        )

    return ProcessResponseResult(
        is_correct=is_correct,
        new_theta=new_theta,
        new_se=new_se,
        new_cumulative_lr=sprt_result.cumulative_lr,
        stop_decision=stop_decision,
        next_item=next_item,
        decision=stop_decision.decision,
        confidence=stop_decision.confidence,
    )


def select_first_item(
    state: EngineState,
    eligible_items: list[ItemCandidate],
) -> ItemCandidate | None:
    """
    Select the first item for a new session.

    Uses maximum information at starting theta with full content balance weight
    since all domains have equal deficit at the start.

    Args:
        state: Fresh engine state (no responses yet)
        eligible_items: All active items in the bank

    Returns:
        Selected first item, or None if no items available
    """
    return select_next_item(
        eligible_items=eligible_items,
        theta_hat=state.current_theta,
        domain_counts=state.domain_counts,
        total_administered=0,
        domain_weights=state.config.domain_weights,
        w_info=state.config.w_info,
        w_content=state.config.w_content,
        max_exposure_rate=state.config.max_exposure_rate,
    )
