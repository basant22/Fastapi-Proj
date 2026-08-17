import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY")  # Use os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM")
    CONN_STR = os.getenv("CONN_STR")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR")
    
settings = Settings()    