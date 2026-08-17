from database import sessionLocal
from sqlalchemy.orm import Session
from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
from register import User
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import dbmodel
from todo import Todo
from config import settings
from routers.auth import oauth2_scheme
from jose import jwt,JWTError
todorouter = APIRouter(prefix='/v1/todo/api', tags=['todo'])
SECRET_KEY = settings.SECRET_KEY  
ALGORITHM =  settings.ALGORITHM
def my_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close() 
        

# verify auth2 token
def verify_OAuth_token(token:str= Depends(oauth2_scheme)):  
    try:
        payload = jwt.decode(token,SECRET_KEY ,algorithms=[ALGORITHM])
        username = payload.get('sub')
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            print("User Name",username)
        return username 
    except jwt.JWTError:
         raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        
        
@todorouter.get("/todos") 
def get_todo(
    request:Request,
             db:Session = Depends(my_db),
             user = Depends(verify_OAuth_token),
             ):
    try:
             
            login_userid = request.state.user_id  
            # login_user = db.query(dbmodel.User).filter(dbmodel.User.email == user).first()
            todos = db.query(dbmodel.Todo).filter(dbmodel.Todo.user_id == login_userid).all()
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
    except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail="No data found"
                )           
@todorouter.post('/todo')
def create(todo:Todo,db:Session = Depends(my_db), user = Depends(verify_OAuth_token) ):
    try:
        if todo is None:
            raise HTTPException(
                status_code=404,
                detail="No toto request found"
            )  
            
        else:
            login_user = db.query(dbmodel.User).filter(dbmodel.User.email == user).first()
            new_todo = dbmodel.Todo(title=todo.title,completed=todo.completed,user_id=login_user.id)
            db.add(new_todo)
            db.commit()
            return {
                "message":"Todo added successfully"
            }
    except Exception as e:
              raise HTTPException(
                status_code=400,
                detail="No data found"
            )    
    
@todorouter.put("/todo/{todo_id}")
def update(
    todo_id:int,
    todo:Todo,
    db:Session = Depends(my_db),
    user = Depends(verify_OAuth_token)
    ):
    try:
        if user is None:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid user authentication"
            ) 
        print('email', user)   
        login_user = db.query(dbmodel.User).filter(dbmodel.User.email == user).first()
        if login_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {user} not found"
            )
            
        dbtodo =  db.query(dbmodel.Todo).filter(
            (dbmodel.Todo.user_id == login_user.id) and( dbmodel.Todo.id == todo_id) 
            ).first()
      
        if dbtodo is None:
            raise HTTPException(
                status_code=404,
                detail=f"No todo found for this id:{todo_id}"
            )  
           
        else:
            dbtodo.title = todo.title
            dbtodo.completed = todo.completed
            
            db.commit()
            db.refresh(dbtodo)
            
            return{
                "status":"success",
                "message":"Todo updated successfully",
                "data" : dbtodo
            }
    except Exception as e:
        db.rollback()    
        raise HTTPException(
             status_code=400,
             detail= f"failed to update todo: {str(e)}"
         )  

@todorouter.get("/todo/{id}")
def getTodo(id:int,db:Session = Depends(my_db),user:str = Depends(verify_OAuth_token)):
    try:
        if user is None:
            raise HTTPException(
                status_code=404,
                detail=f"No todo found for this id:{id}"
            ) 
        dbtodo = db.query(dbmodel.Todo).filter(dbmodel.Todo.id == id ).first()
        if dbtodo is None:
            raise HTTPException(
                status_code=404,
                deatil=f"No todo found for this id:{id}"
            )  
           
        else:
             return{
                "status":"success",
                "message":"Todo found successfully",
                "data" : dbtodo
            }
              
    except Exception as e:
        db.rollback()    
        raise HTTPException(
             status_code=400,
             detail= f"failed to update todo: {str(e)}"
         )  

@todorouter.delete('/delete/{id}')    
def deletetodo(id:int,db:Session = Depends(my_db),user:str = Depends(verify_OAuth_token)):
    try:
        if user is None:
            raise HTTPException(
                status_code=404,
                detail=f"No todo found for this id:{id}"
            ) 
        dbTodo = db.query(dbmodel.Todo).filter(dbmodel.Todo.id == id).first()
        if dbTodo is None:
             raise HTTPException(
                    status_code=404,
                    deatil="No todo found for this id : {id}"
                )   
            
        else:
            db.delete(dbTodo)
            db.commit()
            return{
                    "status":"success",
                    "message":"Todo deleted successfully",
                }
        
                
    except Exception as e:
        db.rollback()
        raise HTTPException(
             status_code=400,
             detail= f"failed to delete todo{str(e)}"
         )     
        
        