# app/domains/procurement/usecases/suppliers/delete_supplier.py
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, NotFound
from app.infra.uow import UoW
from app.repositories.procurement.write.supplier_write_repo import SupplierWriteRepository


def execute(uow: UoW, *, id_supplier: int) -> None:
    db = uow.db
    repo = SupplierWriteRepository(db)

    supplier = repo.get(id_supplier)
    if not supplier:
        raise NotFound("Supplier not found") from None

    try:
        # repo.delete espera a entidade ORM
        repo.delete(supplier)
        uow.commit()
    except IntegrityError as err:
        uow.rollback()
        # FK em itens/feeds, etc.
        raise Conflict("Cannot delete supplier due to related records") from err
    except Exception as err:
        uow.rollback()
        # não expomos detalhes internos; middleware mapeia para {"code","detail"}
        raise BadRequest("Could not delete supplier") from err
