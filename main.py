# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os controllers (rotas)
from ifood.ifood_controllers import merchant, auth

# Cria a instância principal da aplicação
app = FastAPI(
    title="Pizzaria PDV API",
    description="API da Pizzaria com integração iFood",
    version="1.0.0"
)

# Configura CORS (permite o frontend se conectar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pode restringir a origem do seu frontend aqui
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas (controllers)
app.include_router(merchant.router)
app.include_router(auth.router)


# Rota raiz (teste rápido)
@app.get("/")
def root():
    return {"message": "API Pizzaria PDV está funcionando!"}
