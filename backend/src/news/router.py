from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from bs4 import BeautifulSoup
import requests
import json
from src.auth.dependencies import authenticate_user_token
from src.news.schemas import PromptRequest, NewsResponse, NewsSumaryRequestSchema, NewsSumaryCustomModelSchema
from src.news.dependencies import (
    session_opener,
    get_article_upvote_details,
    fetch_news_info_by_search_term,
    toggle_news_upvoted_status,
)
from src.news.models import NewsArticle
from src.news.utils import _id_counter
from src.llm_client.openai_client import OpenAIClient
from src.llm_client.anthropic_client import AnthropicClient
from src.llm_client.base import Message, LLMClientTemplate


router = APIRouter()


@router.get("/api/v1/news/news")


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
    :param llm_client: OpenAI 客戶端，用於與 LLM 交互
    :return: 搜尋結果的新聞列表
    """
    prompt = request.prompt
    news_list = []
    llm_client = OpenAIClient()

    # 使用 llm_client 提取關鍵字
    keywords = llm_client.extract_keywords(prompt).strip()
    if not keywords:
        return {"error": "Failed to extract keywords. Please try again."}


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
                p.text.strip()
                for p in content_section.find_all("p")
                if p.text.strip() and "▪" not in p.text
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
async def get_news_summary(
    payload: NewsSumaryRequestSchema,
):
    """
    使用 OpenAI 生成新聞摘要，提取影響和原因。


    :param payload: 包含新聞內容的請求資料
    :param llm_client: OpenAI 客戶端，用於與 LLM 交互
    :param u: 已驗證的使用者
    :return: 包含摘要和原因的回應
    """
    llm_client = OpenAIClient()
    response = {}
    #try:
        # 使用 llm_client 提取新聞摘要
    summary_data = llm_client.generate_summary(payload.content)
    if summary_data:
        response["summary"] = summary_data["影響"]
        response["reason"] = summary_data["原因"]


    return response
       
   
    #except Exception as e:
    #    print(f"Error generating news summary: {e}")
    #    return {"error": "An error occurred while generating the news summary."}


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

headers = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJUZXN0IiwiZXhwIjoxNzMzNzU3NzI4fQ.U8PawaychCLxKQ6HUFTR2nxm9ufeHQ7HfR2yL_Yjg9U"
@router.post("/api/v1/news/news_summary_custom_model")
async def get_news_summary_custom_model(
    payload: NewsSumaryCustomModelSchema,
    model_type,  # 默認使用 OpenAI
):
    """
    使用指定的 LLM 模型（OpenAI 或 Anthropic）生成新聞摘要，提取影響和原因。


    :param payload: 包含新聞內容的請求資料
    :param model_type: 模型類型，"openai" 或 "anthropic"
    :param u: 已驗證的使用者
    :return: 包含摘要和原因的回應
    """
    if(model_type == "openai"):
        llm_client = OpenAIClient()
    elif(model_type == "anthropic"):
        llm_client = AnthropicClient()
    else:
        raise HTTPException(status_code=500, detail=f"Error llm_client: {str(e)}")
    # 呼叫 LLM 客戶端生成摘要
    try:
        summary_data = llm_client.generate_summary(payload.content)
        if not summary_data:
            raise HTTPException(status_code=500, detail="Failed to generate summary.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

    response = {}
    # 構建回應
    if summary_data:
        response["summary"] = summary_data["影響"]
        response["reason"] = summary_data["原因"]

    return response


