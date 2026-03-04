"""模块三支撑：DeepSeek Agent 封装。"""

from __future__ import annotations

import json
import os
from typing import Any

import requests


# 如果只在本地开发/测试，可以把 DeepSeek 的 API Key 直接写在这里。
# !!! 切记不要把包含真实密钥的代码推到公网仓库（GitHub 等）或发给他人。
DEEPSEEK_API_KEY_HARDCODED = "sk-fa86cd1e1c814e0b90155dd6180d9055"  # 在这里填入你的 DeepSeek API Key，例如："sk-xxx..."


class DeepSeekAgent:
    """封装 Prompt 组装与 DeepSeek API 调用。"""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.deepseek.com/v1/chat/completions"):
        # 优先使用显式传入的 api_key，其次是本文件中硬编码的常量，最后才尝试读环境变量。
        self.api_key = api_key or DEEPSEEK_API_KEY_HARDCODED or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url

    # ================= 通用底层调用封装 =================
    def _chat(self, system_prompt: str, user_content: str, timeout: int = 45) -> str:
        """底层 HTTP 调用封装，返回原始文本内容，由上层自行解析 JSON。"""
        if not self.api_key:
            raise RuntimeError(
                "缺少 DeepSeek API Key：请在 module_rag_ai/deepseek_agent.py 中设置 DEEPSEEK_API_KEY_HARDCODED，"
                "或者配置环境变量 DEEPSEEK_API_KEY。"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
        }

        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """
        从模型输出中提取 JSON。

        兼容以下情况：
        - 纯 JSON 文本
        - 被 ```json / ``` 包裹的代码块
        - 前后带有解释性文字，只在中间包含一个 JSON 对象
        """
        raw = text.strip()

        # 1. 优先处理 markdown 代码块：```json\n{...}\n``` 或 ```\n{...}\n```
        if "```" in raw:
            parts = raw.split("```")
            # 常见结构：before ``` json\n{...}\n ``` after
            if len(parts) >= 3:
                candidate = parts[1]
            else:
                # 退化情况：只出现一次 ```，尝试取其后的部分
                candidate = parts[-1]
            candidate = candidate.strip()
            if candidate.lower().startswith("json"):
                # 去掉可能的 "json\n"
                candidate = candidate[4:].lstrip("\n\r").lstrip()
            raw = candidate.strip()

        # 2. 先尝试整体解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 3. 如果整体失败，再尝试提取第一个完整的大括号 JSON 对象
        first_brace = raw.find("{")
        last_brace = raw.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            json_str = raw[first_brace : last_brace + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # 4. 仍然失败，则抛出原始文本，交由上层捕获并做降级处理
        raise json.JSONDecodeError("无法从模型输出中提取合法 JSON", raw, 0)

    # ================= 推荐精排 Prompt / 调用 =================
    def build_prompt(self, user_id: str, user_profile: dict[str, Any], candidates: list[dict[str, Any]], query: str) -> str:
        """构建 RAG Prompt，要求模型返回可解析 JSON（用于 Top-K 精排推荐）。"""
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
        """调用 DeepSeek 做推荐精排，失败时抛出异常由上层降级处理。"""
        content = self._chat(
            system_prompt=(
                "你是电商推荐专家。"
                "请严格只输出一个合法的 JSON 对象："
                "不要使用 markdown 代码块、不要添加任何解释或多余文字。"
            ),
            user_content=prompt,
            timeout=timeout,
        )
        return self._extract_json(content)

    # ================= 查询意图解析 =================
    def build_intent_prompt(
        self,
        query: str,
        user_id: str | None = None,
        user_profile: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        构建“查询意图解析” Prompt，要求模型返回结构化意图 JSON。

        该 JSON 将用于后续 Hybrid Recall + Rerank。
        """
        payload: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "user_profile": user_profile or {},
            "history": history or [],
            "output_schema": {
                "normalized_query": "string，自然语言规范化后的查询（便于展示）",
                "search_vector_text": "string，用于向量检索的紧凑语义表述（必须保留关键信息）",
                "category": "string | null，核心品类（例如：手机、耳机、电视），不确定时给 null",
                "price_range": {
                    "min": "number | null，最低价格，无法判断时为 null",
                    "max": "number | null，最高价格，无法判断时为 null",
                },
                "style_tags": ["string，风格/偏好标签，例如：极简、科技感、适合学生"],
                "must_have_keywords": ["string，必须满足的关键诉求词，例如“降噪”“轻薄”"],
                "exclude_keywords": ["string，需要明显排除的特征，例如“二手”“翻新”"],
                "sort_by": "string，推荐排序侧重：relevance / price_asc / price_desc / popularity",
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def analyze_intent(self, prompt: str, timeout: int = 30) -> dict[str, Any]:
        """
        调用 DeepSeek 做“查询意图解析”，返回结构化 JSON。

        上层会将该结果映射为 QueryIntent 数据结构。
        """
        content = self._chat(
            system_prompt=(
                "你是电商搜索与推荐的查询意图分析助手。"
                "请根据用户查询、画像与历史行为，推断其真实购物诉求。"
                "你必须严格按照用户提供的 output_schema 输出且只输出一个合法的 JSON 对象："
                "不要使用 markdown 代码块（不要输出 ```json 或 ```），"
                "不要输出任何解释性文字、注释或其他多余内容。"
            ),
            user_content=prompt,
            timeout=timeout,
        )
        return self._extract_json(content)
