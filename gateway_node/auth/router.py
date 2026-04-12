import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
import asyncpg
from .models import RegisterRequest, TokenResponse
from .jwt import create_access_token

router = APIRouter()

# ─── Password Hashing ────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── DB Connection ───────────────────────────────────────────────
async def get_db():
    """Return a PostgreSQL connection"""
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        ssl="require"
    )
    return conn


# ─── Auth Endpoints ──────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    """Register a new user"""
    conn = await get_db()
    try:
        # Check if email already exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", data.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed = pwd_context.hash(data.password)

        # Insert into DB
        user = await conn.fetchrow(
            "INSERT INTO users (email, hashed_password) VALUES ($1, $2) RETURNING id",
            data.email, hashed
        )

        token = create_access_token({"id": str(user["id"]), "role": "user"})
        return TokenResponse(access_token=token)

    finally:
        await conn.close()


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login a user and return JWT token"""
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", form.username
        )
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not pwd_context.verify(form.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({"id": str(user["id"]), "role": "user"})
        return TokenResponse(access_token=token)

    finally:
        await conn.close()


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    """Login an admin and return JWT token"""
    conn = await get_db()
    try:
        admin = await conn.fetchrow(
            "SELECT * FROM admins WHERE email = $1", form.username
        )
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not pwd_context.verify(form.password, admin["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({"id": str(admin["id"]), "role": "admin"})
        return TokenResponse(access_token=token)

    finally:
        await conn.close()