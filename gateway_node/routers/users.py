from fastapi import APIRouter, HTTPException, Depends
import asyncpg
from core.database import get_db
from core.security import verify_password, hash_password
from auth.dependencies import get_current_user
from auth.models import TokenData, UpdateProfileRequest, ChangePasswordRequest

router = APIRouter()


@router.get("/me")
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """GET /user/me — Returns current user profile. Contract §4."""
    user = await conn.fetchrow(
        "SELECT id, email, full_name, avatar_url, role FROM users WHERE id = $1",
        current_user.id,
    )
    if not user:
        # Check admins table
        user = await conn.fetchrow(
            "SELECT id, email, full_name, avatar_url, 'admin' AS role FROM admins WHERE id = $1",
            current_user.id,
        )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user["id"]),
        "name": user["full_name"] or "User",
        "email": user["email"],
        "role": user["role"],
        "plan": "free",
        "searches_this_month": 0,  # TODO: query from usage table
        "searches_limit": 50,
    }


@router.patch("/me")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """PATCH /user/me — Update display name or avatar. Contract §4."""
    user = await conn.fetchrow(
        """
        UPDATE users
        SET
            full_name  = COALESCE($1, full_name),
            avatar_url = COALESCE($2, avatar_url)
        WHERE id = $3
        RETURNING id, email, full_name, avatar_url
        """,
        data.full_name, data.avatar_url, current_user.id,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "avatar_url": user["avatar_url"],
    }


@router.put("/password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """PUT /user/password — Change current user password. Contract §4."""
    user = await conn.fetchrow(
        "SELECT hashed_password FROM users WHERE id = $1", current_user.id
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.current_password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hashed = hash_password(data.new_password)
    await conn.execute(
        "UPDATE users SET hashed_password = $1 WHERE id = $2",
        new_hashed, current_user.id,
    )
    return {"message": "Password updated successfully"}


@router.get("/usage")
async def get_usage(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """GET /user/usage — Returns search quota info. Contract §4."""
    row = await conn.fetchrow(
        "SELECT searches_this_month, searches_limit, plan FROM user_usage WHERE user_id = $1",
        current_user.id,
    )
    if row:
        return {
            "searches_this_month": row["searches_this_month"],
            "searches_limit": row["searches_limit"],
            "plan": row["plan"],
        }
    # Graceful default if usage table not yet populated
    return {"searches_this_month": 0, "searches_limit": 50, "plan": "free"}


@router.delete("/history")
async def clear_history(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """DELETE /user/history — Clears search / chat history. Contract §4."""
    await conn.execute(
        "DELETE FROM chat_history WHERE user_id = $1", current_user.id
    )
    return {"message": "History cleared successfully"}


@router.get("/export")
async def export_data(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """GET /user/export — Export user data as JSON. Contract §4."""
    user = await conn.fetchrow(
        "SELECT id, email, full_name, avatar_url, created_at FROM users WHERE id = $1",
        current_user.id,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    history = await conn.fetch(
        "SELECT query, created_at FROM chat_history WHERE user_id = $1 ORDER BY created_at DESC",
        current_user.id,
    )

    return {
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "avatar_url": user["avatar_url"],
            "created_at": str(user["created_at"]),
        },
        "search_history": [
            {"query": r["query"], "created_at": str(r["created_at"])} for r in history
        ],
    }
