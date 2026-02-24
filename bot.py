import os
import logging
import requests
import sqlite3
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import Conflict

# 🔐 TOKEN
TOKEN = os.getenv("TOKEN")

# 📂 Caminho do banco no disco persistente do Render
DB_PATH = "/data/dados.db"

# 🧾 LOG
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# 🔕 Silenciar logs do Telegram/httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# 🔤 Normalizar texto
def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto

# 🗄️ Conectar no banco
def get_db():
    return sqlite3.connect(DB_PATH)

# 🏗️ Criar tabelas se não existirem
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        cnpj TEXT PRIMARY KEY,
        razao_social TEXT,
        municipio TEXT,
        uf TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios_autorizados (
        user_id INTEGER PRIMARY KEY
    )
    """)

    conn.commit()
    conn.close()

# 🔎 Verificar usuário autorizado
def usuario_autorizado(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM usuarios_autorizados WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result is not None

# ➕ Adicionar usuário autorizado (uso manual via script depois)
def adicionar_usuario(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO usuarios_autorizados (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# 🔎 Consulta BrasilAPI
def buscar_cnpj(cnpj):
    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            logger.warning(f"Erro ao consultar CNPJ {cnpj} | Status: {r.status_code}")
            return None

        return r.json()

    except Exception as e:
        logger.error(f"Erro ao consultar CNPJ {cnpj} | {e}")
        return None

# 📊 Estimar funcionários
def estimar_funcionarios(porte):
    if not porte:
        return "Não informado"

    porte = porte.upper()

    if "MEI" in porte:
        return "1 funcionário"
    elif "MICRO" in porte or "ME" in porte:
        return "1 a 9 funcionários"
    elif "PEQUENO" in porte or "EPP" in porte:
        return "10 a 49 funcionários"
    else:
        return "50+ funcionários"

# 🧾 Formatar empresa
def formatar_empresa(data):
    nome = data.get("razao_social", "N/A")
    fantasia = data.get("nome_fantasia", "N/A")
    cidade = data.get("municipio", "N/A")
    uf = data.get("uf", "N/A")
    situacao = data.get("descricao_situacao_cadastral", "N/A")
    telefone = data.get("ddd_telefone_1")
    porte = data.get("porte")
    cnae = data.get("cnae_fiscal_descricao", "N/A")

    funcionarios = estimar_funcionarios(porte)

    if telefone:
        telefone = f"({telefone[:2]}) {telefone[2:]}" if len(telefone) > 2 else telefone
    else:
        telefone = "Não informado"

    return (
        f"🏢 {nome}\n"
        f"🏷️ {fantasia}\n"
        f"📍 {cidade} - {uf}\n"
        f"📊 {situacao}\n"
        f"🏭 Ramo: {cnae}\n"
        f"👥 Funcionários: {funcionarios}\n"
        f"📞 {telefone}\n"
    )

# 🏙️ Buscar empresas no banco e remover após uso
def buscar_empresas_por_cidade(cidade, limite=10):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cnpj FROM empresas
        WHERE municipio = ?
        LIMIT ?
    """, (cidade, limite))

    resultados = cursor.fetchall()

    if not resultados:
        conn.close()
        return []

    cnpjs = [row[0] for row in resultados]

    # 🔥 Remover os CNPJs usados
    cursor.executemany("DELETE FROM empresas WHERE cnpj = ?", [(c,) for c in cnpjs])

    conn.commit()
    conn.close()

    return cnpjs

# 📌 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    logger.info(f"/start | user_id={user}")

    if not usuario_autorizado(user):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return

    await update.message.reply_text(
        "🤖 Bot CNPJ Online!\n\n"
        "Use:\n"
        "/cnpj 00000000000100\n"
        "/cidade santo andre"
    )

# 📌 /cnpj
async def cnpj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if not usuario_autorizado(user):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return

    if not context.args:
        await update.message.reply_text("Use: /cnpj 00000000000100")
        return

    cnpj_num = context.args[0]
    logger.info(f"/cnpj {cnpj_num} | user_id={user}")

    data = buscar_cnpj(cnpj_num)

    if not data:
        await update.message.reply_text("❌ CNPJ não encontrado.")
        return

    await update.message.reply_text(formatar_empresa(data))

# 📌 /cidade
async def cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if not usuario_autorizado(user):
        await update.message.reply_text("⛔ Você não está autorizado a usar este bot.")
        return

    if not context.args:
        await update.message.reply_text("Use: /cidade santo andre")
        return

    cidade_original = " ".join(context.args)
    cidade_api = normalizar_texto(cidade_original)

    logger.info(f"/cidade {cidade_original} | normalizado={cidade_api} | user_id={user}")

    cnpjs = buscar_empresas_por_cidade(cidade_api, limite=10)

    if not cnpjs:
        await update.message.reply_text("⚠️ Não há mais empresas disponíveis para essa cidade.")
        return

    resposta = f"🏙️ Empresas em {cidade_original.title()}:\n\n"

    for cnpj in cnpjs:
        data = buscar_cnpj(cnpj)
        if data:
            resposta += formatar_empresa(data)
            resposta += "-----------------\n"

    await update.message.reply_text(resposta)

# 🚀 Inicialização
logger.info("Iniciando bot...")

if not TOKEN:
    raise ValueError("TOKEN não configurado")

init_db()

try:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cnpj", cnpj))
    app.add_handler(CommandHandler("cidade", cidade))

    logger.info("Bot iniciado com sucesso.")

    app.run_polling()

except Conflict:
    logger.warning("Outra instância do bot está rodando.")

except Exception as e:
    logger.exception(f"Erro fatal: {e}")

