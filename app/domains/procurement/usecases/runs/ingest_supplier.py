# app/domains/procurement/usecases/runs/ingest_supplier.py
from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any

from app.core.errors import NotFound
from app.domains.mapping.engine import IngestEngine
from app.domains.procurement.services import (
    FeedHttpError,
    load_feed_rows,
    process_row,
    sync_active_offer_for_products,
)
from app.external.feed_downloader import FeedDownloader
from app.infra.uow import UoW
from app.repositories.catalog.read.products_read_repo import ProductsReadRepository
from app.repositories.catalog.write.product_write_repo import ProductWriteRepository
from app.repositories.procurement.read.feed_run_read_repo import FeedRunReadRepository
from app.repositories.procurement.read.mapper_read_repo import MapperReadRepository
from app.repositories.procurement.read.supplier_feed_read_repo import (
    SupplierFeedReadRepository,
)
from app.repositories.procurement.read.supplier_read_repo import SupplierReadRepository
from app.repositories.procurement.write.feed_run_write_repo import (
    FeedRunWriteRepository,
)
from app.repositories.procurement.write.product_event_write_repo import (
    ProductEventWriteRepository,
)
from app.repositories.procurement.write.supplier_item_write_repo import (
    SupplierItemWriteRepository,
)

log = logging.getLogger("gsm.ingest")


async def execute(uow: UoW, *, id_supplier: int, limit: int | None = None) -> dict[str, Any]:
    """
    Orquestra uma run de ingest para um supplier:

    1) Valida supplier/feed e cria FeedRun.
    2) Faz download + parse do feed (CSV/JSON, com suporte a paginação).
    3) Mapeia linhas via IngestEngine e, por cada linha válida:
       - Product.get_or_create + fill canonicals + brand/category + meta.
       - SupplierItem.upsert → deteta created/changed.
       - ProductSupplierEvent.record_from_item_change (init/change).
    4) mark_eol_for_unseen_items → regista events "eol" + devolve products afetados.
    5) Para cada produto afetado com id_ecommerce:
       - recalcula ProductActiveOffer com base nas SupplierItem atuais;
       - compara snapshot anterior vs novo;
       - se mudou (supplier/preço_enviado/stock) → emite product_state_changed
         no CatalogUpdateStream (prioridade em função da transição de stock).
    6) Finaliza FeedRun (ok/erro) e devolve resumo.
    """
    db = uow.db

    # --- Repositórios (CQRS) ---
    run_r = FeedRunReadRepository(db)
    run_w = FeedRunWriteRepository(db)

    sup_r = SupplierReadRepository(db)
    feed_r = SupplierFeedReadRepository(db)
    mapper_r = MapperReadRepository(db)
    prod_r = ProductsReadRepository(db)

    prod_w = ProductWriteRepository(db)
    item_w = SupplierItemWriteRepository(db)
    ev_w = ProductEventWriteRepository(db)

    # --- 1) Supplier + Feed + Run ---
    supplier = sup_r.get_required(id_supplier)
    supplier_margin = float(supplier.margin or 0.0)

    feed = feed_r.get_by_supplier(id_supplier)
    if not feed or not feed.active:
        raise NotFound("Feed not found for supplier")

    run = run_w.start(id_feed=feed.id)
    id_run = run.id

    log.info(
        "[run=%s] start ingest id_supplier=%s id_feed=%s format=%s url=%s",
        id_run,
        id_supplier,
        feed.id,
        feed.format,
        feed.url,
    )

    try:
        # --- 2) Download + parse feed (com suporte a paginação) ---
        headers = json.loads(feed.headers_json) if getattr(feed, "headers_json", None) else None
        params = json.loads(feed.params_json) if getattr(feed, "params_json", None) else None
        auth = json.loads(feed.auth_json) if getattr(feed, "auth_json", None) else None
        extra = json.loads(feed.extra_json) if getattr(feed, "extra_json", None) else None

        # extra_fields.json_root → raiz da lista de dados JSON (ex.: "productos")
        json_root: str | None = None
        if isinstance(extra, dict):
            ef = extra.get("extra_fields")
            if isinstance(ef, dict):
                jr = ef.get("json_root")
                if isinstance(jr, str) and jr.strip():
                    json_root = jr.strip()

        downloader = FeedDownloader()
        fmt = (feed.format or "").lower()

        try:
            rows, total = await load_feed_rows(
                downloader=downloader,
                feed=feed,
                headers=headers,
                params=params,
                auth=auth,
                extra=extra,
                fmt=fmt,
                json_root=json_root,
                limit=limit,
                log_prefix=f"run={id_run}",
            )
        except FeedHttpError as http_err:
            run_w.finalize_http_error(
                id_run,
                http_status=http_err.status_code,
                error_msg=http_err.message,
            )
            uow.commit()
            log.error(
                "[run=%s] download error: HTTP %s msg=%s",
                id_run,
                http_err.status_code,
                http_err.message,
            )
            return {
                "ok": False,
                "id_run": id_run,
                "error": f"HTTP {http_err.status_code}",
            }

        log.info(
            "[run=%s] fetched rows: total=%s using=%s",
            id_run,
            total,
            len(rows),
        )

        # --- 3) Mapping + persistência linha-a-linha ---
        profile = mapper_r.profile_for_feed(feed.id)  # {} se não existir/for inválido
        engine = IngestEngine(profile)

        affected_products: set[int] = set()
        ok = bad = changed = 0

        for idx, raw_row in enumerate(rows, 1):
            ok_inc, bad_inc, changed_inc, product_id = process_row(
                db=db,
                raw_row=raw_row,
                row_index=idx,
                id_run=id_run,
                id_supplier=id_supplier,
                feed=feed,
                engine=engine,
                prod_w=prod_w,
                item_w=item_w,
                ev_w=ev_w,
                supplier_margin=supplier_margin,
            )
            ok += ok_inc
            bad += bad_inc
            changed += changed_inc
            if product_id:
                affected_products.add(product_id)

            if idx % 500 == 0:
                log.info(
                    "[run=%s] progress %s/%s ok=%s bad=%s",
                    id_run,
                    idx,
                    len(rows),
                    ok,
                    bad,
                )

        # --- 4) EOL dos itens não vistos neste run ---
        eol_res = ev_w.mark_eol_for_unseen_items(
            id_feed=feed.id,
            id_supplier=id_supplier,
            id_feed_run=id_run,
        )
        eol_marked = eol_res.items_stock_changed  # “mudanças reais”
        eol_unseen = eol_res.items_total  # “desaparecidos do feed”
        affected_products.update(eol_res.affected_products)

        log.info("[run=%s] EOL marked=%s", id_run, eol_marked)

        # --- 5) Active offer + eventos de estado (apenas para produtos com id_ecommerce) ---
        sync_active_offer_for_products(
            db,
            prod_r,
            affected_products=affected_products,
            reason="ingest_supplier",
        )

        # --- 6) Finalizar run + commit ---
        run_w.finalize_ok(
            id_run,
            rows_total=total,
            rows_changed=changed,
            partial=bool(bad and ok),
        )
        uow.commit()

        status = (run_r.get(id_run) or run).status
        log.info(
            "[run=%s] done status=%s total=%s ok=%s bad=%s changed=%s eol=%s",
            id_run,
            status,
            total,
            ok,
            bad,
            changed,
            eol_marked,
        )

        return {
            "ok": True,
            "id_run": id_run,
            "rows_total": total,
            "rows_processed": ok + bad,
            "rows_valid": ok,
            "rows_invalid": bad,
            "changes": changed,
            "eol_unseen": eol_unseen,
            "eol_marked": eol_marked,
            "status": status,
        }

    except Exception as e:  # noqa: BLE001
        # Hard-fail da run
        with suppress(Exception):
            db.rollback()

        try:
            run_w.finalize_error(
                id_run,
                error_msg=f"{type(e).__name__}: {e}",
            )
            uow.commit()
        except Exception:
            with suppress(Exception):
                db.rollback()

        log.exception("[run=%s] ingest failed", id_run)
        return {"ok": False, "id_run": id_run, "error": str(e)}
