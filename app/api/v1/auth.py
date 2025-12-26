# app/api/v1/auth.py
"""
Endpoints de autenticação.
"""

from typing import Annotated
from fastapi import APIRouter, Depends

from app.core.deps import require_access_token, get_prestashop_client, get_uow
from app.domains.auth.usecases.login import execute as uc_login
from app.domains.auth.usecases.refresh_tokens import execute as uc_refresh
from app.external.prestashop_client import PrestashopClient
from app.infra.uow import UoW
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse

router = APIRouter(prefix="/auth", tags=["auth"])
UserDep = Annotated[dict, Depends(require_access_token)]


@router.post("/login", response_model=LoginResponse, summary="Autenticação de utilizador")
def post_login(
    body: LoginRequest,
    client: PrestashopClient = Depends(get_prestashop_client),
    uow: UoW = Depends(get_uow),
):
    """
    Autenticação de utilizador.
    Retorna access_token (curta duração) e refresh_token (longa duração).
    """
    return uc_login(body, auth_login=client.login, db=uow.db)


@router.post("/refresh", response_model=RefreshResponse, summary="Renovar tokens")
def post_refresh(body: RefreshRequest):
    """
    Renova os tokens usando um refresh_token válido.
    Retorna novos access_token e refresh_token.
    """
    return uc_refresh(body)


@router.get("/me", summary="Informações do utilizador autenticado")
def get_me(user: UserDep):
    """
    Retorna as informações do utilizador autenticado.
    """
    return {"user": user}
