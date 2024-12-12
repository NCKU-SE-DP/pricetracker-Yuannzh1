import abc
from pydantic import BaseModel, Field
from typing import List, Dict, Any


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
    '''
    @property
    def transfer_to_dict(self):
        value = [
            {"role": "system", "content": f"{self.role}"},
            {"role": "user", "content": f"{self.content}"},
        ]
        return value
    '''
    


class LLMClientBase(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def generate_summary() -> dict:
        
        return NotImplemented
    
    @abc.abstractmethod
    def generate_summary() -> str:
        
        return NotImplemented
    
    @abc.abstractmethod
    def evaluate_relevance() -> str:
        
        return NotImplemented
