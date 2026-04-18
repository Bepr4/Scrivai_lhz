"""Proposer JSON 解析加固单元测试(M3a Task 1)。

覆盖 M2 Task 9 实跑发现的真实异常格式。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from scrivai.evolution.proposer import (
    Proposer,
    ProposerError,
    _extract_json,
    _find_json_object,
    _normalize_common_issues,
)


def _valid_payload(n: int = 1) -> dict:
    """构造 N 条合法 proposals 负载。"""
    return {
        "proposals": [
            {
                "change_summary": f"s{i}",
                "reasoning": f"r{i}",
                "new_content": {"SKILL.md": f"# new {i}"},
            }
            for i in range(n)
        ]
    }


def test_extract_json_plain():
    """原始 json.dumps 输出必须能直接解析。"""
    payload = _valid_payload(2)
    raw = json.dumps(payload, ensure_ascii=False)
    assert _extract_json(raw) == payload


def test_extract_json_with_markdown_fence():
    """LLM 把 JSON 包在 ```json ... ``` 中。"""
    payload = _valid_payload(1)
    raw = "这是分析结果:\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```\n"
    assert _extract_json(raw) == payload


def test_extract_json_with_prose_prefix():
    """LLM 先说一段话才给 JSON。"""
    payload = _valid_payload(1)
    raw = "好的,这是我的建议:\n" + json.dumps(payload, ensure_ascii=False)
    assert _extract_json(raw) == payload


def test_extract_json_with_nested_braces_in_string():
    """new_content.SKILL.md 字符串内含 { } (天真策略会误判)。"""
    payload = {
        "proposals": [
            {
                "change_summary": "use braces in skill content",
                "reasoning": "r",
                "new_content": {"SKILL.md": "# X\n\n使用 {var} 模板与 } 等字符"},
            }
        ]
    }
    raw = json.dumps(payload, ensure_ascii=False)
    parsed = _extract_json(raw)
    assert parsed["proposals"][0]["new_content"]["SKILL.md"] == "# X\n\n使用 {var} 模板与 } 等字符"


def test_extract_json_with_chinese_quotes():
    """GLM 偶发把 " 换成中文引号 " "。"""
    raw = (
        '{"proposals": [{"change_summary": "abc", "reasoning": "r", '
        '"new_content": {"SKILL.md": "# x"}}]}'
    )
    raw_broken = raw.replace('"abc"', "\u201cabc\u201d")
    parsed = _extract_json(raw_broken)
    assert parsed["proposals"][0]["change_summary"] == "abc"


def test_extract_json_with_trailing_comma():
    """GLM 偶发在最后一个对象后带尾逗号(非法 JSON)。"""
    raw = (
        '{"proposals": [{"change_summary": "a", "reasoning": "r", '
        '"new_content": {"SKILL.md": "# x"},}]}'
    )
    parsed = _extract_json(raw)
    assert parsed["proposals"][0]["change_summary"] == "a"


def test_extract_json_totally_invalid_raises():
    """完全没有 JSON 结构 → ProposerError。"""
    with pytest.raises(ProposerError, match="no JSON object"):
        _extract_json("这只是自然语言回答,没有任何 JSON 格式。")


def test_find_json_object_respects_string_escapes():
    """平衡扫描必须正确处理字符串内的 \\" 转义。"""
    raw = '{"k": "he said \\"hi\\" and {}"}'
    assert _find_json_object(raw) == raw


def test_normalize_common_issues_handles_both():
    """同时含中文引号和尾逗号。"""
    raw = '{\u201ckey\u201d: "value",}'
    normalized = _normalize_common_issues(raw)
    assert json.loads(normalized) == {"key": "value"}


@pytest.mark.asyncio
async def test_propose_retries_once_on_bad_json():
    """propose() 第一次解析失败应触发 1 次重试,重试成功则返回。"""
    good = json.dumps(_valid_payload(1), ensure_ascii=False)

    call_count = {"n": 0}

    async def _flaky(prompt, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "这根本不是 JSON"
        return good

    mock_client = MagicMock()
    mock_client.simple_query = _flaky
    p = Proposer(mock_client)
    out = await p.propose(
        current_skill_snapshot={"SKILL.md": "# x"},
        failures=[],
        rejected_proposals=[],
        n=1,
    )
    assert len(out) == 1
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_propose_raises_after_retry_also_fails():
    """两次都解析失败 → ProposerError。"""
    mock_client = MagicMock()
    mock_client.simple_query = AsyncMock(return_value="still not json")
    p = Proposer(mock_client)
    with pytest.raises(ProposerError):
        await p.propose(
            current_skill_snapshot={"SKILL.md": "# x"},
            failures=[],
            rejected_proposals=[],
            n=1,
        )
