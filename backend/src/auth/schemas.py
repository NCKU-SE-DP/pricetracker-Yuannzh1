from pydantic import BaseModel

class UserAuthSchema(BaseModel):
    username: str = "Apple"
    password: str = "Apple"

class Token(BaseModel):
    access_token: str
    token_type: str
