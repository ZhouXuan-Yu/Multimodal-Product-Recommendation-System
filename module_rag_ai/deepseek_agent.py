"""模块三支撑：DeepSeek Agent 封装。"""

from __future__ import annotations

import json
import os
from typing import Any

import requests


class DeepSeekAgent:
    """封装 Prompt 组装与 DeepSeek API 调用。"""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.deepseek.com/v1/chat/completions"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url

    def build_prompt(self, user_id: str, user_profile: dict[str, Any], candidates: list[dict[str, Any]], query: str) -> str:
        """构建 RAG Prompt，要求模型返回可解析 JSON。"""
        rules = {
            "target": "输出Top-3推荐",
            "must_format": "必须返回 JSON，字段包含 recommendations(list)；每项含 product_id, rank, reason",
            "constraints": ["优先满足用户偏好", "结合用户当前查询词", "推荐理由简洁可信"],
        }
        prompt_payload = {
            "user_id": user_id,
            "query": query,
            "user_profile": user_profile,
            "candidates": candidates,
            "rules": rules,
        }
        return json.dumps(prompt_payload, ensure_ascii=False, indent=2)

    def recommend(self, prompt: str, timeout: int = 45) -> dict[str, Any]:
        """调用 DeepSeek，失败时抛出异常由上层降级处理。"""
        if not self.api_key:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY，请先配置环境变量")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是电商推荐专家，请严格输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # 优先直接解析；若模型包了 markdown 代码块，做一次清理。
        text = content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)
