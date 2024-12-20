from pydantic import BaseModel

class UserAuthSchema(BaseModel):
    username: str = "Test"
    password: str = "Test"

class Token(BaseModel):
    access_token: str
    token_type: str
