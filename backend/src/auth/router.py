from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.auth.models import User
from src.auth.dependencies import authenticate_user, create_access_token, session_opener, pwd_context
from src.auth.schemas import UserAuthSchema, Token
from datetime import timedelta
from src.auth.config import TOKEN_EXPIRE_MINUTES
router = APIRouter()

@router.post("/api/v1/auth/register")

def register_user(user: UserAuthSchema, db: Session = Depends(session_opener)):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/api/v1/auth/login", response_model=Token)

def login(user: UserAuthSchema, db: Session = Depends(session_opener)):
    db_user = authenticate_user(db, user.username, user.password)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}
