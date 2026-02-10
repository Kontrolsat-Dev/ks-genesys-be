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

log = logging.getLogger(__name__)


async def execute(uow: UoW, *, id_supplier: int, limit: int | None = None) -> dict[str, Any]:
    """
    Orquestra uma run de ingest para um supplier:

    1) Valida supplier/feed e cria FeedRun.
    2) Faz download + parse do feed (CSV/JSON, com suporte a paginação).
    3) Mapeia linhas via IngestEngine e, por cada linha válida:
       - Product.get_or_create + fill canonicals + brand/category + meta.
       - SupplierItem.upsert → deteta created/changed.
       - ProductSupplierEvent.record_from_item_change (init/change).
    4) mark_unseen_items_stock_zero → zera stock de itens não vistos neste run
       e regista eventos "feed_missing" por supplier.
    5) Para cada produto afetado com id_ecommerce:
       - recalcula ProductActiveOffer com base nas SupplierItem atuais;
       - compara snapshot anterior vs novo;
       - se mudou (supplier/preço_enviado/stock) → emite product_state_changed
         no CatalogUpdateStream (prioridade em função da transição de stock).
    6) Finaliza FeedRun (ok/erro) e devolve resumo.
    """

    # --- 1) Supplier + Feed + Run ---
    supplier = uow.suppliers.get_required(id_supplier)
    supplier_margin = float(supplier.margin or 0.0)

    feed = uow.feeds.get_by_supplier(id_supplier)
    if not feed or not feed.active:
        raise NotFound("Feed not found for supplier")

    run = uow.feed_runs_w.start(id_feed=feed.id)
    id_run = run.id
    uow.commit()

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
            uow.feed_runs_w.finalize_http_error(
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
        profile = uow.mappers.profile_for_feed(feed.id)  # {} se não existir/for inválido
        engine = IngestEngine(profile)

        affected_products: set[int] = set()
        ok = bad = changed = 0

        for idx, raw_row in enumerate(rows, 1):
            ok_inc, bad_inc, changed_inc, product_id = process_row(
                uow=uow,
                raw_row=raw_row,
                row_index=idx,
                id_run=id_run,
                id_supplier=id_supplier,
                feed=feed,
                engine=engine,
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

        # --- 4) Itens não vistos neste run (stock -> 0 por feed) ---
        unseen_res = uow.product_events_w.mark_unseen_items_stock_zero(
            id_feed=feed.id,
            id_supplier=id_supplier,
            id_feed_run=id_run,
        )
        unseen_total = unseen_res.items_total
        unseen_stock_zeroed = unseen_res.items_stock_zeroed
        affected_products.update(unseen_res.affected_products)

        log.info("[run=%s] unseen_items_stock_zeroed=%s", id_run, unseen_stock_zeroed)

        # --- 5) Active offer + eventos de estado (apenas para produtos com id_ecommerce) ---
        sync_active_offer_for_products(
            uow,
            affected_products=affected_products,
            reason="ingest_supplier",
        )

        # --- 6) Finalizar run + commit ---
        uow.feed_runs_w.finalize_ok(
            id_run,
            rows_total=total,
            rows_changed=changed,
            rows_failed=bad,
            rows_unseen=unseen_stock_zeroed,
            partial=bool(bad and ok),
        )
        uow.commit()

        status = (uow.feed_runs.get(id_run) or run).status
        log.info(
            "[run=%s] done status=%s total=%s ok=%s bad=%s changed=%s unseen_total=%s",
            id_run,
            status,
            total,
            ok,
            bad,
            changed,
            unseen_total,
        )

        return {
            "ok": True,
            "id_run": id_run,
            "rows_total": total,
            "rows_processed": ok + bad,
            "rows_valid": ok,
            "rows_invalid": bad,
            "changes": changed,
            "unseen_total": unseen_total,
            "unseen_stock_zeroed": unseen_stock_zeroed,
            "status": status,
        }

    except Exception as e:  # noqa: BLE001
        # Hard-fail da run
        with suppress(Exception):
            uow.db.rollback()

        try:
            uow.feed_runs_w.finalize_error(
                id_run,
                error_msg=f"{type(e).__name__}: {e}",
            )
            uow.commit()
        except Exception:
            with suppress(Exception):
                uow.db.rollback()

        log.exception("[run=%s] ingest failed", id_run)
        return {"ok": False, "id_run": id_run, "error": str(e)}
