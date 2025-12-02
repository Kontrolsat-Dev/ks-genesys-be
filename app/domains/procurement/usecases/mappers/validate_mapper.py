# app/domains/procurement/usecases/mappers/validate_mapper.py
from __future__ import annotations
from typing import Any

from app.infra.uow import UoW
from app.repositories.procurement.read.mapper_read_repo import MapperReadRepository
from app.schemas.mappers import MapperValidateIn, MapperValidateOut


def _validate(profile: dict[str, Any] | None, headers: list[str] | None) -> dict[str, Any]:
    profile = profile or {}
    fields = profile.get("fields") or {}
    required = {"gtin", "price", "stock"}

    # aceita formato lista ou dict
    if isinstance(fields, list):
        norm = {}
        for row in fields:
            t = (row or {}).get("target")
            if t:
                norm[t] = {k: v for k, v in row.items() if k != "target"}
        fields = norm

    errors = []
    for r in required:
        if r not in fields:
            errors.append({"code": "missing_field", "msg": f"Required field '{r}' is not mapped"})

    headers_checked = False
    if headers is not None:
        headers_checked = True
        hdrset = {str(h).lower() for h in headers}
        for _tgt, cfg in fields.items():
            src = (cfg or {}).get("source") or (cfg or {}).get("from")
            if src and str(src).lower() not in hdrset:
                errors.append(
                    {"code": "missing_source", "msg": f"Source '{src}' does not exist in headers"}
                )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": [],
        "required_coverage": {r: (r in fields) for r in required},
        "headers_checked": headers_checked,
    }


def execute(uow: UoW, *, id_feed: int, payload: MapperValidateIn) -> MapperValidateOut:
    db = uow.db
    profile = payload.profile
    if profile is None:
        # usa o helper do read-repo que já te devolve dict seguro
        repo = MapperReadRepository(db)
        profile = repo.get_by_feed(id_feed)  # {} se não existir ou se json estiver inválido

        if not profile:
            return MapperValidateOut(
                ok=False,
                errors=[{"code": "not_found", "msg": "Mapper not found for this feed"}],
                warnings=[],
                required_coverage={},
                headers_checked=False,
            )

    res = _validate(profile, headers=payload.headers)
    return MapperValidateOut(**res)
