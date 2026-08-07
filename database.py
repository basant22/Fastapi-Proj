import sqlite3
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
load_dotenv()
conn_str = os.getenv("CONN_STR") 


engine = create_engine(conn_str, connect_args={"check_same_thread":False})
session = sessionmaker(bind=engine, autoflush=False, autocommit=False)