from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import PrestashopOrdersDropshippingOut


def execute(
    page: int, page_size: int, ps_client: PrestashopClient
) -> PrestashopOrdersDropshippingOut:
    """
    Obter encomendas do prestashop atraves do modulo r_gensys
    e valida contra o schema Pydantic
    """
    raw = ps_client.get_orders_dropshipping(page, page_size)
    return PrestashopOrdersDropshippingOut.model_validate(raw)
