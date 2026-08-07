from sqlalchemy import Column,Integer,Float,String,ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Todo(Base):
    __tablename__ = "totos"
    
    id=Column(Integer, primary_key=True, index=True,autoincrement=True)
    title=Column(String)
    completed=Column(String)
    user_id=Column(Integer,ForeignKey('users.id'))
    owner = relationship("User",back_populates='todos')

class User(Base):
    __tablename__ = "users"
    
    id=Column(Integer, primary_key=True, index=True,autoincrement=True)
    name=Column(String)
    email=Column(String)
    mobileno=Column(String)
    password=Column(String)
    # One-to-Many relationship with Todo
    todos = relationship("Todo", back_populates="owner")    