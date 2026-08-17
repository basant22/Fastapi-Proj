import sqlite3
from sqlalchemy.orm import sessionmaker,declarative_base
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
load_dotenv()
conn_str = os.getenv("CONN_STR") 

base = declarative_base()
engine = create_engine(conn_str, connect_args={"check_same_thread":False})
sessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
