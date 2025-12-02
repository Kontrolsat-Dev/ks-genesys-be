# app/domains/procurement/usecases/mappers/put_mapper.py
from __future__ import annotations

from app.infra.uow import UoW
from sqlalchemy.exc import IntegrityError
from app.core.errors import BadRequest, Conflict, InvalidArgument, NotFound
from app.repositories.procurement.write.mapper_write_repo import MapperWriteRepository
from app.repositories.procurement.read.supplier_feed_read_repo import SupplierFeedReadRepository
from app.schemas.mappers import FeedMapperOut, FeedMapperUpsert


def execute(uow: UoW, *, id_feed: int, payload: FeedMapperUpsert) -> FeedMapperOut:
    db = uow.db

    if not payload or payload.profile is None or not isinstance(payload.profile, dict):
        raise InvalidArgument("Mapper profile must be a non-empty object")

    # garante que o feed existe
    feed_repo = SupplierFeedReadRepository(db)
    if not feed_repo.get(id_feed):
        raise NotFound("Feed not found")

    repo = MapperWriteRepository(db)
    try:
        entity = repo.upsert_profile(
            id_feed=id_feed,
            profile=payload.profile,
            bump_version=payload.bump_version,
        )
        uow.commit()
    except IntegrityError as err:
        uow.rollback()
        raise Conflict("Could not upsert mapper due to integrity constraints") from err
    except Exception as err:
        uow.rollback()
        raise BadRequest("Could not upsert mapper") from err

    return FeedMapperOut.from_entity(entity)
