from typing import Any
from collections.abc import Callable
from app.external.prestashop_client import PrestashopClient

AuthFn = Callable[[str, str], dict[str, Any]]
UpdateFn = Callable[[int, int], dict[str, Any]]


def get_prestashop_client() -> PrestashopClient:
    return PrestashopClient()
