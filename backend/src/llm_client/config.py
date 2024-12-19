from dotenv import load_dotenv
import os

# 載入 .env 檔案
load_dotenv()

# 取得 API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
