from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import timedelta
from src.auth.dependencies import authenticate_user_token
from src.users.schemas import UserProfile


router = APIRouter()

@router.get("/api/v1/users/me", response_model=UserProfile)
def read_users_me(user=Depends(authenticate_user_token)):
    return {"id": user.id, "username": user.username}

