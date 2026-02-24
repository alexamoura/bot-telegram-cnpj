import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

# 🔎 Consulta por CNPJ
def buscar_cnpj(cnpj):
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    return r.json()

# 🧾 Formatar dados da empresa
def formatar_empresa(data):
    nome = data.get("razao_social", "N/A")
    fantasia = data.get("nome_fantasia", "N/A")
    cidade = data.get("municipio", "N/A")
    uf = data.get("uf", "N/A")
    situacao = data.get("descricao_situacao_cadastral", "N/A")
    telefone = data.get("ddd_telefone_1")

    if telefone:
        telefone = f"({telefone[:2]}) {telefone[2:]}" if len(telefone) > 2 else telefone
    else:
        telefone = "Não informado"

    return (
        f"🏢 {nome}\n"
        f"🏷️ {fantasia}\n"
        f"📍 {cidade} - {uf}\n"
        f"📊 {situacao}\n"
        f"📞 {telefone}\n"
    )

# 🔎 Buscar empresas por cidade com telefone
def buscar_por_cidade(cidade):
    url = f"https://brasilapi.com.br/api/cnpj/v1?municipio={cidade}"
    r = requests.get(url)

    if r.status_code != 200:
        return "❌ Erro ao buscar empresas."

    data = r.json()

    if not data:
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

    return resposta

# 📌 Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot CNPJ Online!\n\n"
        "Use:\n"
        "/cnpj 00000000000100\n"
        "/cidade santo andre"
    )

# 📌 Comando /cnpj
async def cnpj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /cnpj 00000000000100")
        return

    data = buscar_cnpj(context.args[0])

    if not data:
        await update.message.reply_text("❌ CNPJ não encontrado.")
        return

    await update.message.reply_text(formatar_empresa(data))

# 📌 Comando /cidade
async def cidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /cidade santo andre")
        return

    cidade_nome = " ".join(context.args)
    resultado = buscar_por_cidade(cidade_nome)
    await update.message.reply_text(resultado)

# 🚀 Inicializar bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cnpj", cnpj))
app.add_handler(CommandHandler("cidade", cidade))

app.run_polling()