from sqlalchemy import Column,Integer,Float,String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Todo(Base):
    __tablename__ = "totos"
    
    id=Column(Integer, primary_key=True, index=True)
    title=Column(String)
    completed=Column(String)