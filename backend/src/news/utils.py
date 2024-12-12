import itertools
from fastapi import Depends
from src.llm_client.openai_client import OpenAIClient
# 用於生成唯一 ID 的計數器
_id_counter = itertools.count(start=1000000)

def get_openai_client() -> OpenAIClient:
    """
    提供 OpenAIClient 實例的工廠函數
    """
    return OpenAIClient(_api_key="xxx")