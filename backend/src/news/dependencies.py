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

def add_news_to_database(news_data):
    """
    將新聞資料新增到資料庫中
    :param news_data: 包含新聞資訊的字典
    :return:
    """
    session = Session() 
    session.add(NewsArticle(
        url=news_data["url"],
        title=news_data["title"],
        time=news_data["time"],
        content=" ".join(news_data["content"]),  # 將內容list轉換為字串
        summary=news_data["summary"],
        reason=news_data["reason"],
    ))
    session.commit()
    session.close()

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
        aggregated_news_data = []
        for page_number in range(1, 10):
            request_params = {
                "page": page_number,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }
            response = requests.get("https://udn.com/api/more", params=request_params)
            aggregated_news_data.append(response.json()["lists"])


        for news_data in aggregated_news_data:
            all_news_data.append(news_data)
    else:
        params = {
            "page": 1,
            "id": f"search:{quote(search_term)}",
            "channelId": 2,
            "type": "searchword",
        }
        response = requests.get("https://udn.com/api/more", params=params)


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
    
def get_news_article(is_initial=False):
    """
    獲取並處理與民生用品價格變化相關的新聞資訊
    
    :param is_initial: 布林值，若為 True 則會嘗試抓取多頁數據
    :return: None
    """
    news_data = fetch_news_info_by_search_term("價格", is_initial=is_initial)
    for news in news_data:
        title = news["title"]
        messages_content = [
            {
                "role": "system",
                "content": "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
            },
            {"role": "user", "content": f"{title}"},
        ]
        ai = OpenAI(api_key="xxx").chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_content,
        )
        relevance = ai.choices[0].message.content
        if relevance == "high":
            response = requests.get(news["titleLink"])
            soup = BeautifulSoup(response.text, "html.parser")
            # 標題
            title = soup.find("h1", class_="article-content__title").text
            time = soup.find("time", class_="article-content__time").text
            # 定位到包含文章内容的 <section>
            content_section = soup.find("section", class_="article-content__editor")


            paragraphs = [
                p.text
                for p in content_section.find_all("p")
                if p.text.strip() != "" and "▪" not in p.text
            ]
            detailed_news =  {
                "url": news["titleLink"],
                "title": title,
                "time": time,
                "content": paragraphs,
            }
            messages_content = [
                {
                    "role": "system",
                    "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                },
                {"role": "user", "content": " ".join(detailed_news["content"])},
            ]


            completion = OpenAI(api_key="xxx").chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_content,
            )
            result = completion.choices[0].message.content
            result = json.loads(result)
            detailed_news["summary"] = result["影響"]
            detailed_news["reason"] = result["原因"]
            add_news_to_database(detailed_news)

def get_news_exists_status(news_id: int, db: Session) -> bool:
    """
    檢查指定的新聞 ID 是否存在於資料庫中。
    :param news_id: 新聞 ID
    :param db: 資料庫會話
    :return: 如果新聞存在返回 True，否則返回 False
    """
    return db.query(NewsArticle).filter_by(id=news_id).first() is not None