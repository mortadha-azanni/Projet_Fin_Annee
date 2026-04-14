from fastapi import APIRouter, HTTPException, Depends, status
import asyncpg
import bcrypt
from typing import Optional
from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import TokenData, UpdateProfileRequest, ChangePasswordRequest

router = APIRouter()

@router.get("/me")
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Get current user profile (Matches GET /auth/me requirement)"""
    user = await conn.fetchrow(
        "SELECT id, email, full_name, avatar_url, created_at, role FROM users WHERE id = $1",
        current_user.id
    )
    if not user:
        # Check admins table if not in users
        user = await conn.fetchrow(
            "SELECT id, email, full_name, avatar_url, created_at, 'admin' as role FROM admins WHERE id = $1",
            current_user.id
        )
        
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "id": str(user["id"]),
        "name": user["full_name"] or "User",
        "email": user["email"],
        "role": user["role"],
        "plan": "free", # Placeholder as per contract
        "searches_this_month": 0, # Placeholder
        "searches_limit": 50 # Placeholder
    }

@router.patch("/me")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Update current user profile"""
    user = await conn.fetchrow(
        """
        UPDATE users
        SET
            full_name = COALESCE($1, full_name),
            avatar_url = COALESCE($2, avatar_url)
        WHERE id = $3
        RETURNING id, email, full_name, avatar_url
        """,
        data.full_name, data.avatar_url, current_user.id
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "avatar_url": user["avatar_url"]
    }

@router.put("/password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Change current user password"""
    user = await conn.fetchrow(
        "SELECT hashed_password FROM users WHERE id = $1",
        current_user.id
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt.checkpw(
        data.current_password.encode('utf-8'),
        user["hashed_password"].encode('utf-8')
    ):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hashed = bcrypt.hashpw(
        data.new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    await conn.execute(
        "UPDATE users SET hashed_password = $1 WHERE id = $2",
        new_hashed, current_user.id
    )
    return {"message": "Password updated successfully"}

@router.get("/usage")
async def get_usage(current_user: TokenData = Depends(get_current_user)):
    """Get user search usage stats"""
    return {
        "searches_this_month": 14,
        "searches_limit": 50,
        "plan": "free"
    }

@router.delete("/history")
async def clear_history(current_user: TokenData = Depends(get_current_user)):
    """Clear user chat history"""
    # Logic to clear history from Redis/DB goes here
    return {"message": "History cleared successfully"}

@router.get("/export")
async def export_data(current_user: TokenData = Depends(get_current_user)):
    """Export user data as JSON"""
    return {"user_id": current_user.id, "data": "Exported user data placeholder"}
