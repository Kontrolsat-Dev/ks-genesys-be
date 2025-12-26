# app/domains/procurement/usecases/suppliers/create_supplier.py
"""
UseCase para criar um novo fornecedor.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, InvalidArgument
from app.infra.uow import UoW
from app.repositories.procurement.write.supplier_write_repo import SupplierWriteRepository
from app.schemas.suppliers import SupplierCreate, SupplierOut


def execute(uow: UoW, *, data: SupplierCreate) -> SupplierOut:
    """
    Cria um fornecedor e faz commit via UoW.

    Toda a lógica de normalização/unique fica no SupplierWriteRepository.create.
    Aqui só gerimos a transação e mapeamos erros para AppErrors.

    Returns:
        SupplierOut schema
    """
    db = uow.db
    repo = SupplierWriteRepository(db)

    try:
        entity = repo.create(data)
        uow.commit()
        return SupplierOut.model_validate(entity)

    except (InvalidArgument, Conflict):
        # erros de domínio conhecidos → apenas rollback e rethrow
        uow.rollback()
        raise

    except IntegrityError as err:
        # se escapar alguma IntegrityError não tratada no repo
        uow.rollback()
        raise Conflict("Could not create supplier due to integrity error") from err

    except Exception as err:
        uow.rollback()
        raise BadRequest("Could not create supplier") from err
