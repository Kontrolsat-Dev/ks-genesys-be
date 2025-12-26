from pydantic import BaseModel


class BrandIn(BaseModel):
    name: str


class BrandOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class BrandListOut(BaseModel):
    items: list[BrandOut]
    total: int
    page: int
    page_size: int
