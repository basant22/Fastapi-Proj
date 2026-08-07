from pydantic import BaseModel
import hashlib
import base64
import bcrypt

class LoginAuth(BaseModel):
    username:str
    password:str
    
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a stored bcrypt hash."""
        digest = hashlib.sha256(plain_password.encode('utf-8')).digest()
        prepared_pwd = base64.b64encode(digest)
        
        return bcrypt.checkpw(prepared_pwd, hashed_password.encode('utf-8'))