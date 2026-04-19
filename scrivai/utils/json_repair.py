"""LLM 输出 JSON 容错解析 — 5 阶段渐进修复管线。

阶段顺序(任意一步成功即返回;全部失败才抛):
  Stage-0: json.loads 快路径
  Stage-1: 剥壳(空白 / Markdown 围栏 / 注释)
  Stage-2: 标点归一(中文引号 / 全角逗号)
  Stage-3: 尾逗号删除
  Stage-4: 字符串内裸引号转义
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, overload

from scrivai.exceptions import ScrivaiJSONRepairError

_MAX_MSG_PREVIEW = 200


@dataclass(frozen=True)
class RepairReport:
    """JSON 修复报告。"""

    stages_applied: list[str]
    original: str
    final: str


@overload
def relaxed_json_loads(
    text: str,
    *,
    strict: bool = False,
    return_repair_report: bool = False,
) -> Any: ...


@overload
def relaxed_json_loads(
    text: str,
    *,
    strict: bool = False,
    return_repair_report: bool = True,
) -> tuple[Any, RepairReport]: ...


def relaxed_json_loads(
    text: str,
    *,
    strict: bool = False,
    return_repair_report: bool = False,
) -> Any | tuple[Any, RepairReport]:
    """LLM 输出 JSON 容错解析。

    参数:
        text: LLM 原始输出文本（可能含 Markdown 围栏）。
        strict: True 时跳过所有修复，行为与 json.loads 完全一致。
        return_repair_report: True 时返回 (parsed_data, RepairReport) 元组。

    返回:
        解析后的 Python 对象；或 (对象, RepairReport) 元组。

    异常:
        ScrivaiJSONRepairError: 所有修复阶段均失败。
        json.JSONDecodeError: strict=True 时，与 json.loads 行为一致。
    """
    if strict:
        result = json.loads(text)
        if return_repair_report:
            return result, RepairReport(stages_applied=[], original=text, final=text)
        return result

    # Stage-0: 快路径
    try:
        result = json.loads(text)
        if return_repair_report:
            return result, RepairReport(stages_applied=[], original=text, final=text)
        return result
    except json.JSONDecodeError:
        pass

    original = text
    stages_applied: list[str] = []
    last_error: json.JSONDecodeError | None = None

    stages: list[tuple[str, Any]] = [
        ("strip_envelope", _strip_envelope),
        ("normalize_quotes", _normalize_quotes),
        ("remove_trailing_commas", _remove_trailing_commas),
        ("escape_inner_quotes", _escape_inner_quotes),
    ]

    for stage_name, stage_fn in stages:
        text = stage_fn(text)
        stages_applied.append(stage_name)
        try:
            result = json.loads(text)
            if return_repair_report:
                return result, RepairReport(
                    stages_applied=list(stages_applied),
                    original=original,
                    final=text,
                )
            return result
        except json.JSONDecodeError as e:
            last_error = e

    assert last_error is not None
    preview_orig = original[:_MAX_MSG_PREVIEW]
    preview_final = text[:_MAX_MSG_PREVIEW]
    msg = (
        f"JSON 修复失败(已尝试: {', '.join(stages_applied)}):\n"
        f"  json.loads 错误: {last_error}\n"
        f"  原始文本(前{_MAX_MSG_PREVIEW}字符): {preview_orig}\n"
        f"  修复后文本(前{_MAX_MSG_PREVIEW}字符): {preview_final}"
    )
    raise ScrivaiJSONRepairError(
        msg=msg,
        doc=text,
        pos=last_error.pos if last_error.pos is not None else 0,
        original_text=original,
        repaired_text=text,
        stages_applied=stages_applied,
    )


# ── Stage 实现 ──

_RE_FENCE = re.compile(r"^```(?:json|JSON)?\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


def _strip_envelope(text: str) -> str:
    """Stage-1: 去除前后空白、Markdown 围栏、行/块注释。"""
    text = text.strip()

    fence = _RE_FENCE.match(text)
    if fence:
        text = fence.group(1).strip()

    text = _remove_comments_outside_strings(text)
    return text


def _remove_comments_outside_strings(text: str) -> str:
    """去除 JSON 语法位置的 // 行注释和 /* */ 块注释,保留字符串内容不变。"""
    result: list[str] = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]

        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < len(text):
                result.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            end = text.find("\n", i)
            if end == -1:
                break
            i = end
            continue

        if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                break
            i = end + 2
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _normalize_quotes(text: str) -> str:
    return text


def _remove_trailing_commas(text: str) -> str:
    return text


def _escape_inner_quotes(text: str) -> str:
    return text
