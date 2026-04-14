from fastapi import APIRouter, HTTPException, Depends, status
import asyncpg
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user
from .models import RegisterRequest, LoginRequest, AuthResponse, TokenData

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Register a new user."""
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", data.email
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(data.password)
    user = await conn.fetchrow(
        "INSERT INTO users (email, hashed_password) VALUES ($1, $2) RETURNING id",
        data.email, hashed,
    )

    token = create_access_token({"id": str(user["id"]), "role": "user"})
    return AuthResponse(token=token, role="user", access_token=token)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Login a user and return a JWT token."""
    user = await conn.fetchrow(
        "SELECT * FROM users WHERE email = $1", data.email
    )
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = user.get("role", "user")
    token = create_access_token({"id": str(user["id"]), "role": role})
    return AuthResponse(token=token, role=role, access_token=token)


@router.post("/admin/login", response_model=AuthResponse)
async def admin_login(data: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Login an admin and return a JWT token."""
    admin = await conn.fetchrow(
        "SELECT * FROM admins WHERE email = $1", data.email
    )
    if not admin or not verify_password(data.password, admin["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"id": str(admin["id"]), "role": "admin"})
    return AuthResponse(token=token, role="admin", access_token=token)


@router.get("/me")
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    GET /auth/me — Contract §1.
    Called by the frontend after login to populate Topbar, Sidebar, and ProfilePage
    with real user data instead of hardcoded placeholders.
    """
    user = await conn.fetchrow(
        "SELECT id, email, full_name, avatar_url, role FROM users WHERE id = $1",
        current_user.id,
    )
    if not user:
        # Fall back to admins table
        user = await conn.fetchrow(
            "SELECT id, email, full_name, avatar_url, 'admin' AS role FROM admins WHERE id = $1",
            current_user.id,
        )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch real usage stats if the column / table exists; default gracefully
    usage = await conn.fetchrow(
        "SELECT searches_this_month FROM user_usage WHERE user_id = $1",
        current_user.id,
    ) if False else None  # Replace `False` with `True` once user_usage table exists

    return {
        "id": str(user["id"]),
        "name": user["full_name"] or "User",
        "email": user["email"],
        "role": user["role"],
        "plan": "free",
        "searches_this_month": usage["searches_this_month"] if usage else 0,
        "searches_limit": 50,
    }
