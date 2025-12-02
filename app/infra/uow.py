# app/infra/uow.py
# Unit of Work simples para SQLAlchemy

from __future__ import annotations

from sqlalchemy.orm import Session


class UoW:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self._committed = False  # mantemos só para o __exit__

    def commit(self) -> None:
        self.db.commit()
        self._committed = True

    def rollback(self) -> None:
        self.db.rollback()
        self._committed = True

    def __enter__(self) -> UoW:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc or not self._committed:
            self.rollback()
