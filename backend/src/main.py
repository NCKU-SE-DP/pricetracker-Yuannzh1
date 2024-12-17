
import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import SessionLocal
from src.news.models import NewsArticle
from src.news.dependencies import get_news_article
from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.news.router import router as news_router
from src.price.router import router as price_router
from src.news.dependencies import fetch_news_info_by_search_term
from src.crawler.udn_crawler import UDNCrawler
from src.llm_client.openai_client import OpenAIClient

app = FastAPI()
bgs = BackgroundScheduler()

llm_client = OpenAIClient()
crawler = UDNCrawler()
@app.on_event("startup")
def start_scheduler():
    db = SessionLocal()
    if db.query(NewsArticle).count() == 0:
        # should change into simple factory pattern
        fetch_news_info_by_search_term("價格")
    db.close()
    bgs.add_job(get_news_article, "interval", minutes=100, kwargs={"llm_client": llm_client, "crawler": crawler})
    bgs.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    bgs.shutdown()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(news_router)
app.include_router(price_router)
