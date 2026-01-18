from app.external.prestashop_client import PrestashopClient
from app.schemas.prestashop import PrestashopOrderDetailOut


def execute(id_order: int, ps_client: PrestashopClient) -> PrestashopOrderDetailOut:
    """
    Obter detalhes de uma encomenda do PrestaShop (JIT) e valida contra schema.
    """
    raw = ps_client.get_order_detail(id_order)
    return PrestashopOrderDetailOut.model_validate(raw)
