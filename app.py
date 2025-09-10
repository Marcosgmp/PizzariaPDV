from Models import Customer, Order, Product
from fastapi import FastAPI
from Database.db import init_db
from routes.orders import router as orders_router

app = FastAPI()
init_db()  # cria todas as tabelas
app.include_router(orders_router)
