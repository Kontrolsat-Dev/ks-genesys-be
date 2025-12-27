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
from app.repositories.procurement.read.supplier_read_repo import SupplierReadRepository
from app.repositories.procurement.write.mapper_write_repo import MapperWriteRepository
from app.repositories.procurement.write.supplier_feed_write_repo import (
    SupplierFeedWriteRepository,
)
from app.repositories.procurement.write.supplier_write_repo import (
    SupplierWriteRepository,
)
from app.schemas.suppliers import SupplierBundleUpdate, SupplierDetailOut
from app.domains.audit.services.audit_service import AuditService

log = logging.getLogger("gsm.procurement.update_bundle")


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
    """
    Atualiza supplier, feed e mapper num único bundle atómico.

    Nota arquitetural:
    Este UseCase (escrita) invoca `get_supplier_detail` (leitura) no final para
    devolver o objeto atualizado. Em CQRS puro, o write devolveria apenas o ID
    e o frontend faria GET separado. Optámos por devolver o objeto completo
    para melhor UX (menos round-trips).
    """
    db = uow.db

    sup_w = SupplierWriteRepository(db)
    feed_r = SupplierFeedReadRepository(db)
    feed_w = SupplierFeedWriteRepository(db)
    map_w = MapperWriteRepository(db)

    try:
        # 1) Supplier (usa repo.update)
        _update_supplier_fields(sup_w, id_supplier, payload.supplier)

        # 1b) Se ingest_enabled=True, garantir que existe job pending/running
        if payload.supplier and getattr(payload.supplier, "ingest_enabled", None) is True:
            _ensure_supplier_ingest_job(db, id_supplier)

        # 2) Feed
        feed_entity = _upsert_feed_for_supplier(feed_w, id_supplier, payload.feed)

        # 3) Mapper (depende do feed)
        _upsert_mapper_for_feed(map_w, feed_r, id_supplier, feed_entity, payload.mapper)

        # Registar no audit log (antes do commit)
        supplier = SupplierReadRepository(db).get(id_supplier)
        if supplier:
            AuditService(db).log_supplier_update(
                supplier_id=id_supplier,
                supplier_name=supplier.name,
            )

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


def _ensure_supplier_ingest_job(db, id_supplier: int) -> None:
    """
    Garante que existe um job pending/running para este supplier.
    Chamado quando ingest_enabled é definido como True.
    """
    from app.background.job_handlers import JOB_KIND_SUPPLIER_INGEST
    from app.repositories.worker.read.worker_job_read_repo import WorkerJobReadRepository
    from app.repositories.worker.write.worker_job_write_repo import WorkerJobWriteRepository
    from app.infra.base import utcnow

    job_key = f"{JOB_KIND_SUPPLIER_INGEST}:{id_supplier}"
    job_r = WorkerJobReadRepository(db)

    if job_r.has_active_job_for_key(job_kind=JOB_KIND_SUPPLIER_INGEST, job_key=job_key):
        return  # Já existe job

    job_w = WorkerJobWriteRepository(db)
    job_w.enqueue_job(
        job_kind=JOB_KIND_SUPPLIER_INGEST,
        job_key=job_key,
        payload={"id_supplier": id_supplier},
        not_before=utcnow(),
    )
    log.info("Created supplier_ingest job for supplier %d (ingest_enabled toggled)", id_supplier)
