import json
from bs4 import BeautifulSoup
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session
from src.database import session_opener, SessionLocal
from src.news.models import NewsArticle, user_news_association_table

import requests
from urllib.parse import quote
from fastapi import Depends
from openai import OpenAI
from src.crawler.udn_crawler import UDNCrawler
from src.llm_client.openai_client import OpenAIClient

crawler = UDNCrawler()

def add_news_to_database(news_data):
    """
    將新聞資料新增到資料庫中
    :param news_data: 包含新聞資訊的字典
    :return:
    """
    session = Session() 
    crawler.save(news_data,session)

#def get_news_article_by_id(article_id: int, db: Session = Depends(session_opener)):
#  return db.query(NewsArticle).filter(NewsArticle.id == article_id).first()

def fetch_news_info_by_search_term(search_term, is_initial=False):
    """
    根據指定的搜尋詞來獲取新聞資訊
    
    :param search_term: 用於搜尋的關鍵字
    :param is_initial: 布林值，若為 True 則會抓取多頁新聞數據
    :return: 包含新聞資訊的列表
    """
    all_news_data = []
    # iterate pages to get more news data, not actually get all news data
    if is_initial:
        all_news_data = crawler.get_headline(search_term,(1,10))
    else:
        # 使用 _create_search_params 方法生成参数
        params = crawler._create_search_params(page=1, search_term=search_term)
        response = crawler._perform_request(params=params)
        all_news_data = response.json()["lists"]
    return all_news_data

def get_article_upvote_details(article_id, uid, db):
    """
    根據新聞 ID 獲取點讚數和用戶點讚狀態
    :param article_id: 新聞 ID
    :param user_id: 使用者 ID
    :param db: 資料庫會話
    :return: 點讚數和是否已被用戶點讚的布林值
    """
    # 計算該新聞的總點讚數
    count = (
        db.query(user_news_association_table)
        .filter_by(news_articles_id=article_id)
        .count()
    )
     # 檢查該用戶是否已點讚該新聞
    voted = False
    if uid:
        voted = (
                db.query(user_news_association_table)
                .filter_by(news_articles_id=article_id, user_id=uid)
                .first()
                is not None
        )
    return count, voted


def toggle_news_upvoted_status(n_id, u_id, db):
    existing_upvote = db.execute(
        select(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == n_id,
            user_news_association_table.c.user_id == u_id,
        )
    ).scalar()


    if existing_upvote:
        delete_stmt = delete(user_news_association_table).where(
            user_news_association_table.c.news_articles_id == n_id,
            user_news_association_table.c.user_id == u_id,
        )
        db.execute(delete_stmt)
        db.commit()
        return "Upvote removed"
    else:
        insert_stmt = insert(user_news_association_table).values(
            news_articles_id=n_id, user_id=u_id
        )
        db.execute(insert_stmt)
        db.commit()
        return "Article upvoted"
    
def get_news_article(llm_client: OpenAIClient, crawler: UDNCrawler, is_initial: bool = False):
    """
    獲取並處理與民生用品價格變化相關的新聞資訊。

    :param llm_client: LLM 客戶端實例，用於與 OpenAI 交互。
    :param crawler: 爬蟲實例，用於抓取新聞內容。
    :param is_initial: 是否抓取多頁數據（默認為 False）。
    :return: None
    """
    # 抓取新聞資料
    news_data = fetch_news_info_by_search_term("價格", is_initial=is_initial) #list

    for news in news_data:
        title = news["title"]

        # 1. 使用 LLM 判斷新聞與主題的關聯度
        relevance = llm_client.evaluate_relevance(title, "民生用品的價格變化")
        if relevance == "high":
            # 2. 抓取並解析詳細新聞內容
            detailed_news = crawler.parse(news["titleLink"]) #News

            # 3. 使用 LLM 生成新聞摘要
            summary_data = llm_client.generate_summary(" ".join(detailed_news["content"]))
        

            # 4. 更新新聞詳細內容並存入資料庫
            detailed_news["summary"] = summary_data.get("影響", "")
            detailed_news["reason"] = summary_data.get("原因", "")
            add_news_to_database(detailed_news)


def get_news_exists_status(news_id: int, db: Session) -> bool:
    """
    檢查指定的新聞 ID 是否存在於資料庫中。
    :param news_id: 新聞 ID
    :param db: 資料庫會話
    :return: 如果新聞存在返回 True，否則返回 False
    """
    return db.query(NewsArticle).filter_by(id=news_id).first() is not None