from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidArgument
from app.models.product import Product
from app.models.product_meta import ProductMeta

# Importes de write repos para garantir criação de brand/category quando em falta.
# (usa import local para evitar ciclos, se necessário)
from app.repositories.catalog.write.brand_write_repo import BrandsWriteRepository
from app.repositories.catalog.write.category_write_repo import CategoryWriteRepository


class ProductWriteRepository:
    """
    Operações de escrita/manutenção de produtos.
    (Herda implicitamente a possibilidade de fazer lookups simples, mas
    deixamos os lookups mais ricos no read repo.)
    """

    def __init__(self, db: Session):
        self.db = db

    # --- Lookups auxiliares para writes (CQRS pragmático) ----------
    # Usados internamente antes de operações de escrita.
    # Para queries ricas de leitura, usar ProductsReadRepository.
    def get(self, id_product: int) -> Product | None:
        return self.db.get(Product, id_product)

    def get_by_gtin(self, gtin: str) -> Product | None:
        if not gtin:
            return None
        gtin_norm = gtin.strip()
        if not gtin_norm:
            return None
        return self.db.scalar(select(Product).where(Product.gtin == gtin_norm))

    def get_by_brand_mpn(self, id_brand: int, partnumber: str) -> Product | None:
        if not id_brand or not partnumber:
            return None
        part_norm = partnumber.strip()
        if not part_norm:
            return None
        stmt = select(Product).where(
            Product.id_brand == id_brand,
            Product.partnumber == part_norm,
        )
        return self.db.scalar(stmt)

    # --- Escrita -------------------------------------------------
    def get_or_create(
        self,
        *,
        gtin: str | None,
        partnumber: str | None,
        brand_name: str | None,
        default_margin: float | None,
    ) -> Product:
        """
        Regra:

        - Se HÁ GTIN → GTIN manda em tudo:
            * tenta get_by_gtin(gtin)
            * se não existir → cria novo Product com esse GTIN
            * NÃO cai para brand+mpn

        - Se NÃO há GTIN → aí sim usamos brand+MPN para dedupe:
            * cria/resolve brand por nome (BrandsWriteRepository)
            * tenta get_by_brand_mpn(id_brand, partnumber)
            * se não existir → cria produto sem GTIN

        - Se não há GTIN nem (brand+mpn) → erro (InvalidArgument).
        """

        gtin_norm = gtin.strip() if gtin else None
        part_norm = partnumber.strip() if partnumber else None
        brand_norm = brand_name.strip() if brand_name else None

        # 1) Caso com GTIN → só GTIN conta
        if gtin_norm:
            # tentar encontrar produto por GTIN
            p = self.get_by_gtin(gtin_norm)
            if p:
                return p

            # opcionalmente ainda podemos associar brand se vier no feed
            id_brand = None
            if brand_norm:
                id_brand = BrandsWriteRepository(self.db).get_or_create(brand_norm).id

            p = Product(
                gtin=gtin_norm,
                id_brand=id_brand,
                partnumber=part_norm,
                margin=(default_margin or 0.0),
            )
            self.db.add(p)
            self.db.flush()
            return p

        # 2) Sem GTIN → podemos usar brand+MPN como chave
        id_brand = None
        if brand_norm:
            id_brand = BrandsWriteRepository(self.db).get_or_create(brand_norm).id

        # Sem GTIN e sem (brand+mpn) ⇒ não temos chave
        if not (id_brand and part_norm):
            raise InvalidArgument("Missing product key (gtin or brand+mpn)")

        # Tentar dedupe por brand+mpn
        p = self.get_by_brand_mpn(id_brand, part_norm)
        if p:
            return p

        # Criar novo produto sem GTIN (catálogo sem código de barras)
        p = Product(
            gtin=None,
            id_brand=id_brand,
            partnumber=part_norm,
            margin=(default_margin or 0.0),
        )
        self.db.add(p)
        self.db.flush()
        return p

    def fill_canonicals_if_empty(self, id_product: int, **fields):
        p = self.db.get(Product, id_product)
        if not p:
            return
        changed = False
        for k, v in fields.items():
            if v in (None, ""):
                continue
            if getattr(p, k, None) in (None, "", 0):
                setattr(p, k, v)
                changed = True
        if changed:
            self.db.add(p)
            self.db.flush()

    def fill_brand_category_if_empty(
        self, id_product: int, *, brand_name: str | None, category_name: str | None
    ):
        p = self.db.get(Product, id_product)
        if not p:
            return
        changed = False
        if brand_name and not p.id_brand:
            p.id_brand = BrandsWriteRepository(self.db).get_or_create(brand_name).id
            changed = True
        if category_name and not p.id_category:
            p.id_category = CategoryWriteRepository(self.db).get_or_create(category_name).id
            changed = True
        if changed:
            self.db.add(p)
            self.db.flush()

    def add_meta_if_missing(self, id_product: int, *, name: str, value: str) -> tuple[bool, bool]:
        row = self.db.scalar(
            select(ProductMeta).where(
                ProductMeta.id_product == id_product,
                ProductMeta.name == name,
            )
        )
        if row is None:
            self.db.add(ProductMeta(id_product=id_product, name=name, value=value))
            # flush só se precisares do id
            return True, False
        else:
            return (False, (row.value or "") != (value or ""))

    def set_margin(self, id_product: int, margin: float) -> None:
        """
        Atualiza apenas a margem do produto.

        Validação semântica (ex.: não permitir < 0) deve ser feita no usecase;
        aqui o repo só aplica a alteração e faz flush.
        """
        p = self.db.get(Product, id_product)
        if not p:
            return
        p.margin = margin
        self.db.add(p)
        self.db.flush()

    def set_eol(self, id_product: int, is_eol: bool) -> None:
        """
        Marca um produto como EOL (End of Life) ou não.

        EOL significa que o produto desapareceu de todos os catálogos de fornecedores
        (não veio em nenhum feed), não apenas que tem stock = 0.
        """
        p = self.db.get(Product, id_product)
        if not p:
            return
        if p.is_eol != is_eol:
            p.is_eol = is_eol
            self.db.add(p)
            self.db.flush()
