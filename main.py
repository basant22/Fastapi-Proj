from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
import os
from fastapi.staticfiles import StaticFiles
import shutil
from database import session,engine
from sqlalchemy.orm import Session
import dbmodel
from todo import Todo
from register import User,UserResponse,RequestRefreshToken
from jose import jwt,JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from passlib.context import CryptContext
from loginmodel import LoginAuth
import hashlib
import base64
import bcrypt
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from bs4 import BeautifulSoup
import requests
import time
# rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import uvicorn
from database import session
FILEURL = "http://127.0.0.1:8000/files/"
# Define allowed extensions and MIME types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}
app = FastAPI()
dbmodel.Base.metadata.create_all(bind=engine)
# Version 1 routes
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.include_router(v1_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Set to False when using wildcard "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    
# Static file setup
app.mount("/files",StaticFiles(directory=UPLOAD_DIR),name="files")     
def my_db():
    db = session()
    try:
        yield db
    finally:
        db.close() 
        
Cache_data = []
last_fetch = 0        
# JWT Config
SECRET_KEY = settings.SECRET_KEY  
ALGORITHM =  settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_user_from_request(request: Request):
    """Get user from request.state"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    return user
def get_password_hash(password: str) -> str:
    """Pre-hash with SHA-256 to bypass the 72-byte limit, then hash with bcrypt."""
    # Step 1: Pre-hash with SHA-256 (produces 32 raw bytes)
    digest = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Step 2: Base64 encode to get a clean 44-character ASCII string
    prepared_pwd = base64.b64encode(digest)
    
    # Step 3: Hash with native bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(prepared_pwd, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    digest = hashlib.sha256(plain_password.encode('utf-8')).digest()
    prepared_pwd = base64.b64encode(digest)
    
    return bcrypt.checkpw(prepared_pwd, hashed_password.encode('utf-8'))

# Rate limiter logic
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

#Error handle
@app.exception_handler(RateLimitExceeded)
def rate_limiter_handler(request:Request,exc:RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "message":"To many requests"
        }
    )


oath2_schema = OAuth2PasswordBearer(tokenUrl="api/v1/loginauth")

# hash password
def hash_password(password:str):
    return pwd_context.hash(password)
# verify password
# def verify_password(plain_password,hashed_password):
#     return pwd_context.verify(plain_password,hashed_password)
def authenticate_user(username:str,password:str):
    if username != "admin" and password != "1234":
        raise HTTPException(
                status_code=401,
                detail=f"User:{username} not found found"
            ) 
    else:
        return{
            "sub":username,
             "role":"admin"
        }
def create_token(data:dict):
        to_encode = data.copy()
        expiry = datetime.now() + timedelta(minutes=30)
        to_encode.update({
                "exp" : expiry,
                "type":"access"
            })
        token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
        return token
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)    
# verify auth2 token
def verify_OAuth_token(token:str= Depends(oath2_schema)):  
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
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
        
        
# FIX 2: Better error handling and debugging
def verify_token(token: str = Header(...)):
    try:
        print(f"Raw token received: {token}")
        print(f"Token length: {len(token)}")
        
        # Handle "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
            print(f"Token after removing Bearer prefix: {token[:20]}...")
        
        # Try to decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Token decoded successfully: {payload}")
        return payload
        
    except jwt.ExpiredSignatureError:
        print("Token expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
# @app.middleware('http') 
# Middleware 1: Logging

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"📝 [Log Middleware] - Before request: {request.method} {request.url.path}")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"📝 [Log Middleware] - After request: {process_time:.3f}s")
    
    return response  

@app.middleware('http')     
async def auth_middleware(
    request: Request, call_next,
    
    ):  
    print('url_path=', request.url.path)
          
    # path = request.url.path.split('/')[2]
    # MUST return the response
    public_paths = [ '/', '/api/v1/loginauth', '/api/v1/register' ,'/docs', '/docs/', '/openapi.json',
        '/redoc',
        '/redoc/','/static',
        '/static/',]
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Not authenticated",
                "error": "Missing Authorization header"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    # Validate token format
    if not auth_header.startswith('Bearer '):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Invalid authentication scheme",
                "error": "Use Bearer token"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(' ')[1]   
    # token = auth_header
    print('token',token)
    try:
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise JWTError("Invalid token payload")
        
        # Check token type (optional)
        token_type = payload.get("type", "access")
        if token_type != "access":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token type. Use access token"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Get user from database
        db = session()
        user = db.query(dbmodel.User).filter(dbmodel.User.email == username).first()
        if user is None:
            raise JWTError("User not found")
        
        # if user.disabled:
        #     return JSONResponse(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         content={"detail": "User account disabled"}
        #     )
        
        # Store user in request state
        request.state.user_id = user.id
        request.state.username = username
        # request.state.token = token
        # request.state.token_payload = payload
        response = await call_next(request)
        return response
        
    except JWTError as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(e) or "Invalid authentication credentials"},
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Authentication error: {str(e)}"}
        ) 
    finally:
        db.close()    
          



#check rate limiter
@app.get("/ratelimiter") 
@limiter.limit("5/minute")      
def check_limit(request:Request):
    return{
        "message":"Success"
    } 
    

            
#Upload file api
@v1_router.post('/upload') 
def upload_file(file:UploadFile = File(...)):
    filename = file.filename
    
    file_path = os.path.join(UPLOAD_DIR,filename)
    
    if not filename:
        raise HTTPException( status_code=400,detail="File not found") 
    # 2. Extract file extension
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    # 3. Validate both extension and MIME type
    if file_ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)
        return{
            "message":"File uploaded successfully",
            "filename":filename,
            "file_url":f"{FILEURL}{filename}"
        }  
# get file
@v1_router.get("/file/{filename}")
def get_file(filename:str):
    file_path = os.path.join(UPLOAD_DIR,filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404,detail="FFile not found")
    return{
        "file_url":f"{FILEURL}{filename}"
    }            
#Register user
@v1_router.post("/register")  
def register_user(user:User, db:Session = Depends(my_db)):
    try:
        if user is None:
            raise HTTPException(
                status_code=404,
                detail="No user data received"
            )
        else:
            existing_user = db.query(dbmodel.User).filter(dbmodel.User.email == user.email).first()
            if existing_user:
                raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
                                    )
            existing_user = db.query(dbmodel.User).filter(dbmodel.User.mobileno == user.mobileno).first()
            if existing_user:
                raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile Number is already registered"
                                    )
                    
            hashed_pwd = get_password_hash(user.password)
            db_user = dbmodel.User(
                        name=user.name,
                        email=user.email,
                        mobileno=user.mobileno,
                        password=hashed_pwd
                        )
            create_user = UserResponse(
                        name=user.name,
                        email=user.email,
                        mobileno=user.mobileno
                        )
            db.add(db_user)   
            db.commit()
            db.refresh(db_user)
            return{
                        "status":'success',
                        "message":"User created successfully",
                        "User":create_user
                    }
              
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail = f" found some error:{str(e)} while refister user"
        )   
# Oauth2 login
@v1_router.post('/loginauth')
def login_auth(request_form:OAuth2PasswordRequestForm = Depends(),db:Session = Depends(my_db)):
        # hash_pass = get_password_hash('1234')
        user = db.query(dbmodel.User).filter(dbmodel.User.email == request_form.username).first()
       
        if not user or not verify_password(request_form.password,user.password):
            raise HTTPException(
            status_code=401,
            detail="Invalid user name or password"
                                )
        access_token = create_token({"sub":request_form.username})  
        refresh_token = create_refresh_token({"sub":request_form.username})
        return{
            "access_token":access_token,
            "refresh_token":refresh_token,
            "token_type":"bearer"
        }     
#Refresh token
@v1_router.post('/refresh')
def refresh_token(token:RequestRefreshToken):
    try:
        payload = jwt.decode(token.refreshtoken,SECRET_KEY,algorithms=[ALGORITHM])
        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=401,
                detail="Inalid token type"
            )
        username:str = payload.get('sub')
        if username is None:
            raise HTTPException(
                status_code=401,
                detail='Invaid user'
            )
        access_token = create_token({"sub":username})  
        refresh_token = create_refresh_token({"sub":username})
        return{
            "access_token":access_token,
            "refresh_token":refresh_token,
            "token_type":"bearer"
        }        
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Error while generation of refresh token"
        ) 
    
    
             
@v1_router.post('/login')
def login(user:LoginAuth):
    auth_user = authenticate_user(username=user.username,password=user.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    else:
       token = create_token(auth_user)
       return{
           "useremail":user.username,
            "access_token":token
       }
       
@v1_router.get('/dashboard')
def dashboard(user = Depends(verify_token)):
    return {
        "message":"Secure data accessed",
        "user":user
    }
@v1_router.get('/protected')
def dashboard(username = Depends(verify_OAuth_token)):
    return {
        "message":f"hello {username} , You have successfully accessed protected path",
        "user":username
    }         
   
        

@v1_router.get("/todos") 
def get_todo(
    request:Request,
             db:Session = Depends(my_db),
             user = Depends(verify_OAuth_token),
             ):
    print('--------------------')   
    try:
            print('--',30)   
            login_userid = request.state.user_id  
            print('myuser',login_userid)   
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
@v1_router.post('/todo')
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
    
@v1_router.put("/todo/{todo_id}")
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

@v1_router.get("/todo/{id}")
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

@v1_router.delete('/delete/{id}')    
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

# web crawling

@v1_router.get("/news")
def get_news(page:int=1,limit:int=5):
    global Cache_data,time_left
    url = "https://news.ycombinator.com/"   
    response = requests.get(url)
    soup = BeautifulSoup(response.text,"html.parser")
    title=[]
    
   
    for item in soup.find_all('span', class_="titleline"):
            title.append(item.text)
        
    
       
    #pagination logic
    start = (page-1)*limit
    end = start+limit
    if len(title) > 5:
       
        return{
            "page":page,
            "limit":limit,
            "total":len(title),
            "data":title[start:end]
        }    
        
    else:
        return{
            "page":page,
            "limit":limit,
            "total":len(title),
            "data":title[start:end]
        }  
  
@v1_router.get("/cachednews")
def get_cached_news(page:int=1,limit:int=5):
    global Cache_data,last_fetch
    url = "https://news.ycombinator.com/"   
    response = requests.get(url)
    soup = BeautifulSoup(response.text,"html.parser")
    title=[]
    start = time.time()
    if time.time() - last_fetch > 60:
       
        print("Fresh start")
        Cache_data=[
          item.text for item in soup.find_all('span', class_="titleline")
        ]
    
       
        last_fetch = time.time()
        time_taken = round(last_fetch-start,4) 
        print("time taken",time_taken)
        return{
            "time taken":time_taken,
            "data":Cache_data
        }    
       
    else:
        print("cached start")
        end = time.time()
        time_taken = round(end-start,4) 
        print("time taken",time_taken)
        return{
            "time taken":time_taken,
            "data":Cache_data
        }    


# if __name__ == "__main__":
#     uvicorn.run('main:app', host="127.0.0.1", port=8000, reload=True)
        