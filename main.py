from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from ifood.ifood_controllers import merchant, auth, orders, event, review, shipping


app = FastAPI(
    title="Pizzaria PDV API",
    description="API da Pizzaria com integração iFood",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)   

app.include_router(merchant.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(event.router)
app.include_router(review.router)
app.include_router(shipping.router)     


@app.get("/")
def root():
    return {"message": "API Pizzaria PDV está funcionando!"}
