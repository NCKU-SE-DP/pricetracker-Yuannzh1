from pydantic import BaseModel

class UserProfile(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True
