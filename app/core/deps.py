# app/core/deps.py
# Dependências comuns para rotas FastAPI

import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import Unauthorized
from app.infra.session import get_session
from app.infra.uow import UoW
from app.shared.jwt import decode_token
from app.external.prestashop_client import PrestahopClient


log = logging.getLogger(__name__)

_auth = HTTPBearer(auto_error=True)


def require_access_token(creds: Annotated[HTTPAuthorizationCredentials, Depends(_auth)]):
    try:
        return decode_token(creds.credentials, expected_typ="access")
    except Exception as e:
        log.error("Error validating token: %s", e)
        raise Unauthorized("Token inválido ou expirado") from e


def get_uow(db: Annotated[Session, Depends(get_session)]) -> UoW:
    return UoW(db)


def get_auth_login():
    return PrestahopClient().login
