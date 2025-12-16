from __future__ import annotations

from sqlalchemy import select, func, and_, or_, exists
from sqlalchemy.orm import Session, aliased

from app.models.product import Product
from app.models.brand import Brand
from app.models.category import Category
from app.models.supplier_item import SupplierItem
from app.models.supplier_feed import SupplierFeed


class ProductsReadRepository:
    """
    Consultas de leitura para produtos (inclui joins/filtros com procurement
    apenas no caminho de leitura).
    """

    def __init__(self, db: Session):
        self.db = db

    # Lookups simples --------------------------------------------
    def get(self, id_product: int) -> Product | None:
        return self.db.get(Product, id_product)

    def get_by_gtin(self, gtin: str) -> Product | None:
        if not gtin:
            return None
        return self.db.scalar(select(Product).where(Product.gtin == gtin))

    def get_by_brand_mpn(self, id_brand: int, partnumber: str) -> Product | None:
        if not id_brand or not partnumber:
            return None
        stmt = select(Product).where(
            Product.id_brand == id_brand,
            Product.partnumber == partnumber,
        )
        return self.db.scalar(stmt)

    # Helpers internos --------------------------------------------

    def _base_query(self):
        """
        Query base (sem filtros nem ordenação) já com joins a Brand/Category.
        """
        b = aliased(Brand)
        c = aliased(Category)

        stmt = (
            select(
                Product.id,
                Product.gtin,
                Product.id_ecommerce,
                Product.id_brand,
                Product.id_category,
                Product.partnumber,
                Product.name,
                Product.margin,
                Product.description,
                Product.image_url,
                Product.weight_str,
                Product.created_at,
                Product.updated_at,
                b.name.label("brand_name"),
                c.name.label("category_name"),
            )
            .select_from(Product)
            .join(b, b.id == Product.id_brand, isouter=True)
            .join(c, c.id == Product.id_category, isouter=True)
        )

        return stmt, b, c

    def _apply_filters(
        self,
        stmt,
        *,
        b,
        c,
        q: str | None = None,
        gtin: str | None = None,
        partnumber: str | None = None,
        id_brand: int | None = None,
        brand: str | None = None,
        id_category: int | None = None,
        category: str | None = None,
        has_stock: bool | None = None,
        id_supplier: int | None = None,
        imported: bool | None = None,
    ):
        """
        Aplica os filtros comuns (q, gtin, brand, category, stock, supplier)
        sobre um statement que já tenha joins a Brand/Category.
        """
        si = aliased(SupplierItem)
        sf = aliased(SupplierFeed)

        filters: list = []

        if q:
            like = f"%{q.strip()}%"
            filters.append(
                or_(
                    Product.name.ilike(like),
                    Product.partnumber.ilike(like),
                    Product.gtin.ilike(like),
                )
            )

        if gtin:
            filters.append(Product.gtin == gtin)

        if partnumber:
            filters.append(Product.partnumber == partnumber)

        if id_brand:
            filters.append(Product.id_brand == id_brand)
        elif brand:
            filters.append(
                func.lower(func.btrim(b.name))
                == func.lower(func.btrim(func.cast(brand, b.name.type)))
            )

        if id_category:
            filters.append(Product.id_category == id_category)
        elif category:
            filters.append(
                func.lower(func.btrim(c.name))
                == func.lower(func.btrim(func.cast(category, c.name.type)))
            )

        if has_stock is True:
            exists_stock = exists(
                select(si.id).where(
                    and_(
                        si.id_product == Product.id,
                        si.stock > 0,
                    )
                )
            )
            filters.append(exists_stock)
        elif has_stock is False:
            not_exists_stock = ~exists(
                select(si.id).where(
                    and_(
                        si.id_product == Product.id,
                        si.stock > 0,
                    )
                )
            )
            filters.append(not_exists_stock)

        if id_supplier:
            exists_supplier_offer = exists(
                select(si.id)
                .join(sf, sf.id == si.id_feed)
                .where(
                    and_(
                        si.id_product == Product.id,
                        sf.id_supplier == id_supplier,
                    )
                )
            )
            filters.append(exists_supplier_offer)

        # imported: True = tem id_ecommerce, False = não tem
        if imported is True:
            filters.append(Product.id_ecommerce.isnot(None))
            filters.append(Product.id_ecommerce > 0)
        elif imported is False:
            filters.append(
                or_(
                    Product.id_ecommerce.is_(None),
                    Product.id_ecommerce == 0,
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        return stmt

    # Lista paginada com filtros/sort ----------------------------

    def list_products(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        gtin: str | None = None,
        partnumber: str | None = None,
        id_brand: int | None = None,
        brand: str | None = None,
        id_category: int | None = None,
        category: str | None = None,
        has_stock: bool | None = None,
        id_supplier: int | None = None,
        imported: bool | None = None,
        sort: str = "recent",  # "recent" | "name" | "cheapest"
    ):
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        stmt, b, c = self._base_query()
        stmt = self._apply_filters(
            stmt,
            b=b,
            c=c,
            q=q,
            gtin=gtin,
            partnumber=partnumber,
            id_brand=id_brand,
            brand=brand,
            id_category=id_category,
            category=category,
            has_stock=has_stock,
            id_supplier=id_supplier,
            imported=imported,
        )

        si = aliased(SupplierItem)
        sf = aliased(SupplierFeed)

        # Ordenação
        if sort == "name":
            stmt = stmt.order_by(Product.name.asc().nulls_last(), Product.id.asc())
        elif sort == "cheapest":
            # menor preço entre ofertas com stock>0; NULLS LAST
            min_price_with_stock = (
                select(func.min(si.price))
                .select_from(si)
                .join(sf, sf.id == si.id_feed)
                .where(
                    and_(
                        si.id_product == Product.id,
                        si.stock > 0,
                        si.price.isnot(None),
                    )
                )
                .correlate(Product)
                .scalar_subquery()
            )
            stmt = stmt.order_by(
                min_price_with_stock.is_(None),
                min_price_with_stock.asc(),
                Product.id.asc(),
            )
        else:
            # recent: updated_at DESC, depois created_at DESC
            stmt = stmt.order_by(
                Product.updated_at.desc().nulls_last(),
                Product.created_at.desc(),
                Product.id.desc(),
            )

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        rows = self.db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).all()

        return rows, int(total)

    # Facets ------------------------------------------------------

    def get_facets(
        self,
        *,
        q: str | None = None,
        gtin: str | None = None,
        partnumber: str | None = None,
        id_brand: int | None = None,
        brand: str | None = None,
        id_category: int | None = None,
        category: str | None = None,
        has_stock: bool | None = None,
        id_supplier: int | None = None,
    ) -> tuple[list[int], list[int], list[int]]:
        """
        Devolve (brand_ids, category_ids, supplier_ids) válidos para os filtros.

        Regra:
        - Para calcular cada facet, ignoramos o filtro **dessa própria dimensão**,
          mas mantemos os restantes (q, has_stock, etc.), para poderes trocar
          de marca/categoria/fornecedor sem ficares “preso”.
        """

        # --- BRANDS (ignora filtro de brand) ---
        stmt_b, b_b, c_b = self._base_query()
        stmt_b = self._apply_filters(
            stmt_b,
            b=b_b,
            c=c_b,
            q=q,
            gtin=gtin,
            partnumber=partnumber,
            id_brand=None,
            brand=None,
            id_category=id_category,
            category=category,
            has_stock=has_stock,
            id_supplier=id_supplier,
        )
        sub_b = stmt_b.subquery()
        stmt_brand_ids = (
            select(sub_b.c.id_brand)
            .where(sub_b.c.id_brand.isnot(None))
            .distinct()
            .order_by(sub_b.c.id_brand)
        )
        brand_ids = [row[0] for row in self.db.execute(stmt_brand_ids).all()]

        # --- CATEGORIES (ignora filtro de category) ---
        stmt_c, b_c, c_c = self._base_query()
        stmt_c = self._apply_filters(
            stmt_c,
            b=b_c,
            c=c_c,
            q=q,
            gtin=gtin,
            partnumber=partnumber,
            id_brand=id_brand,
            brand=brand,
            id_category=None,
            category=None,
            has_stock=has_stock,
            id_supplier=id_supplier,
        )
        sub_c = stmt_c.subquery()
        stmt_category_ids = (
            select(sub_c.c.id_category)
            .where(sub_c.c.id_category.isnot(None))
            .distinct()
            .order_by(sub_c.c.id_category)
        )
        category_ids = [row[0] for row in self.db.execute(stmt_category_ids).all()]

        # --- SUPPLIERS (ignora filtro de supplier) ---
        stmt_s, b_s, c_s = self._base_query()
        stmt_s = self._apply_filters(
            stmt_s,
            b=b_s,
            c=c_s,
            q=q,
            gtin=gtin,
            partnumber=partnumber,
            id_brand=id_brand,
            brand=brand,
            id_category=id_category,
            category=category,
            has_stock=has_stock,
            id_supplier=None,
        )
        sub_s = stmt_s.subquery()

        si = aliased(SupplierItem)
        sf = aliased(SupplierFeed)

        stmt_supplier_ids = (
            select(sf.id_supplier)
            .select_from(si)
            .join(sf, sf.id == si.id_feed)
            .join(sub_s, sub_s.c.id == si.id_product)
            .distinct()
            .order_by(sf.id_supplier)
        )
        supplier_ids = [row[0] for row in self.db.execute(stmt_supplier_ids).all()]

        return brand_ids, category_ids, supplier_ids

    # Dados de produto individual -------------------------------

    def get_product_with_names(self, id_product: int):
        b = aliased(Brand)
        c = aliased(Category)
        stmt = (
            select(
                Product.id,
                Product.gtin,
                Product.id_ecommerce,
                Product.id_brand,
                Product.id_category,
                Product.partnumber,
                Product.name,
                Product.margin,
                Product.description,
                Product.image_url,
                Product.weight_str,
                Product.created_at,
                Product.updated_at,
                b.name.label("brand_name"),
                c.name.label("category_name"),
            )
            .select_from(Product)
            .join(b, b.id == Product.id_brand, isouter=True)
            .join(c, c.id == Product.id_category, isouter=True)
            .where(Product.id == id_product)
        )
        row = self.db.execute(stmt).first()
        return row

    def get_id_by_gtin(self, gtin: str) -> int | None:
        if not gtin:
            return None
        stmt = select(Product.id).where(Product.gtin == gtin)
        return self.db.scalar(stmt)

    def get_product_margin(self, id_product: int) -> float:
        """
        Devolve a margem do produto.

        Nota: Retorna 0.0 se margin for NULL. Na prática, isto não acontece
        porque produtos só são criados via ingest e herdam a margem do supplier.
        Não há criação manual de produtos — o Genesys trata apenas produtos
        de fornecedores.
        """
        if not id_product:
            return 0.0

        product = self.db.get(Product, id_product)
        if product is None or product.margin is None:
            return 0.0

        try:
            margin = float(product.margin)
        except (TypeError, ValueError):
            return 0.0

        if margin < 0:
            margin = 0.0

        return margin
