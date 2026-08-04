import sqlite3
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

conn_str = "sqlite:///./fast.db"

engine = create_engine(conn_str, connect_args={"check_same_thread":False})
session = sessionmaker(bind=engine, autoflush=False, autocommit=False)