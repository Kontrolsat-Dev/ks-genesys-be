# app/domains/procurement/usecases/suppliers/update_bundle.py
"""
UseCase para atualizar um fornecedor e opcionalmente o seu feed e mapper.
"""

from __future__ import annotations

import json
from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, NotFound
from app.infra.uow import UoW
from app.schemas.suppliers import SupplierBundleUpdate, SupplierDetailOut, SupplierOut
from app.schemas.feeds import SupplierFeedOut
from app.schemas.mappers import FeedMapperOut
from app.domains.audit.services.audit_service import AuditService


def execute(
    uow: UoW,
    *,
    id_supplier: int,
    payload: SupplierBundleUpdate,
) -> SupplierDetailOut:
    """
    Atualiza um fornecedor e opcionalmente o seu feed e mapper numa única operação.

    Args:
        uow: Unit of Work
        id_supplier: ID do fornecedor a atualizar
        payload: Bundle com dados a atualizar (supplier, feed, mapper)

    Returns:
        SupplierDetailOut com supplier, feed e mapper atualizados
    """
    try:
        # 1) Verificar se o fornecedor existe
        supplier = uow.suppliers.get(id_supplier)
        if not supplier:
            raise NotFound(f"Fornecedor {id_supplier} não encontrado")

        changes: dict = {}

        # 2) Atualizar supplier se fornecido
        if payload.supplier:
            update_data = payload.supplier.model_dump(exclude_unset=True)
            if update_data:
                for key, value in update_data.items():
                    old_value = getattr(supplier, key, None)
                    if old_value != value:
                        changes[key] = {"old": old_value, "new": value}
                    setattr(supplier, key, value)
                uow.db.add(supplier)

        # 3) Atualizar feed se fornecido
        feed = uow.feeds.get_by_supplier(id_supplier)
        if payload.feed:
            feed_data = payload.feed.model_dump(exclude_unset=True)

            def mutate_feed(entity):
                entity.kind = feed_data.get(
                    "kind", entity.kind if hasattr(entity, "kind") else "http"
                )
                entity.format = feed_data.get(
                    "format", entity.format if hasattr(entity, "format") else "csv"
                )
                entity.url = feed_data.get("url", entity.url if hasattr(entity, "url") else "")
                entity.active = feed_data.get(
                    "active", entity.active if hasattr(entity, "active") else True
                )
                if "headers" in feed_data and feed_data["headers"]:
                    entity.headers_json = json.dumps(feed_data["headers"])
                if "params" in feed_data and feed_data["params"]:
                    entity.params_json = json.dumps(feed_data["params"])
                if "auth_kind" in feed_data:
                    entity.auth_kind = feed_data["auth_kind"]
                if "auth" in feed_data and feed_data["auth"]:
                    entity.auth_json = json.dumps(feed_data["auth"])
                if "extra" in feed_data and feed_data["extra"]:
                    entity.extra_json = json.dumps(feed_data["extra"])
                if "csv_delimiter" in feed_data:
                    entity.csv_delimiter = feed_data["csv_delimiter"]

            feed = uow.feeds_w.upsert_for_supplier(id_supplier, mutate_feed)

        # 4) Atualizar mapper se fornecido
        mapper = None
        if payload.mapper and feed:
            profile = payload.mapper.profile or {}
            bump_version = (
                payload.mapper.bump_version if hasattr(payload.mapper, "bump_version") else True
            )
            mapper = uow.mappers_w.set_profile(feed.id, profile, bump_version=bump_version)

        # Re-fetch mapper se não foi alterado mas existe
        if mapper is None and feed:
            mapper = uow.mappers.get_by_feed(feed.id)

        # 5) Registar no audit log
        if changes:
            AuditService(uow.db).log_supplier_update(
                supplier_id=id_supplier,
                supplier_name=supplier.name,
                changes=changes,
            )

        uow.commit()

        # 6) Construir resposta
        feed_out = SupplierFeedOut.from_entity(feed) if feed else None
        mapper_out = FeedMapperOut.from_entity(mapper) if mapper else None

        return SupplierDetailOut(
            supplier=SupplierOut.model_validate(supplier),
            feed=feed_out,
            mapper=mapper_out,
        )

    except NotFound:
        uow.rollback()
        raise

    except IntegrityError as err:
        uow.rollback()
        raise Conflict(
            "Não foi possível atualizar fornecedor devido a erro de integridade"
        ) from err

    except Exception as err:
        uow.rollback()
        raise BadRequest(f"Não foi possível atualizar fornecedor: {err}") from err
