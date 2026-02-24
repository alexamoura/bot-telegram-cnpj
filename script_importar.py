import sqlite3
import csv
import unicodedata

DB_PATH = "/var/data/dados.db"  # no Render
CSV_PATH = "empresas.csv"

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        cnpj TEXT PRIMARY KEY,
        razao_social TEXT,
        municipio TEXT,
        uf TEXT
    )
    """)

    conn.commit()
    conn.close()

def importar_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = 0
    inseridos = 0

    with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            total += 1

            cnpj = row["cnpj"].strip()
            razao = row["razao_social"].strip()
            municipio = normalizar_texto(row["municipio"].strip())
            uf = row["uf"].strip()

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO empresas (cnpj, razao_social, municipio, uf)
                    VALUES (?, ?, ?, ?)
                """, (cnpj, razao, municipio, uf))

                if cursor.rowcount > 0:
                    inseridos += 1

            except Exception as e:
                print(f"Erro ao inserir {cnpj}: {e}")

    conn.commit()
    conn.close()

    print(f"Total lidos: {total}")
    print(f"Inseridos: {inseridos}")

if __name__ == "__main__":
    init_db()
    importar_csv()