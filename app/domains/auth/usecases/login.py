# app/domains/auth/usecases/login.py
from __future__ import annotations
from typing import Any
from collections.abc import Callable

from app.core.config import settings
from app.core.errors import Unauthorized
from app.schemas.auth import LoginRequest, LoginResponse
from app.shared.jwt import create_access_token, create_refresh_token

AuthFn = Callable[[str, str], dict[str, Any]]


def execute(req: LoginRequest, *, auth_login: AuthFn) -> LoginResponse:
    """
    Authenticate via injected auth function and issue JWT tokens.
    Returns both access_token (short-lived) and refresh_token (long-lived).
    """
    try:
        user = auth_login(req.email, req.password)
    except Exception as err:
        # genérico para não vazar detalhes
        raise Unauthorized("Invalid credentials") from err

    user_id = str(user.get("id"))
    role = user.get("role", "user")
    name = user.get("name")

    access = create_access_token(sub=user_id, role=role, name=name)
    refresh = create_refresh_token(sub=user_id, role=role, name=name)

    expires_in = settings.JWT_EXPIRE_MIN * 60
    refresh_expires_in = settings.JWT_REFRESH_EXPIRE_MIN * 60

    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        user={
            "uid": user.get("id"),
            "email": user.get("email"),
            "name": name,
            "role": role,
        },
    )
