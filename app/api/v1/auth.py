# app/api/v1/auth.py
from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.deps import require_access_token, get_prestashop_client
from app.domains.auth.usecases.login import execute as uc_login
from app.external.prestashop_client import PrestashopClient
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
UserDep = Annotated[dict, Depends(require_access_token)]


@router.post("/login", response_model=LoginResponse)
def post_login(
    body: LoginRequest,
    client: PrestashopClient = Depends(get_prestashop_client),
):
    return uc_login(body, auth_login=client.login)


@router.get("/me")
def get_me(user: UserDep):
    return {"user": user}
