import sqlite3
import csv
import unicodedata
import os

# 📂 Caminho do banco no disco persistente do Render
DB_PATH = "/data/dados.db"
CSV_PATH = "empresas.csv"

# 🗂️ Garantir que a pasta exista
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 🔤 Normalizar texto (remover acentos e minúsculo)
def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto

# 🏗️ Criar tabela se não existir
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

# 📥 Importar CSV
def importar_csv():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = 0
    inseridos = 0

    if not os.path.exists(CSV_PATH):
        print(f"Arquivo {CSV_PATH} não encontrado!")
        return

    with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            total += 1

            try:
                cnpj = row["cnpj"].strip()
                razao = row["razao_social"].strip()
                municipio = normalizar_texto(row["municipio"].strip())
                uf = row["uf"].strip()

                cursor.execute("""
                    INSERT OR IGNORE INTO empresas (cnpj, razao_social, municipio, uf)
                    VALUES (?, ?, ?, ?)
                """, (cnpj, razao, municipio, uf))

                if cursor.rowcount > 0:
                    inseridos += 1

            except Exception as e:
                print(f"Erro ao inserir linha {total}: {e}")

    conn.commit()
    conn.close()

    print(f"Total lidos: {total}")
    print(f"Inseridos: {inseridos}")

# 🚀 Execução
if __name__ == "__main__":
    print("Iniciando importação...")
    init_db()
    importar_csv()
    print("Importação finalizada.")
