"""DeepSeek 客户端。

用途：
1. 读取环境变量配置。
2. 调用 OpenAI 兼容的 /chat/completions 接口。
3. 返回模型文本内容。
"""

import os
from typing import Any

import httpx


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com").strip()
        self.model = os.getenv("OPENAI_CHAT_MODEL", "deepseek-chat").strip()

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[dict[str, str]], response_as_json: bool = False) -> str:
        if not self.is_enabled():
            raise RuntimeError("OPENAI_API_KEY is not configured")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if response_as_json:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(
                f"DeepSeek API error {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("DeepSeek API error: empty choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek API error: empty content")

        return content.strip()
