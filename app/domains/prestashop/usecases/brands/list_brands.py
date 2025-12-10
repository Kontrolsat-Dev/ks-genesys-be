# app/domains/prestashop/usecases/list_brands.py

from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import PrestashopBrandsOut


def execute(ps_client: PrestashopClient) -> PrestashopBrandsOut:
    """
    GET Prestashop via r_genesys, obtém o JSON bruto
    e valida contra o schema Pydantic.
    """
    raw = ps_client.get_brands()
    return PrestashopBrandsOut.model_validate(raw)
