"""
UseCase: Importar encomendas dropshipping do PrestaShop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.infra.uow import UoW
from app.external.prestashop_client import PrestashopClient
from app.repositories.orders_dropshipping.read.dropshipping_order_read_repo import (
    DropshippingOrderReadRepository,
)
from app.repositories.orders_dropshipping.write.dropshipping_order_write_repo import (
    DropshippingOrderWriteRepository,
    DropshippingOrderLineWriteRepository,
)
from app.repositories.catalog.read.product_read_repo import ProductReadRepository

log = logging.getLogger("gsm.dropshipping.import_orders")


@dataclass
class ImportResult:
    """Resultado da importação."""

    total_fetched: int = 0
    imported: int = 0
    skipped: int = 0  # Já existiam
    errors: int = 0
    error_messages: list[str] | None = None


def execute(
    uow: UoW,
    ps_client: PrestashopClient,
    *,
    since: str | None = None,
    page_size: int = 50,
    max_pages: int = 10,
) -> ImportResult:
    """
    Importa encomendas dropshipping do PrestaShop.

    Args:
        uow: Unit of Work
        ps_client: Cliente PrestaShop
        since: Data ISO para filtrar (date_upd >= since)
        page_size: Tamanho da página
        max_pages: Máximo de páginas a processar (limite de segurança)

    Returns:
        ImportResult com estatísticas
    """
    db = uow.db
    order_r = DropshippingOrderReadRepository(db)
    order_w = DropshippingOrderWriteRepository(db)
    line_w = DropshippingOrderLineWriteRepository(db)
    product_r = ProductReadRepository(db)

    result = ImportResult(error_messages=[])

    for page in range(1, max_pages + 1):
        try:
            log.info("import_orders page=%d since=%s", page, since or "none")

            data = ps_client.get_orders_dropshipping(
                page=page,
                page_size=page_size,
                since=since,
            )

            items = data.get("items", [])
            if not items:
                log.info("import_orders sem_mais_itens page=%d", page)
                break

            result.total_fetched += len(items)

            for item in items:
                try:
                    _import_order(
                        item,
                        order_r=order_r,
                        order_w=order_w,
                        line_w=line_w,
                        product_r=product_r,
                        result=result,
                    )
                except Exception as e:
                    result.errors += 1
                    msg = f"Encomenda {item.get('id_order')}: {e}"
                    result.error_messages.append(msg)
                    log.warning("import_orders erro order=%s: %s", item.get("id_order"), e)

            # Se retornou menos que page_size, não há mais páginas
            if len(items) < page_size:
                break

        except Exception as e:
            result.errors += 1
            result.error_messages.append(f"Página {page}: {e}")
            log.error("import_orders erro_pagina page=%d: %s", page, e)
            break

    # Commit de todas as alterações
    uow.commit()

    log.info(
        "import_orders completo fetched=%d imported=%d skipped=%d errors=%d",
        result.total_fetched,
        result.imported,
        result.skipped,
        result.errors,
    )

    return result


def _import_order(
    item: dict,
    *,
    order_r: DropshippingOrderReadRepository,
    order_w: DropshippingOrderWriteRepository,
    line_w: DropshippingOrderLineWriteRepository,
    product_r: ProductReadRepository,
    result: ImportResult,
) -> None:
    """Importa uma encomenda individual."""

    id_ps_order = item["id_order"]

    # Verificar se já existe
    if order_r.exists_by_ps_order_id(id_ps_order):
        result.skipped += 1
        return

    # Parse cliente
    customer = item.get("customer", {})

    # Parse datas
    ps_date_add = datetime.fromisoformat(item["date_add"].replace(" ", "T"))
    ps_date_upd = datetime.fromisoformat(item["date_upd"].replace(" ", "T"))

    # Criar encomenda
    order = order_w.create(
        id_ps_order=id_ps_order,
        reference=item["reference"],
        customer_email=customer.get("email", ""),
        customer_firstname=customer.get("firstname", ""),
        customer_lastname=customer.get("lastname", ""),
        delivery_address=item.get("delivery_address") or {},
        invoice_address=item.get("invoice_address") or {},
        carrier_name=item.get("carrier", {}).get("name"),
        payment_method=item.get("payment"),
        total_paid_tax_incl=Decimal(str(item.get("total_paid_tax_incl", 0))),
        total_paid_tax_excl=Decimal(str(item.get("total_paid_tax_excl", 0))),
        total_shipping_tax_incl=Decimal(str(item.get("total_shipping_tax_incl", 0))),
        total_shipping_tax_excl=Decimal(str(item.get("total_shipping_tax_excl", 0))),
        ps_date_add=ps_date_add,
        ps_date_upd=ps_date_upd,
    )

    # Criar linhas - apenas products com match
    lines = item.get("dropshipping_lines", [])
    imported_lines = 0
    for ln in lines:
        # Tentar fazer match do produto por EAN
        ean = ln.get("product_ean13") or ln.get("product_reference")
        id_product = None

        if ean:
            product = product_r.get_by_gtin(ean)
            if product:
                id_product = product.id

        # Só importar linhas com match no catálogo
        if id_product is None:
            log.debug(
                "import_orders skip_line_no_match order=%d ean=%s ref=%s",
                id_ps_order,
                ln.get("product_ean13"),
                ln.get("product_reference"),
            )
            continue

        line_w.create(
            id_order=order.id,
            id_ps_order_detail=ln["id_order_detail"],
            id_ps_product=ln["id_product"],
            id_ps_product_attribute=ln.get("id_product_attribute", 0),
            product_name=ln["product_name"],
            product_reference=ln.get("product_reference"),
            product_ean=ln.get("product_ean13"),
            product_supplier_reference=ln.get("product_supplier_reference"),
            qty=ln["qty"],
            unit_price_tax_excl=Decimal(str(ln.get("unit_price_tax_excl", 0))),
            unit_price_tax_incl=Decimal(str(ln.get("unit_price_tax_incl", 0))),
            total_price_tax_excl=Decimal(str(ln.get("total_price_tax_excl", 0))),
            total_price_tax_incl=Decimal(str(ln.get("total_price_tax_incl", 0))),
            id_product=id_product,
        )
        imported_lines += 1

    result.imported += 1
    log.debug(
        "import_orders importada order=%d ref=%s lines=%d (de %d)",
        id_ps_order,
        order.reference,
        imported_lines,
        len(lines),
    )
