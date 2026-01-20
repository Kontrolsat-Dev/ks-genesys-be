# app/api/v1/categories.py
# Endpoints para interagir com ERP SAGE 50c Loja

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_access_token

router = APIRouter(
    prefix="/sage",
    tags=["sage"],
    dependencies=[Depends(require_access_token)],
)

# TODO

# GET - Lista de fornecedores
# GET - Produto existe
