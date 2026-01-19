# app/domains/procurement/services/feed_loader.py
from __future__ import annotations

import asyncio
import json
import logging
from copy import deepcopy
from typing import Any

from app.external.feed_downloader import FeedDownloader, parse_rows_json, parse_rows_csv

log = logging.getLogger(__name__)


class FeedHttpError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = int(status_code)
        self.message = message
        super().__init__(message)


def _extract_rows_from_json(raw: bytes, json_root: str | None = None) -> list[dict[str, Any]]:
    """
    Extrai linhas de um payload JSON.

    - Se json_root for fornecido (ex.: "productos" ou "data.items"), tenta navegar
      até aí e devolver a lista de objetos.
    - Se falhar ou não houver json_root, cai no parse_rows_json() heurístico.
    """
    if not raw:
        return []

    if json_root:
        try:
            obj = json.loads(raw.decode(errors="ignore"))
        except Exception:
            # JSON truncado ou inválido → fallback
            return parse_rows_json(raw)

        data: Any = obj
        # Suporta "productos" ou "data.items" (dot-notation simples)
        for part in str(json_root).split("."):
            if isinstance(data, dict):
                data = data.get(part)
            else:
                data = None
                break

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]

        # json_root mal definido → fallback
        return parse_rows_json(raw)

    # Sem json_root, comportamento antigo
    return parse_rows_json(raw)


async def load_feed_rows(
    *,
    downloader: FeedDownloader,
    feed,
    headers: dict[str, Any] | None,
    params: dict[str, Any] | None,
    auth: dict[str, Any] | None,
    extra: dict[str, Any] | None,
    fmt: str,
    json_root: str | None,
    limit: int | None,
    log_prefix: str,
) -> tuple[list[dict[str, Any]], int]:
    """
    Faz o download do feed com suporte a paginação (extra.pagination.mode='page').

    Devolve:
      - rows -> lista de dicts (já cortada por 'limit', se existir)
      - total -> total de linhas recebidas do fornecedor (antes de aplicar limit)
    """
    pagination = None
    if isinstance(extra, dict):
        p = extra.get("pagination")
        if isinstance(p, dict):
            pagination = p

    # --- Sem paginação configurada -> comportamento antigo (uma chamada) ---
    if not pagination or str(pagination.get("mode") or "").lower() != "page":
        status_code, content_type, raw, err_text = await downloader.download_feed(
            kind=getattr(feed, "kind", None),
            url=feed.url,
            headers=headers,
            params=params,
            auth_kind=getattr(feed, "auth_kind", None),
            auth=auth,
            extra=extra,
            timeout_s=60,
        )
        if status_code < 200 or status_code >= 300:
            raise FeedHttpError(status_code, err_text or f"HTTP {status_code}")

        if fmt == "json":
            rows = _extract_rows_from_json(raw, json_root=json_root)
        else:
            rows = parse_rows_csv(
                raw,
                delimiter=(feed.csv_delimiter or ","),
                max_rows=None,
            )

        total = len(rows)
        if limit is not None and len(rows) > limit:
            rows = rows[:limit]
        return rows, total

    # --- Com paginação "page" (concorrente) ---
    page_field = str(pagination.get("page_field") or "page")
    size_field_raw = pagination.get("size_field")
    size_field = str(size_field_raw) if size_field_raw else None

    # início
    start_raw = pagination.get("start", 1)
    try:
        start = int(start_raw)
    except (TypeError, ValueError):
        start = 1

    # nº máximo de páginas
    max_pages_raw = pagination.get("max_pages", 1)
    try:
        max_pages = int(max_pages_raw)
    except (TypeError, ValueError):
        max_pages = 1

    stop_on_empty = pagination.get("stop_on_empty")
    if not isinstance(stop_on_empty, bool):
        stop_on_empty = True

    base_params = dict(params or {})
    base_extra = dict(extra or {}) if extra else {}
    base_body_json = None
    if isinstance(base_extra.get("body_json"), (dict, list)):
        base_body_json = deepcopy(base_extra["body_json"])

    all_rows: list[dict[str, Any]] = []
    total = 0

    # concorrência configurável (extra.pagination.concurrency) com default
    try:
        max_concurrent = int(pagination.get("concurrency") or 5)
    except (TypeError, ValueError):
        max_concurrent = 5

    if max_concurrent < 1:
        max_concurrent = 1

    last_page = start + max_pages - 1
    next_page = start

    def has_more_pages() -> bool:
        return next_page <= last_page

    async def fetch_page(page: int) -> tuple[int, list[dict[str, Any]]]:
        page_params = dict(base_params)
        page_params[page_field] = str(page)

        extra_page = dict(base_extra)

        # body_json base do utilizador + override dos campos de página (se for dict)
        if isinstance(base_body_json, dict):
            body_json = dict(base_body_json)
            body_json[page_field] = page
            # só usamos limit como "page size" em modo debug
            if size_field and limit is not None:
                body_json[size_field] = limit
            extra_page["body_json"] = body_json
        elif base_body_json is not None:
            extra_page["body_json"] = base_body_json

        log.info(
            "[%s] fetching page=%s params=%s",
            log_prefix,
            page,
            {page_field: page_params.get(page_field)},
        )

        status_code, content_type, raw, err_text = await downloader.download_feed(
            kind=getattr(feed, "kind", None),
            url=feed.url,
            headers=headers,
            params=page_params,
            auth_kind=getattr(feed, "auth_kind", None),
            auth=auth,
            extra=extra_page,
            timeout_s=60,
        )

        if status_code < 200 or status_code >= 300:
            raise FeedHttpError(
                status_code,
                err_text or f"HTTP {status_code} (page {page})",
            )

        if fmt == "json":
            page_rows = _extract_rows_from_json(raw, json_root=json_root)
        else:
            page_rows = parse_rows_csv(
                raw,
                delimiter=(feed.csv_delimiter or ","),
                max_rows=None,
            )

        return page, page_rows

    pending: dict[asyncio.Task, int] = {}

    # lançar as primeiras páginas até encher a janela de concorrência
    while has_more_pages() and len(pending) < max_concurrent:
        page = next_page
        next_page += 1
        task = asyncio.create_task(fetch_page(page))
        pending[task] = page

    stop_more = False

    while pending:
        done, _ = await asyncio.wait(
            set(pending.keys()),
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            page_num = pending.pop(task)
            try:
                page, page_rows = await task
            except FeedHttpError as e:
                # falha HTTP numa página → falha a run inteira
                raise e
            except Exception as e:  # noqa: BLE001
                # erro inesperado
                raise FeedHttpError(
                    500,
                    f"Page {page_num} failed: {type(e).__name__}: {e}",
                ) from e

            count_page = len(page_rows)
            total += count_page

            # aplica limit ao conjunto acumulado
            if limit is not None:
                remaining = limit - len(all_rows)
                if remaining <= 0:
                    stop_more = True
                    continue
                if count_page > remaining:
                    page_rows = page_rows[:remaining]
                    count_page = len(page_rows)

            all_rows.extend(page_rows)

            log.info(
                "[%s] page=%s rows=%s accumulated=%s",
                log_prefix,
                page,
                count_page,
                len(all_rows),
            )

            # parar se a página veio vazia e stop_on_empty=true
            if count_page == 0 and stop_on_empty:
                stop_more = True

            # parar se já chegámos ao limit
            if limit is not None and len(all_rows) >= limit:
                stop_more = True

        if stop_more:
            # cancelar qualquer página ainda pendente
            to_cancel = list(pending.keys())
            for t in to_cancel:
                t.cancel()
            if to_cancel:
                await asyncio.gather(*to_cancel, return_exceptions=True)
            pending.clear()
            break

        # encher novamente a janela de concorrência
        while has_more_pages() and len(pending) < max_concurrent:
            page = next_page
            next_page += 1
            task = asyncio.create_task(fetch_page(page))
            pending[task] = page

    return all_rows, total
