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
from sentry_sdk import capture_exception
from src.news.exceptions import ExtractFailure
from src.logging_config import logger

router = APIRouter()


@router.get("/api/v1/news/news")
def get_all_news_from_database(db: Session = Depends(session_opener)):
    """
    從資料庫中獲取所有新聞，並包含點讚數和是否已被點讚的狀態。


    :param db: 資料庫會話
    :return: 包含點讚和狀態資訊的新聞列表
    """
    try:
        logger.info("Fetching all news from database.")
        news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
        result = []
        for news in news:
            upvotes, upvoted = get_article_upvote_details(news.id, None, db)
            result.append(
                {**news.__dict__, "upvotes": upvotes, "is_upvoted": upvoted}
            )
        logger.info("Successfully fetched all news.")
        return result
    except Exception as err:
        logger.error("Error fetching news from database.", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=500, detail="Error fetching news from database.")




@router.get("/api/v1/news/user_news")


def get_user_upvoted_news(db= Depends(session_opener), user=Depends(authenticate_user_token)):
    """
    獲取用戶點讚過的新聞，並包含每篇新聞的點讚數和該用戶是否已點讚的狀態。


    :param db: 資料庫會話
    :param user: 已驗證的使用者
    :return: 包含點讚和用戶狀態的新聞列表
    """
    try:
        logger.info(f"Fetching upvoted news for user: {user.id}.")
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
        logger.info("Successfully fetched user upvoted news.")
        return result
    except Exception as err:
        logger.error("Error fetching user upvoted news.", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=500, detail="Error fetching user upvoted news.")




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
    try:
        logger.info("Extracting keywords from prompt using LLM.")
        keywords = llm_client.extract_keywords(prompt).strip()
        if not keywords:
            logger.warning("No keywords extracted from prompt.")
            raise ExtractFailure()
    except ExtractFailure as extract_err:
        # 捕捉特定的評估失敗錯誤並記錄到 Sentry
        logger.error("Failed to extract keywords.", exc_info=True)
        capture_exception(extract_err)
        return f"error: {extract_err}"
    except Exception as err:
        # 捕捉其他異常並記錄到 Sentry
        logger.error("Unexpected error during keyword extraction.", exc_info=True)
        capture_exception(err)
        return "error: An unexpected error occurred. Please try again."



    try:
        logger.info(f"Searching news with keywords: {keywords}")
        news_items = fetch_news_info_by_search_term(keywords, is_initial=False)
        for news in news_items:
            try:
                response = requests.get(news["titleLink"])
                response.raise_for_status()
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Error fetching news URL: {news['titleLink']}", exc_info=True)
                capture_exception(req_err)
                continue

            try:
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.find("h1", class_="article-content__title").text
                time = soup.find("time", class_="article-content__time").text
                content_section = soup.find("section", class_="article-content__editor")
                paragraphs = [
                    p.text.strip()
                    for p in content_section.find_all("p")
                    if p.text.strip() and "▪" not in p.text
                ]

                detailed_news = {
                    "url": news["titleLink"],
                    "title": title,
                    "time": time,
                    "content": " ".join(paragraphs),
                    "id": next(_id_counter),
                }
                news_list.append(detailed_news)

            except AttributeError as parse_err:
                logger.error("HTML parsing error for news article.", exc_info=True)
                capture_exception(parse_err)
                continue

        logger.info("Successfully fetched and parsed news articles.")
        return sorted(news_list, key=lambda x: x["time"], reverse=True)

    except Exception as err:
        logger.error("Unexpected error during news search.", exc_info=True)
        capture_exception(err)
        return "error: An unexpected error occurred while searching for news."




@router.post("/api/v1/news/news_summary")
async def get_news_summary(
    payload: NewsSumaryRequestSchema,
    user_authentic=Depends(authenticate_user_token)
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
    try:
        logger.info("Generating news summary using OpenAI.")
        # 使用 llm_client 提取新聞摘要
        summary_data = llm_client.generate_summary(payload.content)
        if not summary_data:
            logger.warning("No summary generated for the news.")
            raise ValueError("Empty summary returned.")
        
        response["summary"] = summary_data["影響"]
        response["reason"] = summary_data["原因"]
        logger.info("Successfully generated news summary.")
        return response

    except ValueError as val_err:
        # 捕捉數據格式或值相關的問題
        logger.error("Invalid data during summary generation.", exc_info=True)
        capture_exception(val_err)
        return f"error: Invalid input data: {val_err}"
    except Exception as err:
        # 捕捉其他未預期的異常
        logger.error("Unexpected error during summary generation.", exc_info=True)
        capture_exception(err)
        return "error: An unexpected error occurred while processing your request. Please try again."


    #except Exception as e:
    #    print(f"Error generating news summary: {e}")
    #    return {"error": "An error occurred while generating the news summary."}


@router.post("/api/v1/news/{id}/upvote")
def upvote_article(id, db= Depends(session_opener), user=Depends(authenticate_user_token)):
    """
    切換指定新聞的點讚狀態


    :param id: 新聞 ID
    :param db: 資料庫會話
    :param u: 已驗證的使用者
    :return: 包含操作訊息的字典
    """
    try:
        logger.info(f"Toggling upvote status for article ID: {id}, user: {user.id}.")
        message = toggle_news_upvoted_status(id, user.id, db)
        logger.info(f"Successfully toggled upvote status: {message}")
        return {"message": message}
    except Exception as err:
        logger.error("Error toggling upvote status.", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=500, detail="Error toggling upvote status.")

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
    try:
        logger.info(f"Generating news summary using model type: {model_type}.")
        if model_type == "openai":
            llm_client = OpenAIClient()
        elif model_type == "anthropic":
            llm_client = AnthropicClient()
        else:
            logger.error("Invalid model type provided.")
            raise HTTPException(status_code=400, detail="Invalid model_type provided.")

        summary_data = llm_client.generate_summary(payload.content)
        response = {
            "summary": summary_data["影響"],
            "reason": summary_data["原因"],
        }
        logger.info("Successfully generated custom model news summary.")
        return response

    except HTTPException as http_err:
        logger.error("HTTP error during custom model summary generation.", exc_info=True)
        capture_exception(http_err)
        raise http_err

    except Exception as err:
        logger.error("Unexpected error during custom model summary generation.", exc_info=True)
        capture_exception(err)
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")
