# app/domains/prestashop/usecases/categories/list_categories.py
from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import PrestashopCategoriesOut


def execute(ps_client: PrestashopClient) -> PrestashopCategoriesOut:
    """
    GET Prestashop via r_genesys, obtém o JSON bruto
    e valida contra o schema Pydantic.
    """
    raw = ps_client.get_categories()
    return PrestashopCategoriesOut.model_validate(raw)
