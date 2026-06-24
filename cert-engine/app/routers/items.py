"""
Item bank management endpoints (admin only).

GET    /api/v1/admin/items         — List items with filters
POST   /api/v1/admin/items         — Create single item
PUT    /api/v1/admin/items/{id}    — Update item
PATCH  /api/v1/admin/items/{id}/status — Change lifecycle status
POST   /api/v1/admin/items/import  — Bulk import from JSON
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Item
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemStatusUpdate,
    ItemResponse,
    ItemImportRequest,
    ItemImportResponse,
)

router = APIRouter(prefix="/api/v1/admin/items", tags=["items"])


@router.get("/", response_model=list[ItemResponse])
async def list_items(
    domain_id: int | None = None,
    status: str | None = None,
    cc_level: int | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List items with optional filters."""
    query = select(Item)

    if domain_id is not None:
        query = query.where(Item.domain_id == domain_id)
    if status is not None:
        query = query.where(Item.status == status)
    if cc_level is not None:
        query = query.where(Item.cc_level == cc_level)

    query = query.order_by(Item.domain_id, Item.objective_id).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        ItemResponse(
            id=item.id,
            domain_id=item.domain_id,
            objective_id=item.objective_id,
            cc_level=item.cc_level,
            discrimination=item.discrimination,
            difficulty=item.difficulty,
            scenario=item.scenario,
            stem=item.stem,
            options=[{"text": o["text"], "rationale": o.get("rationale", "")} for o in item.options],
            correct_index=item.correct_index,
            status=item.status,
            exposure_count=item.exposure_count,
            admin_count=item.admin_count,
            correct_count=item.correct_count,
            sympson_hetter_k=item.sympson_hetter_k,
            p_value=item.p_value,
            author=item.author,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(
    request: ItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a single item."""
    item = Item(
        domain_id=request.domain_id,
        objective_id=request.objective_id,
        cc_level=request.cc_level,
        discrimination=request.discrimination,
        difficulty=request.difficulty,
        scenario=request.scenario,
        stem=request.stem,
        options=[{"text": o.text, "rationale": o.rationale} for o in request.options],
        correct_index=request.correct_index,
        status=request.status,
        author=request.author,
    )
    db.add(item)
    await db.flush()

    return ItemResponse(
        id=item.id,
        domain_id=item.domain_id,
        objective_id=item.objective_id,
        cc_level=item.cc_level,
        discrimination=item.discrimination,
        difficulty=item.difficulty,
        scenario=item.scenario,
        stem=item.stem,
        options=[{"text": o["text"], "rationale": o.get("rationale", "")} for o in item.options],
        correct_index=item.correct_index,
        status=item.status,
        exposure_count=item.exposure_count,
        admin_count=item.admin_count,
        correct_count=item.correct_count,
        sympson_hetter_k=item.sympson_hetter_k,
        p_value=item.p_value,
        author=item.author,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    request: ItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing item's content or parameters."""
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    update_data = request.model_dump(exclude_unset=True)
    if "options" in update_data:
        update_data["options"] = [
            {"text": o.text, "rationale": o.rationale} for o in request.options
        ]

    for field, value in update_data.items():
        setattr(item, field, value)

    item.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return ItemResponse(
        id=item.id,
        domain_id=item.domain_id,
        objective_id=item.objective_id,
        cc_level=item.cc_level,
        discrimination=item.discrimination,
        difficulty=item.difficulty,
        scenario=item.scenario,
        stem=item.stem,
        options=[{"text": o["text"], "rationale": o.get("rationale", "")} for o in item.options],
        correct_index=item.correct_index,
        status=item.status,
        exposure_count=item.exposure_count,
        admin_count=item.admin_count,
        correct_count=item.correct_count,
        sympson_hetter_k=item.sympson_hetter_k,
        p_value=item.p_value,
        author=item.author,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.patch("/{item_id}/status")
async def update_item_status(
    item_id: uuid.UUID,
    request: ItemStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Change item lifecycle status (activate, retire, flag)."""
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    item.status = request.status
    item.updated_at = datetime.now(timezone.utc)

    if request.status == "retired":
        item.retired_at = datetime.now(timezone.utc)

    return {"id": str(item.id), "status": item.status}


@router.post("/import", response_model=ItemImportResponse)
async def import_items(
    request: ItemImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk import items from a JSON payload."""
    imported = 0
    errors = []

    for i, item_data in enumerate(request.items):
        try:
            item = Item(
                domain_id=item_data.domain_id,
                objective_id=item_data.objective_id,
                cc_level=item_data.cc_level,
                discrimination=item_data.discrimination,
                difficulty=item_data.difficulty,
                scenario=item_data.scenario,
                stem=item_data.stem,
                options=[
                    {"text": o.text, "rationale": o.rationale}
                    for o in item_data.options
                ],
                correct_index=item_data.correct_index,
                status=item_data.status,
                author=item_data.author,
            )
            db.add(item)
            imported += 1
        except Exception as e:
            errors.append(f"Item {i}: {str(e)}")

    if imported > 0:
        await db.flush()

    return ItemImportResponse(imported=imported, errors=errors)


@router.get("/stats/summary")
async def item_stats_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate item bank statistics."""
    total = await db.execute(select(func.count(Item.id)))
    active = await db.execute(
        select(func.count(Item.id)).where(Item.status == "active")
    )
    pretest = await db.execute(
        select(func.count(Item.id)).where(Item.status == "pretest")
    )
    retired = await db.execute(
        select(func.count(Item.id)).where(Item.status == "retired")
    )

    # Domain distribution
    domain_counts = await db.execute(
        select(Item.domain_id, func.count(Item.id))
        .where(Item.status == "active")
        .group_by(Item.domain_id)
    )

    return {
        "total": total.scalar_one(),
        "active": active.scalar_one(),
        "pretest": pretest.scalar_one(),
        "retired": retired.scalar_one(),
        "by_domain": {
            str(row[0]): row[1] for row in domain_counts.all()
        },
    }
