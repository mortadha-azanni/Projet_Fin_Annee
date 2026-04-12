from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from .jwt import decode_token
from .models import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_admin_scheme = OAuth2PasswordBearer(tokenUrl="/auth/admin/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Validates JWT and returns current user"""
    token_data = decode_token(token)
    if token_data.role != "user":
        raise HTTPException(status_code=403, detail="Not authorized")
    return token_data


async def get_current_admin(token: str = Depends(oauth2_admin_scheme)) -> TokenData:
    """Validates JWT and returns current admin"""
    token_data = decode_token(token)
    if token_data.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token_data