from fastapi import FastAPI,Depends,HTTPException,Header,UploadFile,File,Request,status,APIRouter
import shutil
import os
from config import settings
imagerouter = APIRouter(prefix='/v1/image/api', tags=['images'])


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}
FILEURL = "http://127.0.0.1:8000/files/"

if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)

#Upload file api
@imagerouter.post('/upload') 
def upload_file(file:UploadFile = File(...)):
    filename = file.filename
    
    file_path = os.path.join(settings.UPLOAD_DIR,filename)
    
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
@imagerouter.get("/file/{filename}")
def get_file(filename:str):
    file_path = os.path.join(settings.UPLOAD_DIR,filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404,detail="FFile not found")
    return{
        "file_url":f"{FILEURL}{filename}"
    }            





