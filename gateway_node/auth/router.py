import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from supabase import create_client, Client
from .models import RegisterRequest, TokenResponse
from .jwt import create_access_token

router = APIRouter()

# ─── Supabase Client ─────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Password Hashing ────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    """Register a new user"""
    # Check if email already exists
    existing = supabase.table("users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password before storing
    hashed = pwd_context.hash(data.password)

    # Insert into Supabase
    result = supabase.table("users").insert({
        "email": data.email,
        "hashed_password": hashed
    }).execute()

    user = result.data[0]

    # Return JWT token
    token = create_access_token({"id": str(user["id"]), "role": "user"})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login a user and return JWT token"""
    result = supabase.table("users").select("*").eq("email", form.username).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]

    if not pwd_context.verify(form.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"id": str(user["id"]), "role": "user"})
    return TokenResponse(access_token=token)


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    """Login an admin and return JWT token"""
    result = supabase.table("admins").select("*").eq("email", form.username).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    admin = result.data[0]

    if not pwd_context.verify(form.password, admin["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"id": str(admin["id"]), "role": "admin"})
    return TokenResponse(access_token=token)