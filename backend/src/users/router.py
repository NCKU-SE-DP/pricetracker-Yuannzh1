from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from src.auth.dependencies import authenticate_user_token, check_user_password_is_correct
from src.users.schemas import UserProfile
from src.auth.models import User
from src.auth.dependencies import authenticate_user, create_access_token, session_opener, pwd_context
from src.auth.schemas import UserAuthSchema, Token

router = APIRouter()

@router.get("/api/v1/users/me", response_model=UserProfile)
def read_users_me(user=Depends(authenticate_user_token)):
    return {"id": user.id, "username": user.username}

@router.post("/api/v1/users/register")
def register_user(user: UserAuthSchema, db: Session = Depends(session_opener)):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/api/v1/users/login")
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(session_opener)
):
    """login"""
    user = check_user_password_is_correct(db, form_data.username, form_data.password)
    access_token = create_access_token(
        data={"sub": str(user.username)}, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}
