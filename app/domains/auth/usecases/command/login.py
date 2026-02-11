# app/domains/auth/usecases/login.py
"""
UseCase para autenticação de utilizadores.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Callable

from app.core.config import settings
from app.core.errors import Unauthorized
from app.schemas.auth import LoginRequest, LoginResponse
from app.shared.jwt import create_access_token, create_refresh_token
from app.domains.audit.services.audit_service import AuditService
from app.infra.uow import UoW

AuthFn = Callable[[str, str], dict[str, Any]]


def execute(
    req: LoginRequest,
    *,
    auth_login: AuthFn,
    uow: UoW | None = None,
) -> LoginResponse:
    """
    Autentica via função injetada e emite tokens JWT.
    Retorna access_token (curta duração) e refresh_token (longa duração).

    Argumentos:
        req: Pedido de login com email e password
        auth_login: Função de autenticação (injetada, tipicamente cliente PS)
        uow: Unit of Work opcional para registo de audit logs
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

    # Audit log (se uow disponível)
    if uow is not None:
        AuditService(uow.db).log_user_login(
            user_id=user_id,
            user_name=name,
            email=email,
        )
        uow.commit()

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
