from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.database import Base
from src.news.models import user_news_association_table
from src.auth.config import USERNAME_LENGTH, PASSWORD_LENGTH
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(USERNAME_LENGTH), unique=True, nullable=False)
    hashed_password = Column(String(PASSWORD_LENGTH), nullable=False)
    upvoted_news = relationship(
        "NewsArticle",
        secondary=user_news_association_table,
        back_populates="upvoted_by_users",
    )
