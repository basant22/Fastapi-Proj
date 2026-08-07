from pydantic import BaseModel,model_validator

class User(BaseModel):
    name:str
    email:str
    mobileno:str
    password:str
    confirmpassword:str
    
    # Automatically validate password matching before the endpoint runs
    @model_validator(mode="after")
    def verify_passwords_match(self):
        if self.password != self.confirmpassword:
            raise ValueError("Password and confirm password do not match")
        return self
    
class UserResponse(BaseModel): 
    name:str
    email:str
    mobileno:str   
    
    