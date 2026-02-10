from __future__ import annotations

from sqlalchemy import select

from app.core.errors import InvalidArgument
from app.models.product import Product
from app.models.product_meta import ProductMeta
from app.repositories.catalog.read.product_read_repo import ProductReadRepository


class ProductWriteRepository(ProductReadRepository):
    """
    Operações de escrita/manutenção de produtos.
    """

    def get_or_create(
        self,
        *,
        gtin: str | None = None,
        partnumber: str | None = None,
        id_brand: int | None = None,
        default_margin: float | None = None,
    ) -> Product:
        """
        Tenta encontrar por GTIN (prioritário) ou por (partnumber + id_brand).
        Se não encontrar, cria.
        """
        gtin_norm = gtin.strip() if gtin else None
        pn_norm = partnumber.strip() if partnumber else None

        # 1) Caso com GTIN → só GTIN conta
        if gtin_norm:
            p = self.get_by_gtin(gtin_norm)
            if p:
                return p

        # 2) Sem GTIN ou não encontrado → tenta PN + Brand
        if pn_norm and id_brand:
            p = self.get_by_brand_mpn(id_brand, pn_norm)
            if p:
                return p

        # 3) Não encontrado → Criar
        if not gtin_norm and not (pn_norm and id_brand):
            raise InvalidArgument("Need at least GTIN or (PN + Brand) to get/create")

        p = Product(
            gtin=gtin_norm,
            partnumber=pn_norm,
            id_brand=id_brand,
            margin=default_margin,
            is_eol=False,
        )
        self.db.add(p)
        self.db.flush()
        return p

    def fill_canonicals_if_empty(
        self,
        id_product: int,
        *,
        name: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        weight_str: str | None = None,
        partnumber: str | None = None,
        gtin: str | None = None,
    ) -> bool:
        """
        Preenche campos canónicos se estiverem vazios.
        """
        p = self.get(id_product)
        if not p:
            return False

        changed = False

        if name and not p.name:
            p.name = name[:255]
            changed = True
        if description and not p.description:
            p.description = description
            changed = True
        if image_url and not p.image_url:
            p.image_url = image_url[:512]
            changed = True
        if weight_str and not p.weight_str:
            # Note: The model field is weight_str in some places but weight in others?
            # Let's check Product model.
            p.weight_str = weight_str[:100]
            changed = True

        if partnumber and not p.partnumber:
            p.partnumber = partnumber
            changed = True
        if gtin and not p.gtin:
            p.gtin = gtin
            changed = True

        if changed:
            self.db.flush()

        return changed

    def add_meta_if_missing(self, id_product: int, name: str, value: str) -> tuple[bool, bool]:
        row = self.db.scalar(
            select(ProductMeta).where(
                ProductMeta.id_product == id_product,
                ProductMeta.name == name,
            )
        )
        if row is None:
            self.db.add(ProductMeta(id_product=id_product, name=name, value=value))
            return True, False
        else:
            return (False, (row.value or "") != (value or ""))

    def set_margin(self, id_product: int, margin: float) -> None:
        p = self.get(id_product)
        if not p:
            return
        p.margin = margin
        self.db.flush()

    def set_eol(self, id_product: int, is_eol: bool) -> None:
        p = self.get(id_product)
        if not p:
            return
        if p.is_eol != is_eol:
            p.is_eol = is_eol
            self.db.flush()
