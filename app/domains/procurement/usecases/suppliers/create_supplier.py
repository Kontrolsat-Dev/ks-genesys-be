from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.errors import BadRequest, Conflict, InvalidArgument
from app.infra.uow import UoW
from app.models.supplier import Supplier
from app.repositories.procurement.write.supplier_write_repo import SupplierWriteRepository
from app.schemas.suppliers import SupplierCreate


def execute(uow: UoW, *, data: SupplierCreate) -> Supplier:
    """
    Create a supplier and commit via UoW.

    Toda a lógica de normalização/unique fica no SupplierWriteRepository.create.
    Aqui só gerimos a transação e mapeamos erros para AppErrors.
    """
    db = uow.db
    repo = SupplierWriteRepository(db)

    try:
        entity = repo.create(data)
        uow.commit()
        return entity

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
