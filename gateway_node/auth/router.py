from fastapi import APIRouter, HTTPException, Depends, status
import asyncpg
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from .models import RegisterRequest, LoginRequest, AuthResponse

router = APIRouter()

@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Register a new user"""
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", data.email
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(data.password)
    user = await conn.fetchrow(
        "INSERT INTO users (email, hashed_password) VALUES ($1, $2) RETURNING id",
        data.email, hashed
    )

    token = create_access_token({"id": str(user["id"]), "role": "user"})
    return AuthResponse(
        token=token, 
        role="user",
        access_token=token # For Swagger UI
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Login a user and return JWT token (Accepts JSON email/password)"""
    user = await conn.fetchrow(
        "SELECT * FROM users WHERE email = $1", data.email
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role = user.get("role", "user")
    token = create_access_token({"id": str(user["id"]), "role": role})
    return AuthResponse(
        token=token, 
        role=role,
        access_token=token # For Swagger UI
    )


@router.post("/admin/login", response_model=AuthResponse)
async def admin_login(data: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    """Login an admin and return JWT token (Accepts JSON email/password)"""
    admin = await conn.fetchrow(
        "SELECT * FROM admins WHERE email = $1", data.email
    )
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, admin["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"id": str(admin["id"]), "role": "admin"})
    return AuthResponse(
        token=token, 
        role="admin",
        access_token=token # For Swagger UI
    )
