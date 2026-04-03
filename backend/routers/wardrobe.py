"""
Wardrobe management API endpoints.
"""

import json
import os
import uuid
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import Optional
from database import get_connection
from models.schemas import WardrobeItemCreate, WardrobeItemResponse, WardrobeStats

router = APIRouter(prefix="/api/wardrobe", tags=["Wardrobe"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _parse_tags(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []
    try:
        val = json.loads(text)
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
    except Exception:
        pass
    return [p.strip() for p in text.split(",") if p.strip()]


def _row_to_response(row) -> WardrobeItemResponse:
    return WardrobeItemResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        category=row["category"],
        color=row["color"],
        pattern=row["pattern"],
        fabric=row["fabric"],
        fit_type=row["fit_type"],
        formality=row["formality"],
        style_tags=_parse_tags(row["style_tags"]),
        occasion_tags=_parse_tags(row["occasion_tags"]),
        active_flag=bool(row["active_flag"]),
        image_path=row["image_path"],
        usage_count=row["usage_count"],
        last_used=row["last_used"],
        last_worn_at=row["last_worn_at"],
        created_at=row["created_at"],
    )


@router.post("/{user_id}", response_model=WardrobeItemResponse)
async def add_wardrobe_item(
    user_id: int,
    category: str = Form(...),
    color: str = Form(...),
    formality: str = Form(...),
    name: Optional[str] = Form(None),
    pattern: Optional[str] = Form("Solid"),
    fabric: Optional[str] = Form(None),
    fit_type: Optional[str] = Form("Regular"),
    style_tags: Optional[str] = Form(None),
    occasion_tags: Optional[str] = Form(None),
    active_flag: Optional[bool] = Form(True),
    image: Optional[UploadFile] = File(None),
):
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(await image.read())
        image_path = f"/uploads/{filename}"

    cursor.execute(
        """
        INSERT INTO wardrobe_items (
            user_id, name, category, color, pattern, fabric, fit_type, formality,
            style_tags, occasion_tags, active_flag, image_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            name,
            category.title(),
            color.title(),
            pattern or "Solid",
            fabric,
            fit_type or "Regular",
            formality,
            json.dumps(_parse_tags(style_tags)),
            json.dumps(_parse_tags(occasion_tags)),
            1 if (active_flag is None or active_flag) else 0,
            image_path,
        ),
    )
    item_id = cursor.lastrowid
    conn.commit()
    row = cursor.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return _row_to_response(row)


@router.get("/{user_id}", response_model=list[WardrobeItemResponse])
async def list_wardrobe(user_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM wardrobe_items WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [_row_to_response(r) for r in rows]


@router.get("/{user_id}/stats", response_model=WardrobeStats)
async def wardrobe_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    all_items = cursor.execute(
        "SELECT * FROM wardrobe_items WHERE user_id = ? ORDER BY usage_count DESC",
        (user_id,),
    ).fetchall()
    if not all_items:
        conn.close()
        return WardrobeStats(total_items=0, most_used=[], least_used=[], category_breakdown={})
    most_used = [_row_to_response(r) for r in all_items[:3]]
    least_used = [_row_to_response(r) for r in all_items[-3:]]
    category_breakdown = {}
    for item in all_items:
        category_breakdown[item["category"]] = category_breakdown.get(item["category"], 0) + 1
    conn.close()
    return WardrobeStats(
        total_items=len(all_items),
        most_used=most_used,
        least_used=least_used,
        category_breakdown=category_breakdown,
    )


@router.put("/item/{item_id}", response_model=WardrobeItemResponse)
async def update_item(item_id: int, item: WardrobeItemCreate):
    conn = get_connection()
    cursor = conn.cursor()
    existing = cursor.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found.")

    cursor.execute(
        """
        UPDATE wardrobe_items
        SET name = ?, category = ?, color = ?, pattern = ?, fabric = ?, fit_type = ?,
            formality = ?, style_tags = ?, occasion_tags = ?, active_flag = ?
        WHERE id = ?
        """,
        (
            item.name,
            item.category.title(),
            item.color.title(),
            item.pattern or "Solid",
            item.fabric,
            item.fit_type or "Regular",
            item.formality,
            json.dumps(item.style_tags or []),
            json.dumps(item.occasion_tags or []),
            1 if (item.active_flag is None or item.active_flag) else 0,
            item_id,
        ),
    )
    conn.commit()
    row = cursor.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return _row_to_response(row)


@router.delete("/item/{item_id}")
async def delete_item(item_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    existing = cursor.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found.")

    if existing["image_path"]:
        filepath = os.path.join(os.path.dirname(__file__), "..", existing["image_path"].lstrip("/"))
        if os.path.exists(filepath):
            os.remove(filepath)

    cursor.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"message": "Item deleted successfully."}
