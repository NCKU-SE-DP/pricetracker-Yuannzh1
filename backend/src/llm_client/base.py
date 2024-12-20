
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import json
from json.decoder import JSONDecodeError
from src.llm_client.exceptions import ResponseStructError
from sentry_sdk import capture_exception

# from openai import openAI
class Message(BaseModel):
    """
    A schema for messages passed to the LLM client.
    """
    role: str = Field(
        ...,
        example="user",
        description="Role of the message sender (e.g., 'user', 'assistant')."
    )
    content: str = Field(
        ...,
        example="What is the weather today?",
        description="Content of the message."
    )


class LLMClientTemplate(ABC):
    """
    抽象基類，為 LLM 客戶端提供統一接口。
    """


    def __init__(self, _api_key: str, model: Optional[str] = None):
        self._api_key = _api_key
        self.client = None
        self.model = model

    def _perform_request(
        self,
        message_content: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """
        通用的 API 請求方法，調用 AISuite 的 client.ChatCompletion.create。
        """
        if not self.client:
            raise ValueError("Client should be openai or anthropic")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=message_content,
                temperature=temperature,
            )
            if not response.choices or "content" not in response.choices[0].message:
                raise ResponseStructError("Response structure is invalid.")
            return response.choices[0].message.content
        
        except ValueError as res_err:
            capture_exception(res_err)
            raise res_err  # 保留原始異常上下文
        
        except Exception as err:
            capture_exception(err)
            return "An unexpected error occurred while processing request."
        
        

    def _create_message_content(self, system_role: str, user_content: str) -> List[Dict[str, str]]:
        """
        統一消息格式生成。
        """
        try:
            if not isinstance(user_content, str):
                raise TypeError("user_content must be strings.")
            if not user_content:
                raise ValueError("user_content must be non-empty strings.")
        
            system_message = Message(role="system", content=system_role)
            user_message = Message(role="user", content=user_content)
            message_content = [system_message.dict(), user_message.dict()]
            return message_content
        
        except Exception as err:
            # 捕捉異常並記錄到遠端
            capture_exception(err)

    def generate_summary(self,content) -> dict:
        response = {}
        system_role = "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})"
        message_content = self._create_message_content(system_role,content)
        result = self._perform_request(message_content)
        if result:
            try:
                # 嘗試解析 JSON
                result = json.loads(result)
                response["影響"] = result.get("影響", "未提供影響")
                response["原因"] = result.get("原因", "未提供原因")
                
            except JSONDecodeError as JSON_err:
                #捕捉 JSON 格式錯誤
                capture_exception(JSON_err)  # 記錄到遠端監控（如 Sentry）
                raise ValueError(f"Invalid JSON format in response: {result}") from JSON_err
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

