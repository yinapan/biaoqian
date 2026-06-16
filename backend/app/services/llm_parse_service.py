"""LLM-based query parse service.

Sends the *remaining* (un-matched) portion of a user query to an LLM and
asks it to extract structured tag filters.  The raw LLM output must be
validated by :func:`~app.services.parse_validator.validate_llm_result`
before use.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """你是一个游戏资产搜索系统的查询解析器。
系统已识别出: {already_matched}
以下是尚未匹配的剩余文本，请尝试从中提取更多标签。

尚未匹配的标签维度:
{unmatched_tag_schema}

规则:
1. 只提取有把握的标签，不确定的放入 keyword
2. 数值条件用 {{"op":">","value":5}} 格式
3. 描述性/模糊性词语放入 keyword
4. 返回严格JSON

剩余文本: {remaining_text}

返回: {{"filter":{{}},"keyword":"","confidence":0.0}}"""


async def call_llm(
    remaining_text: str,
    already_matched: dict,
    unmatched_schema: list[dict],
) -> dict | None:
    """Call the configured LLM to parse *remaining_text*.

    Returns the parsed JSON dict on success, or ``None`` if the LLM is
    disabled, misconfigured, or the call fails for any reason.
    """
    if not settings.llm_enabled or not settings.llm_api_key:
        return None

    schema_str = "\n".join(
        f"- {d['field_name']}({d['display_name']}): {d['field_type']}"
        + (f", 可选值: {d.get('values', [])}" if d.get("values") else "")
        for d in unmatched_schema
    )
    prompt = PROMPT_TEMPLATE.format(
        already_matched=json.dumps(already_matched, ensure_ascii=False),
        unmatched_tag_schema=schema_str,
        remaining_text=remaining_text,
    )

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 256,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # Strip markdown code-fence wrapper if present.
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            return json.loads(content)
    except Exception:
        logger.warning("LLM parse call failed for text: %s", remaining_text, exc_info=True)
        return None
