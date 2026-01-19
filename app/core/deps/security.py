import logging
from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import Unauthorized
from app.shared.jwt import decode_token

log = logging.getLogger(__name__)
_auth = HTTPBearer(auto_error=True)


def require_access_token(creds: Annotated[HTTPAuthorizationCredentials, Depends(_auth)]):
    try:
        return decode_token(creds.credentials, expected_typ="access")
    except Exception as e:
        log.error("Invalid/expired token: %s", e)
        raise Unauthorized("Token inválido ou expirado") from e
