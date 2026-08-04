from fastapi import FastAPI,Depends,HTTPException
from database import session,engine
from sqlalchemy.orm import Session
import dbmodel
from dbmodel import Todo
from todo import Todo

app = FastAPI()
dbmodel.Base.metadata.create_all(bind=engine)

def my_db():
    db = session()
    try:
        yield db
    finally:
        db.close()    
        

@app.get("/todos") 
def get_todo(db:Session = Depends(my_db)):
    todos = db.query(dbmodel.Todo).all()           
    if len(todos) > 0:
        return {
            "message": "fetched all todos successfully",
            "todos":todos
        }
    else:
          return {
            "message": "No todos available",
            "todos":[]
        }  
@app.post('/todo')
def create(todo:Todo,db:Session = Depends(my_db) ):
    if todo:
        
        db.add(dbmodel.Todo(**todo.model_dump()))
        db.commit()
        return {
            "message":"Todo added successfully"
        }
    else:
         raise HTTPException(
             status_code=404,
             details="No data found"
         )   
    
