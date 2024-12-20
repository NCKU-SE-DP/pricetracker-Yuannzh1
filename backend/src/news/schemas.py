from pydantic import BaseModel

class NewsRequest(BaseModel):
    prompt: str

class NewsResponse(BaseModel):
    title: str
    content: str
    upvotes: int

class NewsSumaryRequestSchema(BaseModel):
    content: str

class PromptRequest(BaseModel):
    prompt: str
class NewsSumaryCustomModelSchema(BaseModel):
    content: str