



import os
import secrets
import logging
from datetime import datetime, timedelta, timezone

import asyncpg
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jose import JWTError, jwt

from core.database import get_db
from .models import SendVerificationRequest

verification_router = APIRouter()
logger = logging.getLogger(__name__)

# ── Token settings ────────────────────────────────────────────────────────────
SECRET_KEY   = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY", "change-me")
ALGORITHM    = "HS256"
TOKEN_EXPIRE = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_HOURS", 24))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ── SMTP (fastapi-mail) ───────────────────────────────────────────────────────
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "My App")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")

fm = None
if SMTP_USERNAME and SMTP_PASSWORD and SMTP_FROM:
    mail_conf = ConnectionConfig(
        MAIL_USERNAME=SMTP_USERNAME,
        MAIL_PASSWORD=SMTP_PASSWORD,
        MAIL_FROM=SMTP_FROM,
        MAIL_FROM_NAME=MAIL_FROM_NAME,
        MAIL_PORT=SMTP_PORT,
        MAIL_SERVER=SMTP_HOST,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )
    fm = FastMail(mail_conf)
    logger.info("Email verification enabled (SMTP host=%s, port=%s, from=%s)", SMTP_HOST, SMTP_PORT, SMTP_FROM)
else:
    missing = [
        name
        for name, value in {
            "SMTP_USERNAME": SMTP_USERNAME,
            "SMTP_PASSWORD": SMTP_PASSWORD,
            "SMTP_FROM": SMTP_FROM,
        }.items()
        if not value
    ]
    logger.warning("Email verification disabled: missing SMTP config: %s", ", ".join(missing))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE)
    return jwt.encode(
        {"sub": email, "exp": expire, "type": "email_verification", "jti": secrets.token_hex(16)},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def _decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def _build_email(to_email: str, token: str) -> MessageSchema:
    url = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><style>
      body{{font-family:'Segoe UI',sans-serif;background:#f5f5f5;margin:0;padding:40px 0}}
      .card{{max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
      .hdr{{background:#111;padding:36px 40px;text-align:center;color:#fff}}
      .hdr h1{{margin:0;font-size:22px;letter-spacing:1px}}
      .body{{padding:40px;color:#333;line-height:1.6}}
      .btn{{display:inline-block;margin-top:28px;background:#111;color:#fff!important;text-decoration:none;padding:14px 32px;border-radius:6px;font-weight:600;font-size:15px}}
      .foot{{padding:20px 40px;font-size:12px;color:#999;border-top:1px solid #eee}}
      .url{{word-break:break-all;color:#666;font-size:12px;margin-top:20px}}
    </style></head><body>
      <div class="card">
        <div class="hdr"><h1>Verify your email</h1></div>
        <div class="body">
          <p>Thanks for signing up! Click below to verify your address.
             This link expires in <strong>{TOKEN_EXPIRE} hours</strong>.</p>
          <a class="btn" href="{url}">Verify my email →</a>
          <p class="url">Or paste in your browser:<br>{url}</p>
        </div>
        <div class="foot">If you didn't create an account, ignore this email.</div>
      </div>
    </body></html>
    """
    return MessageSchema(subject="Verify your email address", recipients=[to_email], body=html, subtype=MessageType.html)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@verification_router.post("/send-verification")
async def send_verification(
    data: SendVerificationRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    user = await conn.fetchrow("SELECT id, email_verified FROM users WHERE email = $1", data.email)

    # Always 200 — don't leak whether the email exists
    if not user:
        return {"message": "If that address is registered, a verification email was sent."}

    if user["email_verified"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified.")

    if fm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification is not configured on this gateway instance.",
        )

    token = _create_token(data.email)
    await conn.execute("UPDATE users SET verification_token = $1 WHERE email = $2", token, data.email)
    await fm.send_message(_build_email(data.email, token))

    return {"message": "Verification email sent. Please check your inbox."}


@verification_router.get("/verify-email")
async def verify_email(token: str, conn: asyncpg.Connection = Depends(get_db)):
    email = _decode_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link.")

    user = await conn.fetchrow("SELECT email_verified, verification_token FROM users WHERE email = $1", email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user["email_verified"]:
        return {"message": "Email already verified."}

    if user["verification_token"] != token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link has already been used or superseded.")

    await conn.execute(
        "UPDATE users SET email_verified = TRUE, verification_token = NULL WHERE email = $1",
        email,
    )

    return {"message": "Email verified successfully!"}