from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base

# URL do PostgreSQL
DATABASE_URL = "postgresql://postgres:2105mp@localhost:5432/Pizzariapdv"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# cria todas as tabelas baseadas nos models
def init__db():
    Base.metadata.create_all(bind=engine)
