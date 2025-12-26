# app/domains/auth/usecases/refresh_tokens.py
"""
Usecase para renovação de tokens JWT.
"""

from __future__ import annotations

import jwt

from app.core.config import settings
from app.core.errors import Unauthorized
from app.schemas.auth import RefreshRequest, RefreshResponse
from app.shared.jwt import decode_token, create_access_token, create_refresh_token


def execute(req: RefreshRequest) -> RefreshResponse:
    """
    Valida refresh_token e emite novos tokens.
    Keep domain pure: no HTTPException here.
    """
    try:
        payload = decode_token(req.refresh_token, expected_typ="refresh")
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Refresh token expired") from None
    except jwt.InvalidTokenError as e:
        raise Unauthorized(f"Invalid refresh token: {e}") from e

    sub = payload.get("sub", "")
    role = payload.get("role", "user")
    name = payload.get("name")

    new_access = create_access_token(sub=sub, role=role, name=name)
    new_refresh = create_refresh_token(sub=sub, role=role, name=name)

    return RefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_EXPIRE_MIN * 60,
        refresh_expires_in=settings.JWT_REFRESH_EXPIRE_MIN * 60,
    )
