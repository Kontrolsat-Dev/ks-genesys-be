from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CategoryIn(BaseModel):
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    # Supplier source
    id_supplier_source: int | None = None
    supplier_source_name: str | None = None
    # PrestaShop mapping
    id_ps_category: int | None = None
    ps_category_name: str | None = None
    auto_import: bool = False
    # Default taxes for products in this category
    default_ecotax: float = 0
    default_extra_fees: float = 0

    model_config = ConfigDict(from_attributes=True)


class CategoryListOut(BaseModel):
    items: list[CategoryOut]
    total: int
    page: int
    page_size: int


class CategoryMappingIn(BaseModel):
    """Input para mapear categoria Genesys → PrestaShop"""

    id_ps_category: int
    ps_category_name: str
    auto_import: bool = False
    default_ecotax: float | None = None
    default_extra_fees: float | None = None


class CategoryMappingOut(BaseModel):
    """Output após mapear categoria"""

    id: int
    name: str
    id_ps_category: int | None
    ps_category_name: str | None
    auto_import: bool
    default_ecotax: float = 0
    default_extra_fees: float = 0
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
