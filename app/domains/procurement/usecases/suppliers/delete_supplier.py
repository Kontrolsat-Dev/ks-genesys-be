# app/domains/procurement/usecases/suppliers/delete_supplier.py
"""
UseCase para eliminar um fornecedor.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, NotFound
from app.infra.uow import UoW
from app.repositories.procurement.write.supplier_write_repo import SupplierWriteRepository
from app.domains.audit.services.audit_service import AuditService


def execute(uow: UoW, *, id_supplier: int) -> None:
    """
    Elimina um fornecedor.

    Args:
        uow: Unit of Work
        id_supplier: ID do fornecedor a eliminar

    Raises:
        NotFound: Se o fornecedor não existir
        Conflict: Se houver registos relacionados
    """
    db = uow.db
    repo = SupplierWriteRepository(db)

    supplier = repo.get(id_supplier)
    if not supplier:
        raise NotFound("Supplier not found")

    supplier_name = supplier.name

    try:
        repo.delete(supplier)

        # Registar no audit log (antes do commit)
        AuditService(db).log_supplier_delete(
            supplier_id=id_supplier,
            supplier_name=supplier_name,
        )

        uow.commit()

    except IntegrityError as err:
        uow.rollback()
        raise Conflict("Cannot delete supplier due to related records") from err

    except Exception as err:
        uow.rollback()
        raise BadRequest("Could not delete supplier") from err
