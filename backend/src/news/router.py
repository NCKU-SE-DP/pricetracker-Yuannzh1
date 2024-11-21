from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from bs4 import BeautifulSoup
import requests
import json
from src.auth.dependencies import authenticate_user_token
from src.news.schemas import PromptRequest, NewsResponse, NewsSumaryRequestSchema
from src.news.dependencies import (
    session_opener, 
    get_article_upvote_details, 
    fetch_news_info_by_search_term,
    toggle_news_upvoted_status,
)
from src.news.models import NewsArticle
from src.news.utils import _id_counter



router = APIRouter()
@router.get("/api/v1/news/news", response_model=List[NewsResponse])

def get_all_news_from_database(db: Session = Depends(session_opener)):
    """
    從資料庫中獲取所有新聞，並包含點讚數和是否已被點讚的狀態。

    :param db: 資料庫會話
    :return: 包含點讚和狀態資訊的新聞列表
    """
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for n in news:
        upvotes, upvoted = get_article_upvote_details(n.id, None, db)
        result.append(
            {**n.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
        )
    return result


@router.get("/api/v1/news/user_news")

def get_user_upvoted_news(db= Depends(session_opener), user=Depends(authenticate_user_token)):
    """
    獲取用戶點讚過的新聞，並包含每篇新聞的點讚數和該用戶是否已點讚的狀態。

    :param db: 資料庫會話
    :param user: 已驗證的使用者
    :return: 包含點讚和用戶狀態的新聞列表
    """
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news:
        upvotes, upvoted = get_article_upvote_details(article.id, user.id, db)
        result.append(
            {
                **article.__dict__,
                "upvotes": upvotes,
                "is_upvoted": upvoted,
            }
        )
    return result


@router.post("/api/v1/news/search_news")
async def search_news(request: PromptRequest):
    """
    使用 OpenAI 來提取關鍵字並根據關鍵字搜尋新聞內容。

    :param request: 包含用戶輸入的 prompt
    :param db: 資料庫會話
    :return: 搜尋結果的新聞列表
    """
    prompt = request.prompt
    news_list = []

    # 使用 OpenAI 提取關鍵字
    messages_content = [
        {
            "role": "system",
            "content": "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)",
        },
        {"role": "user", "content": f"{prompt}"},
    ]

    # 呼叫 OpenAI API 提取關鍵字
    completion = OpenAI(api_key="xxx").chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages_content,
    )
    keywords = completion.choices[0].message.content.strip()

    # 使用提取出的關鍵字進行新聞搜索
    news_items = fetch_news_info_by_search_term(keywords, is_initial=False)
    for news in news_items:
        try:
            response = requests.get(news["titleLink"])
            soup = BeautifulSoup(response.text, "html.parser")

            # 抓取並解析新聞的標題和時間
            title = soup.find("h1", class_="article-content__title").text
            time = soup.find("time", class_="article-content__time").text
            
            # 抓取新聞內容部分
            content_section = soup.find("section", class_="article-content__editor")
            paragraphs = [
                p.text
                for p in content_section.find_all("p")
                if p.text.strip() != "" and "▪" not in p.text
            ]

            # 組合新聞數據
            detailed_news = {
                "url": news["titleLink"],
                "title": title,
                "time": time,
                "content": " ".join(paragraphs),
            }
            
            # 使用唯一的新聞 ID（假設有 `_id_counter` 作為 ID 生成器）
            detailed_news["id"] = next(_id_counter)
            news_list.append(detailed_news)
        except Exception as error_message:
            print(f"Error fetching article: {error_message}")

    # 按時間排序並返回結果
    return sorted(news_list, key=lambda x: x["time"], reverse=True)

@router.post("/api/v1/news/news_summary")
async def get_news_summary(payload: NewsSumaryRequestSchema, u=Depends(authenticate_user_token)):
    """
    使用 OpenAI 生成新聞摘要，提取影響和原因。

    :param payload: 包含新聞內容的請求資料
    :param u: 已驗證的使用者
    :return: 包含摘要和原因的回應
    """
    response = {}
    messages_content = [
        {
            "role": "system",
            "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
        },
        {"role": "user", "content": f"{payload.content}"},
    ]

    completion = OpenAI(api_key="xxx").chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages_content,
    )
    result = completion.choices[0].message.content
    if result:
        result = json.loads(result)
        response["summary"] = result.get("影響", "")
        response["reason"] = result.get("原因", "")

    return response


@router.post("/api/v1/news/{id}/upvote")
def upvote_article(id, db= Depends(session_opener), u=Depends(authenticate_user_token)):
    """
    切換指定新聞的點讚狀態

    :param id: 新聞 ID
    :param db: 資料庫會話
    :param u: 已驗證的使用者
    :return: 包含操作訊息的字典
    """
    message = toggle_news_upvoted_status(id, u.id, db)
    return {"message": message}