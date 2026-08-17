from database import sessionLocal
from sqlalchemy.orm import Session
from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from register import User
from jose import jwt,JWTError
import hashlib
import base64
import bcrypt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import dbmodel
from config import settings
from register import User,UserResponse,RequestRefreshToken
from jose import jwt,JWTError

SECRET_KEY = settings.SECRET_KEY  
ALGORITHM =  settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

authrouter = APIRouter(prefix='/v1/auth/api', tags=['auth'])
def my_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()    

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/api/loginauth")
# password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# hash password
def hash_password(password:str):
    return pwd_context.hash(password)


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



@authrouter.post("/register")  
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
@authrouter.post('/loginauth')
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
@authrouter.post('/refresh')
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
