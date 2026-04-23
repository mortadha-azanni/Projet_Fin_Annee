import os
import httpx
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from core.security import create_access_token
import asyncpg

async def get_db():
    return await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        ssl="require"
    )

oauth_router = APIRouter()

# ─── Config ──────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173/SEARCHILY_FrontEnd")


# ─── Step 1: Redirect to Google ──────────────────────────────────
@oauth_router.get("/google")
async def google_login():
    """Redirect user to Google login page"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


# ─── Step 2: Handle Google Callback ──────────────────────────────
@oauth_router.get("/google/callback")
async def google_callback(code: str):
    """
    Google redirects here after user accepts.
    - Exchange code for access token
    - Fetch user info from Google
    - Create user in DB if new
    - Return JWT token to frontend
    """

    # 1. Exchange code for Google access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    # 2. Fetch user info from Google
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    userinfo = userinfo_response.json()
    email = userinfo.get("email")
    full_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")
    email_verified = userinfo.get("email_verified", False)
    google_id = userinfo.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="Could not get email from Google")

    # 3. Check if user exists, create if not
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )

        if not user:
            # New user — create account (no password since OAuth)
            user = await conn.fetchrow(
                """
                INSERT INTO users (email, hashed_password, full_name, avatar_url, email_verified, google_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                email, None, full_name, avatar_url, email_verified, google_id
            )
        else:
            # Existing user — update google_id and email_verified if not set
            await conn.execute(
                """
                UPDATE users
                SET google_id = $1, email_verified = $2
                WHERE email = $3
                """,
                google_id, email_verified, email
            )

        # 4. Generate JWT token
        jwt_token = create_access_token({
            "id": str(user["id"]),
            "role": "user"
        })

    finally:
        await conn.close()

    # 5. Redirect frontend with token in URL
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/callback?token={jwt_token}&role=user"
    )