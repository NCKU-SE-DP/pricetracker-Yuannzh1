from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import json



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
            raise ValueError("Client is not initialized.")


        response = self.client.chat.completions.create(
            model=self.model,
            messages=message_content,
            temperature=temperature,
        )
        return response.choices[0].message.content
        

    def _create_message_content(self, system_role: str, user_content: str) -> List[Dict[str, str]]:
        """
        統一消息格式生成。
        """
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

