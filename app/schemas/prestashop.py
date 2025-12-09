# app/schemas/prestashop.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PrestashopCategoryNode(BaseModel):
    """
    Nó de categoria tal como vem do Prestashop.
    Aceita campos extra (se o módulo adicionar mais coisas no futuro).
    """

    model_config = ConfigDict(extra="ignore")

    id_category: int
    id_parent: int
    name: str
    level_depth: int
    active: bool
    position: int
    children: list[PrestashopCategoryNode] = Field(default_factory=list)


PrestashopCategoryNode.model_rebuild()


class PrestashopCategoriesOut(BaseModel):
    """
    Envelope completo devolvido pelo endpoint /prestashop/categories.
    É basicamente o payload do r_genesys/getcategories validado.
    """

    model_config = ConfigDict(extra="ignore")

    root_category_id: int
    language_id: int
    shop_id: int
    categories: list[PrestashopCategoryNode]
