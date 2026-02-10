# app/domains/auth/usecases/login.py
"""
UseCase para autenticação de utilizadores.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Unauthorized
from app.schemas.auth import LoginRequest, LoginResponse
from app.shared.jwt import create_access_token, create_refresh_token
from app.domains.audit.services.audit_service import AuditService

AuthFn = Callable[[str, str], dict[str, Any]]


def execute(
    req: LoginRequest,
    *,
    auth_login: AuthFn,
    db: Session | None = None,
) -> LoginResponse:
    """
    Authenticate via injected auth function and issue JWT tokens.
    Returns both access_token (short-lived) and refresh_token (long-lived).

    Args:
        req: Login request with email and password
        auth_login: Function to authenticate (injected, typically PS client)
        db: Optional DB session for audit logging
    """
    try:
        user = auth_login(req.email, req.password)
    except Exception as err:
        # genérico para não vazar detalhes
        raise Unauthorized("Invalid credentials") from err

    user_id = str(user.get("id"))
    role = user.get("role", "user")
    name = user.get("name")
    email = user.get("email")

    access = create_access_token(sub=user_id, role=role, name=name)
    refresh = create_refresh_token(sub=user_id, role=role, name=name)

    expires_in = settings.JWT_EXPIRE_MIN * 60
    refresh_expires_in = settings.JWT_REFRESH_EXPIRE_MIN * 60

    # Audit log (se db disponível)
    if db is not None:
        AuditService(db).log_user_login(
            user_id=user_id,
            user_name=name,
            email=email,
        )
        db.commit()

    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        user={
            "uid": user.get("id"),
            "email": email,
            "name": name,
            "role": role,
        },
    )
