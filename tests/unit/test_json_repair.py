"""relaxed_json_loads 单元测试。"""

from __future__ import annotations

import json

import pytest

from scrivai.exceptions import ScrivaiError, ScrivaiJSONRepairError


class TestScrivaiJSONRepairError:
    """ScrivaiJSONRepairError 异常类测试。"""

    def test_inherits_scrivai_error(self) -> None:
        err = ScrivaiJSONRepairError(
            msg="test error",
            doc='{"bad}',
            pos=5,
            original_text='{"bad}',
            repaired_text='{"bad}',
            stages_applied=["strip_envelope"],
        )
        assert isinstance(err, ScrivaiError)

    def test_inherits_json_decode_error(self) -> None:
        err = ScrivaiJSONRepairError(
            msg="test error",
            doc='{"bad}',
            pos=5,
            original_text='{"bad}',
            repaired_text='{"bad}',
            stages_applied=["strip_envelope"],
        )
        assert isinstance(err, json.JSONDecodeError)

    def test_attributes(self) -> None:
        err = ScrivaiJSONRepairError(
            msg="parse failed",
            doc='{"bad}',
            pos=5,
            original_text="original",
            repaired_text="repaired",
            stages_applied=["strip_envelope", "normalize_quotes"],
        )
        assert err.original_text == "original"
        assert err.repaired_text == "repaired"
        assert err.stages_applied == ["strip_envelope", "normalize_quotes"]
        assert err.doc == '{"bad}'
        assert err.pos == 5


from scrivai.utils.json_repair import RepairReport, relaxed_json_loads


class TestRelaxedJsonLoadsStrictMode:
    """strict=True 模式测试。"""

    def test_strict_valid_json(self) -> None:
        result = relaxed_json_loads('{"a": 1, "b": 2}', strict=True)
        assert result == {"a": 1, "b": 2}

    def test_strict_invalid_json_raises_json_decode_error(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            relaxed_json_loads('{"a": 1,}', strict=True)

    def test_strict_does_not_raise_scrivai_error(self) -> None:
        with pytest.raises(json.JSONDecodeError) as exc_info:
            relaxed_json_loads('{"a": 1,}', strict=True)
        assert not isinstance(exc_info.value, ScrivaiJSONRepairError)


class TestRelaxedJsonLoadsStage0:
    """Stage-0 快路径:合法 JSON 直通。"""

    def test_valid_object(self) -> None:
        result = relaxed_json_loads('{"a": 1, "b": 2}')
        assert result == {"a": 1, "b": 2}

    def test_valid_array(self) -> None:
        result = relaxed_json_loads('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_valid_json_with_report(self) -> None:
        result, report = relaxed_json_loads(
            '{"a": 1}', return_repair_report=True
        )
        assert result == {"a": 1}
        assert isinstance(report, RepairReport)
        assert report.stages_applied == []
        assert report.original == '{"a": 1}'
        assert report.final == '{"a": 1}'


class TestStage1StripEnvelope:
    """Stage-1: 剥壳(围栏 / 注释 / 空白)。"""

    def test_markdown_fence_json(self) -> None:
        text = '```json\n{"a": 1}\n```'
        assert relaxed_json_loads(text) == {"a": 1}

    def test_markdown_fence_no_lang(self) -> None:
        text = '```\n{"a": 1}\n```'
        assert relaxed_json_loads(text) == {"a": 1}

    def test_markdown_fence_with_whitespace(self) -> None:
        text = '  \n```json\n{"a": 1}\n```\n  '
        assert relaxed_json_loads(text) == {"a": 1}

    def test_line_comment(self) -> None:
        text = '{\n  "a": 1, // this is a comment\n  "b": 2\n}'
        assert relaxed_json_loads(text) == {"a": 1, "b": 2}

    def test_block_comment(self) -> None:
        text = '{\n  /* comment */\n  "a": 1\n}'
        assert relaxed_json_loads(text) == {"a": 1}

    def test_line_comment_inside_string_preserved(self) -> None:
        text = '{"url": "https://example.com"}'
        assert relaxed_json_loads(text) == {"url": "https://example.com"}

    def test_fence_with_report(self) -> None:
        text = '```json\n{"a": 1}\n```'
        result, report = relaxed_json_loads(text, return_repair_report=True)
        assert result == {"a": 1}
        assert "strip_envelope" in report.stages_applied
