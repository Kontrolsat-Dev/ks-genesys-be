import sys
import os

# Adicionar o diretório raiz ao path para encontrar o app
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.infra.session import engine


def migrate():
    print("Iniciando migração de taxas...")

    queries = [
        # Permitir NULL em ecotax e remover default 0
        "ALTER TABLE products ALTER COLUMN ecotax DROP NOT NULL",
        "ALTER TABLE products ALTER COLUMN ecotax SET DEFAULT NULL",
        # Permitir NULL em extra_fees e remover default 0
        "ALTER TABLE products ALTER COLUMN extra_fees DROP NOT NULL",
        "ALTER TABLE products ALTER COLUMN extra_fees SET DEFAULT NULL",
        # Opcional: converter zeros existentes em NULL para forçar herança inicial se desejado
        # "UPDATE products SET ecotax = NULL WHERE ecotax = 0",
        # "UPDATE products SET extra_fees = NULL WHERE extra_fees = 0",
    ]

    try:
        with engine.connect() as conn:
            for query in queries:
                print(f"Executando: {query}")
                conn.execute(text(query))
            conn.commit()
            print("Migração concluída com sucesso!")
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migrate()
