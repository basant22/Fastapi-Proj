from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
from fastapi.staticfiles import StaticFiles
from database import sessionLocal,engine
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt,JWTError
import time
import dbmodel
# rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import uvicorn
from config import settings
from routers.auth import authrouter
from routers.todos import todorouter
from routers.images import imagerouter
from routers.webapi import webrouter

# Define allowed extensions and MIME types

app = FastAPI()
dbmodel.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Set to False when using wildcard "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/files",StaticFiles(directory=settings.UPLOAD_DIR),name="files") 
# Version 1 routes    
app.include_router(authrouter)
app.include_router(todorouter)
app.include_router(imagerouter)
app.include_router(webrouter)

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
          
    public_paths = [ '/', '/v1/auth/api/loginauth', '/v1/auth/api/register' ,'/docs', '/docs/', '/openapi.json',
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
    # print('token',token)
    db = sessionLocal()
    try:
        # Decode and verify token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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
          
@app.get("/")
def root():
    return {"message": "API running smoothly"}


#check rate limiter
@app.get("/ratelimiter") 
@limiter.limit("5/minute")      
def check_limit(request:Request):
    return{
        "message":"Success"
    } 
    

if __name__ == "__main__":
    uvicorn.run('main:app', host="127.0.0.1", port=8000, reload=True)
        