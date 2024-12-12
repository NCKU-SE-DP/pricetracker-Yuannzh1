from pydantic import BaseModel #.dict()
import openai
from typing import List, Dict, Any, Optional
from src.llm_client.base import LLMClientBase, Message
import json


class OpenAIClient(LLMClientBase):
    """
    An implementation of the LLMClientBase for OpenAI's GPT-based APIs.
    """
    def __init__(self,_api_key) -> None:
        self.api_key = _api_key
        self.model = "gpt-3.5-turbo"
    
    def _perform_request(self,message_content):
        openai.api_key = self.api_key  # 設置 API Key
        response = openai.ChatCompletion.create(  # 使用 openai 的 ChatCompletion
            model=self.model,
            messages=message_content,
        )
        return response.choices[0].message.content  # 返回生成的消息
    
    def _create_message_content(self,system_role,user_content):
        system_message = Message(role="system", content=system_role)
        user_message = Message(role="user", content=user_content)
        message_content = [system_message.dict(), user_message.dict()]
        return message_content

    def generate_summary(self,content) -> dict:
        response = {}
        system_role = "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})"
        message_content = self._create_message_content(system_role,content)
        result = self._perform_request(message_content)
        if result:
            result = json.loads(result)
            response["影響"] = result["影響"]
            response["原因"] = result["原因"]
        return response
    
    def extract_keywords(self,prompt) -> str:
        system_role = "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)"
        message_content = self._create_message_content(system_role,prompt)
        keywords = self._perform_request(message_content)
        return keywords
    
    def evaluate_relevance(self,title) -> str:
        system_role = "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)"
        message_content = self._create_message_content(system_role,title)
        relevance = self._perform_request(message_content)
        return relevance

       
