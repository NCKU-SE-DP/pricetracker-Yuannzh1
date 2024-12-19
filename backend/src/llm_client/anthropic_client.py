from src.llm_client.base import LLMClientTemplate
from src.llm_client.config import ANTHROPIC_API_KEY
from typing import List, Dict
import aisuite as ai
class AnthropicClient(LLMClientTemplate):
    def __init__(self) -> None:
        self._api_key = ANTHROPIC_API_KEY
        self.client = ai.Client()
        self.model = "anthropic:claude-3-5-sonnet-20240620"

       