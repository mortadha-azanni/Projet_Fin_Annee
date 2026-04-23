from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_token
from .models import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_admin_scheme = OAuth2PasswordBearer(tokenUrl="/auth/admin/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Validates JWT from Authorization header and returns current user data."""
    token_data = decode_token(token)
    if token_data.role not in ("user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return token_data


async def get_current_admin(token: str = Depends(oauth2_admin_scheme)) -> TokenData:
    """Validates JWT from Authorization header and returns admin data."""
    token_data = decode_token(token)
    if token_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data


async def get_ws_user(token: str = Query(..., description="Bearer token")) -> TokenData:
    """
    WebSocket token dependency.
    WebSocket upgrades don't carry Authorization headers, so the frontend
    must pass the token as a query parameter: ws://host/path?token=<jwt>
    """
    token_data = decode_token(token)
    if token_data.role not in ("user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return token_data


async def get_ws_admin(token: str = Query(..., description="Bearer token")) -> TokenData:
    """
    Admin WebSocket token dependency.
    Pass token as query param: ws://host/path?token=<admin_jwt>
    """
    token_data = decode_token(token)
    if token_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data
