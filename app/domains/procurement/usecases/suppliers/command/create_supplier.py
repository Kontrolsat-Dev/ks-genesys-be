# app/domains/procurement/usecases/suppliers/create_supplier.py
"""
UseCase para criar um novo fornecedor.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, InvalidArgument
from app.infra.uow import UoW
from app.schemas.suppliers import SupplierCreate, SupplierOut
from app.domains.audit.services.audit_service import AuditService


def execute(uow: UoW, *, data: SupplierCreate) -> SupplierOut:
    """
    Cria um fornecedor e faz commit via UoW.

    Toda a lógica de normalização/unique fica no SupplierWriteRepository.create.
    Aqui só gerimos a transação e mapeamos erros para AppErrors.

    Returns:
        SupplierOut schema
    """
    try:
        entity = uow.suppliers_w.create(data)

        # Registar no audit log (antes do commit para estar na mesma transação)
        AuditService(uow.db).log_supplier_create(
            supplier_id=entity.id,
            supplier_name=entity.name,
        )

        uow.commit()

        return SupplierOut.model_validate(entity)

    except (InvalidArgument, Conflict):
        uow.rollback()
        raise

    except IntegrityError as err:
        uow.rollback()
        raise Conflict("Não foi possível criar fornecedor devido a erro de integridade") from err

    except Exception as err:
        uow.rollback()
        raise BadRequest("Não foi possível criar fornecedor") from err
