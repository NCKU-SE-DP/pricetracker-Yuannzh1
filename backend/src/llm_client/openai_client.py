from src.llm_client.base import LLMClientTemplate
from src.llm_client.config import OPENAI_API_KEY 
from typing import List, Dict
import aisuite as ai

class OpenAIClient(LLMClientTemplate):
    """
    An implementation of the LLMClientBase for OpenAI's GPT-based APIs.
    """
    def __init__(self) -> None:
        self._api_key = OPENAI_API_KEY 
        self.client = ai.Client()
        self.model = "openai:gpt-3.5-turbo" 
   


       
