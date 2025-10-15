from dotenv import load_dotenv
import os

# Carrega variáveis do .env
load_dotenv()

# Configurações do Banco de Dados
DATABASE_URL = "postgresql://postgres:2105mp@localhost:5432/Pizzariapdv"

# Configurações do iFood
IFOOD_API_URL = os.getenv("IFOOD_API_URL", "https://merchant-api.ifood.com.br")
IFOOD_CLIENT_ID = os.getenv("IFOOD_CLIENT_ID")
IFOOD_CLIENT_SECRET = os.getenv("IFOOD_CLIENT_SECRET")
IFOOD_MERCHANT_ID = os.getenv("IFOOD_MERCHANT_ID")
#https://merchant-api.ifood.com.br/order/v1.0 

# WhatsApp API 
# WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY")

# Configurações de emissão de nota fiscal 
# NFE_API_URL = os.getenv("NFE_API_URL")

# Configurações gerais do app
# APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")