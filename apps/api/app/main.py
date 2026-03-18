"""搴旂敤鍏ュ彛銆?
鑱岃矗锛?1. 鍔犺浇鐜鍙橀噺銆?2. 鍒涘缓 FastAPI 搴旂敤銆?3. 鎸傝浇 API 璺敱銆?"""

from dotenv import load_dotenv
from fastapi import FastAPI

from app.routes.router import router

load_dotenv()

app = FastAPI(title="Happy Agent API", version="0.3.0")
app.include_router(router)
