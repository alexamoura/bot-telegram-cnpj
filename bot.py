import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🔐 TOKEN
TOKEN = os.getenv("TOKEN")

# 🧾 Configuração de LOG
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# 📊 Estimar funcionários por porte
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

# 🔎 Consulta por CNPJ
def buscar_cnpj(cnpj):
    logger.info(f"Consultando CNPJ: {cnpj}")

    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            logger.warning(f"Erro ao consultar CNPJ {cnpj} | Status: {r.status_code}")
            return None

        return r.json()

    except Exception as e:
        logger.error(f"Exceção ao consultar CNPJ {cnpj} | Erro: {e}")
        return None

# 🧾 Formatar dados da empresa
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

# 🔎 Buscar empresas por cidade
def buscar_por_cidade(cidade):
    logger.info(f"Consultando cidade: {cidade}")

    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1?municipio={cidade}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            logger.warning(f"Erro ao buscar empresas na cidade {cidade} | Status: {r.status_code}")
            return "❌ Erro ao buscar empresas."

        data = r.json()

        if not data:
            logger.info(f"Nenhuma empresa encontrada na cidade: {cidade}")
            return "⚠️ Nenhuma empresa encontrada."

        resposta = f"🏙️ Empresas em {cidade.title()}:\n\n"

        contador = 0

        for empresa in data:
            if contador == 10:
                break

            cnpj = empresa.get("cnpj")
            detalhes = buscar_cnpj(cnpj)

            if detalhes:
                resposta += formatar_empresa(detalhes)
                resposta += "-----------------\n"
                contador += 1

        logger.info(f"Retornadas {contador} empresas para cidade: {cidade}")
        return resposta

    except Exception as e:
        logger.error(f"Exceção ao buscar cidade {cidade} | Erro: {e}")
        return "❌ Erro interno ao buscar empresas."

# 📌 Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    logger.info(f"/start usado por user_id={user}")

    await update.message.reply_text(
        "🤖 Bot CNPJ Online!\n\n"
        "Use:\n"
        "/cnpj 00000000000100\n"
        "/cidade santo andre"
    )

# 📌 Comando /cnpj
async def cnpj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if not context.args:
        logger.warning(f"/cnpj sem argumento | user_id={user}")
        await update.message.reply_text("Use: /cnpj 00000000000100")
        return

    cnpj_num = context.args[0]
    logger.info(f"/cnpj {cnpj_num} | user_id={user}")

    data = buscar_cnpj(cnpj_num)

    if not data:
        await update.message.reply_text("❌ CNPJ não encontrado.")
        return

    await update.message.reply_text(formatar_empresa(data))

# 📌 Comando /cidade
async def cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if not context.args:
        logger.warning(f"/cidade sem argumento | user_id={user}")
        await update.message.reply_text("Use: /cidade santo andre")
        return

    cidade_nome = " ".join(context.args)
    logger.info(f"/cidade {cidade_nome} | user_id={user}")

    resultado = buscar_por_cidade(cidade_nome)
    await update.message.reply_text(resultado)

# 🚀 Inicializar bot
logger.info("Iniciando bot...")

if not TOKEN:
    logger.error("TOKEN não encontrado! Verifique a variável de ambiente no Render.")
    raise ValueError("TOKEN não configurado")

try:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cnpj", cnpj))
    app.add_handler(CommandHandler("cidade", cidade))

    logger.info("Bot iniciado com sucesso. Aguardando comandos...")

    app.run_polling()

except Exception as e:
    logger.exception(f"Erro fatal ao iniciar o bot: {e}")
