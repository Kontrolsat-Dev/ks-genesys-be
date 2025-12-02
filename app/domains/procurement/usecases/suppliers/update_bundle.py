from __future__ import annotations

from typing import Any
import json
import logging

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, NotFound, InvalidArgument
from app.domains.procurement.usecases.suppliers.get_supplier_detail import (
    execute as uc_get_detail,
)
from app.infra.uow import UoW
from app.repositories.procurement.read.supplier_feed_read_repo import (
    SupplierFeedReadRepository,
)
from app.repositories.procurement.write.mapper_write_repo import MapperWriteRepository
from app.repositories.procurement.write.supplier_feed_write_repo import (
    SupplierFeedWriteRepository,
)
from app.repositories.procurement.write.supplier_write_repo import (
    SupplierWriteRepository,
)
from app.schemas.suppliers import SupplierBundleUpdate, SupplierDetailOut

log = logging.getLogger("gsm.http")


def _update_supplier_fields(
    sup_w: SupplierWriteRepository,
    id_supplier: int,
    supplier_data: Any | None,
) -> None:
    """
    Aplica apenas os campos presentes usando o metodo update do repo,
    que já trata de normalização e unicidade do nome.
    """
    if supplier_data is None:
        return

    kwargs: dict[str, Any] = {}

    for f in (
        "name",
        "active",
        "logo_image",
        "contact_name",
        "contact_phone",
        "contact_email",
        "margin",
        "country",
        "ingest_interval_minutes",
        "ingest_enabled",
        "ingest_next_run_at",
    ):
        if hasattr(supplier_data, f):
            v = getattr(supplier_data, f)
            if v is not None:
                kwargs[f] = v

    if not kwargs:
        return

    sup_w.update(id_supplier, **kwargs)


def _apply_feed_mutations(entity: Any, feed_payload: Any) -> None:
    # campos simples
    for f in ("kind", "format", "url", "active", "csv_delimiter", "auth_kind"):
        v = getattr(feed_payload, f, None)
        if v is not None:
            setattr(entity, f, v)

    # blobs JSON (segue o mesmo padrão que usaste no upsert_supplier_feed)
    if hasattr(feed_payload, "headers"):
        entity.headers_json = (
            None
            if feed_payload.headers is None
            else json.dumps(feed_payload.headers, ensure_ascii=False)
        )
    if hasattr(feed_payload, "params"):
        entity.params_json = (
            None
            if feed_payload.params is None
            else json.dumps(feed_payload.params, ensure_ascii=False)
        )
    if hasattr(feed_payload, "extra"):
        entity.extra_json = (
            None
            if feed_payload.extra is None
            else json.dumps(feed_payload.extra, ensure_ascii=False)
        )
    if hasattr(feed_payload, "auth"):
        entity.auth_json = (
            None if feed_payload.auth is None else json.dumps(feed_payload.auth, ensure_ascii=False)
        )


def _upsert_feed_for_supplier(
    feed_w: SupplierFeedWriteRepository,
    id_supplier: int,
    feed_payload: Any | None,
) -> Any | None:
    if feed_payload is None:
        return None

    def mutate(e: Any) -> None:
        _apply_feed_mutations(e, feed_payload)

    return feed_w.upsert_for_supplier(id_supplier, mutate)


def _upsert_mapper_for_feed(
    map_w: MapperWriteRepository,
    feed_r: SupplierFeedReadRepository,
    id_supplier: int,
    feed_entity: Any | None,
    mapper_payload: Any | None,
) -> None:
    if mapper_payload is None:
        return

    feed_e = feed_entity or feed_r.get_by_supplier(id_supplier)
    if not feed_e:
        raise BadRequest("Cannot upsert mapper without a feed for this supplier")

    feed_id = getattr(feed_e, "id", None) or getattr(feed_e, "id_feed", None)
    if feed_id is None:
        raise BadRequest("Feed entity missing id")

    map_w.upsert_profile(
        feed_id,
        mapper_payload.profile or {},
        bump_version=bool(getattr(mapper_payload, "bump_version", True)),
    )


def execute(uow: UoW, *, id_supplier: int, payload: SupplierBundleUpdate) -> SupplierDetailOut:
    db = uow.db

    sup_w = SupplierWriteRepository(db)
    feed_r = SupplierFeedReadRepository(db)
    feed_w = SupplierFeedWriteRepository(db)
    map_w = MapperWriteRepository(db)

    try:
        # 1) Supplier (usa repo.update)
        _update_supplier_fields(sup_w, id_supplier, payload.supplier)

        # 2) Feed
        feed_entity = _upsert_feed_for_supplier(feed_w, id_supplier, payload.feed)

        # 3) Mapper (depende do feed)
        _upsert_mapper_for_feed(map_w, feed_r, id_supplier, feed_entity, payload.mapper)

        uow.commit()

    except (NotFound, InvalidArgument, Conflict):
        uow.rollback()
        raise
    except IntegrityError as err:
        uow.rollback()
        raise Conflict("Could not update supplier bundle due to integrity constraints") from err
    except Exception as err:
        uow.rollback()
        raise BadRequest("Could not update supplier bundle") from err

    # Devolver o detalhe atualizado
    return uc_get_detail(uow, id_supplier=id_supplier)
