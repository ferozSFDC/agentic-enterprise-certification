"""
Exam session lifecycle endpoints.

POST /api/v1/exam/start       — Begin a new exam, receive first item
POST /api/v1/exam/{id}/respond — Submit response, receive next item or decision
GET  /api/v1/exam/{id}/status  — Check session state (for reconnection)
POST /api/v1/exam/{id}/abandon — Mark session abandoned
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Item, ExamSession, ItemResponse, Candidate, ExamConfig
from app.schemas.exam import (
    ExamStartRequest,
    ExamStartResponse,
    ExamRespondRequest,
    ExamRespondResponse,
    ExamStatusResponse,
    ItemPresentation,
)
from app.services.cat_engine import (
    EngineState,
    SessionConfig,
    ResponseRecord,
    ItemCandidate,
    process_response,
    select_first_item,
)

router = APIRouter(prefix="/api/v1/exam", tags=["exam"])


async def _get_active_config(db: AsyncSession) -> ExamConfig:
    """Get the currently active exam configuration."""
    result = await db.execute(
        select(ExamConfig).where(ExamConfig.is_active == True)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(
            status_code=503,
            detail="No active exam configuration. Contact administrator.",
        )
    return config


async def _get_eligible_items(db: AsyncSession) -> list[ItemCandidate]:
    """Load all active items as ItemCandidate objects for the selection algorithm."""
    result = await db.execute(
        select(Item).where(Item.status == "active")
    )
    items = result.scalars().all()
    return [
        ItemCandidate(
            item_id=str(item.id),
            domain_id=item.domain_id,
            discrimination=item.discrimination,
            difficulty=item.difficulty,
            sympson_hetter_k=item.sympson_hetter_k,
        )
        for item in items
    ]


def _item_to_presentation(item: Item, sequence: int) -> ItemPresentation:
    """Convert DB item to candidate-facing presentation (no answers)."""
    options = [opt["text"] for opt in item.options]
    return ItemPresentation(
        id=item.id,
        scenario=item.scenario,
        stem=item.stem,
        options=options,
        sequence=sequence,
    )


@router.post("/start", response_model=ExamStartResponse)
async def start_exam(
    request: ExamStartRequest,
    candidate_id: uuid.UUID,  # TODO: extract from JWT
    db: AsyncSession = Depends(get_db),
):
    """
    Begin a new exam session.

    Creates the session, selects the first item, and returns it.
    The candidate must not have an in-progress session.
    """
    # Check no existing in-progress session
    existing = await db.execute(
        select(ExamSession).where(
            ExamSession.candidate_id == candidate_id,
            ExamSession.status == "in_progress",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="An exam session is already in progress for this candidate.",
        )

    # Load config
    config = await _get_active_config(db)
    session_config = SessionConfig.from_snapshot(config.to_snapshot())

    # Override starting theta if candidate has a prior
    starting_theta = session_config.starting_theta
    if request.prior_theta is not None:
        starting_theta = request.prior_theta

    # Create engine state
    engine_state = EngineState.new_session(session_config)
    engine_state.current_theta = starting_theta

    # Select first item
    eligible = await _get_eligible_items(db)
    if not eligible:
        raise HTTPException(
            status_code=503, detail="No active items in the item bank."
        )

    first_item_candidate = select_first_item(engine_state, eligible)
    if not first_item_candidate:
        raise HTTPException(
            status_code=503, detail="Item selection failed."
        )

    # Load the full item from DB for presentation
    first_item_db = await db.get(Item, uuid.UUID(first_item_candidate.item_id))

    # Create session record
    session = ExamSession(
        candidate_id=candidate_id,
        status="in_progress",
        current_theta=starting_theta,
        theta_se=1.0,
        items_administered=0,
        cumulative_lr=0.0,
        domain_counts={},
        config_snapshot=config.to_snapshot(),
        time_limit_minutes=config.time_limit_minutes,
    )
    db.add(session)
    await db.flush()  # Get the session ID

    return ExamStartResponse(
        session_id=session.id,
        item=_item_to_presentation(first_item_db, sequence=1),
        time_limit_minutes=config.time_limit_minutes,
        max_items=config.max_items,
    )


@router.post("/{session_id}/respond", response_model=ExamRespondResponse)
async def respond_to_item(
    session_id: uuid.UUID,
    request: ExamRespondRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a response to the current item.

    Scores the response, updates ability estimate, checks SPRT,
    and either returns the next item or the final decision.
    """
    # Load session with responses
    result = await db.execute(
        select(ExamSession)
        .where(ExamSession.id == session_id)
        .options(selectinload(ExamSession.responses))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is not in progress.")

    # Load the item being responded to
    item_db = await db.get(Item, request.item_id)
    if not item_db:
        raise HTTPException(status_code=404, detail="Item not found.")

    # Rebuild engine state from session
    config = SessionConfig.from_snapshot(session.config_snapshot)
    responses = [
        ResponseRecord(
            item_id=str(r.item_id),
            domain_id=0,  # We don't need this for re-estimation
            discrimination=0.0,  # Will be populated from actual response tuples
            difficulty=0.0,
            is_correct=r.is_correct,
        )
        for r in session.responses
    ]

    # Build proper response tuples for EAP re-estimation
    # We need the actual item parameters for each past response
    administered_ids = {str(r.item_id) for r in session.responses}
    administered_ids.add(str(request.item_id))

    # Create item candidate for the current item
    current_item = ItemCandidate(
        item_id=str(item_db.id),
        domain_id=item_db.domain_id,
        discrimination=item_db.discrimination,
        difficulty=item_db.difficulty,
        sympson_hetter_k=item_db.sympson_hetter_k,
    )

    # Build engine state
    engine_state = EngineState(
        config=config,
        responses=[],  # Will be rebuilt from DB responses
        current_theta=session.current_theta,
        theta_se=session.theta_se,
        cumulative_lr=session.cumulative_lr,
        domain_counts=dict(session.domain_counts),
        items_administered=session.items_administered,
        administered_item_ids=administered_ids,
    )

    # Rebuild response history with actual parameters
    for r in session.responses:
        resp_item = await db.get(Item, r.item_id)
        if resp_item:
            engine_state.responses.append(ResponseRecord(
                item_id=str(resp_item.id),
                domain_id=resp_item.domain_id,
                discrimination=resp_item.discrimination,
                difficulty=resp_item.difficulty,
                is_correct=r.is_correct,
            ))

    # Get eligible items for next selection
    eligible = await _get_eligible_items(db)
    eligible = [i for i in eligible if i.item_id not in administered_ids]

    # Process the response
    proc_result = process_response(
        state=engine_state,
        item=current_item,
        response_index=request.response,
        correct_index=item_db.correct_index,
        eligible_items=eligible,
    )

    # Record the response
    response_record = ItemResponse(
        session_id=session_id,
        item_id=request.item_id,
        sequence_number=session.items_administered + 1,
        response=request.response,
        is_correct=proc_result.is_correct,
        theta_after=proc_result.new_theta,
        se_after=proc_result.new_se,
        lr_after=proc_result.new_cumulative_lr,
        presented_at=request.presented_at,
        responded_at=request.responded_at,
        response_time_ms=int(
            (request.responded_at - request.presented_at).total_seconds() * 1000
        ),
    )
    db.add(response_record)

    # Update session state
    session.current_theta = proc_result.new_theta
    session.theta_se = proc_result.new_se
    session.cumulative_lr = proc_result.new_cumulative_lr
    session.items_administered += 1
    session.domain_counts = engine_state.domain_counts

    # Update item statistics
    item_db.admin_count += 1
    if proc_result.is_correct:
        item_db.correct_count += 1
    item_db.exposure_count += 1

    # Check if exam is over
    if proc_result.stop_decision.should_stop:
        decision = proc_result.decision.value.upper()
        session.status = f"completed_{decision.lower()}"
        session.decision = decision
        session.decision_confidence = proc_result.confidence
        session.completed_at = datetime.now(timezone.utc)

        return ExamRespondResponse(
            status="completed",
            items_administered=session.items_administered,
            decision=decision,
            confidence=proc_result.confidence,
            reason=proc_result.stop_decision.reason,
        )

    # Exam continues — return next item
    if not proc_result.next_item:
        raise HTTPException(
            status_code=503, detail="No eligible items remaining."
        )

    next_item_db = await db.get(Item, uuid.UUID(proc_result.next_item.item_id))
    return ExamRespondResponse(
        status="continue",
        items_administered=session.items_administered,
        next_item=_item_to_presentation(
            next_item_db, sequence=session.items_administered + 1
        ),
    )


@router.get("/{session_id}/status", response_model=ExamStatusResponse)
async def get_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current session state (for reconnection after disconnect)."""
    session = await db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds() / 60.0

    return ExamStatusResponse(
        session_id=session.id,
        status=session.status,
        items_administered=session.items_administered,
        elapsed_minutes=elapsed,
        time_limit_minutes=session.time_limit_minutes,
        current_sequence=session.items_administered + 1,
        decision=session.decision,
        confidence=session.decision_confidence,
    )


@router.post("/{session_id}/abandon")
async def abandon_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a session as abandoned (timeout, quit, browser close)."""
    session = await db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is not in progress.")

    session.status = "abandoned"
    session.completed_at = datetime.now(timezone.utc)

    return {"status": "abandoned", "items_administered": session.items_administered}
