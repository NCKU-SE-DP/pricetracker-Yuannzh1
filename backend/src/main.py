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
from src.crawler.udn_crawler import UDNCrawler

sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()
bgs = BackgroundScheduler()
crawler = UDNCrawler()

@app.on_event("startup")
def start_scheduler():
    db = SessionLocal()
    if db.query(NewsArticle).count() == 0:
        # should change into simple factory pattern
        crawler.startup("價格")
    db.close()
    bgs.add_job(get_news_article, "interval", minutes=100)
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
