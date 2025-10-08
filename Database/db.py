from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Models.base import Base
from config import DATABASE_URL


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# cria todas as tabelas baseadas nos models
def init__db():
    Base.metadata.create_all(bind=engine)
