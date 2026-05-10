import os

# API 설정 (환경 변수 또는 직접 입력)
# 본인의 Gemini API 키를 입력하세요.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_ACTUAL_API_KEY_HERE")
MODEL_NAME = "gemini-1.5-flash"  # 혹은 gemini-2.0-flash