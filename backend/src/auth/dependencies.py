from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt
from src.auth.models import User
from src.database import session_opener
from passlib.context import CryptContext
from datetime import datetime, timedelta
 
SECRET_KEY = "1892dhianiandowqd0n"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def verify_hashed_password(p1, p2):
    return pwd_context.verify(p1, p2)

def check_user_password_is_correct(db, username, password):
    user = db.query(User).filter(User.username == username).first()
    if not verify_hashed_password(password, user.hashed_password):
        return False
    return user

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user_token(
    token = Depends(oauth2_scheme),
    db = Depends(session_opener)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return db.query(User).filter(User.username == payload.get("sub")).first()
