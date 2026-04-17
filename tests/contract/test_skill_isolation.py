"""M0.75 T0.14 contract test:available-tools/SKILL.md 不能含 workspace/trajectory/io。

参考 docs/superpowers/specs/2026-04-16-scrivai-m0.75-design.md §6.2。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
AVAILABLE_TOOLS_MD = PROJECT_ROOT / "skills" / "available-tools" / "SKILL.md"


def test_available_tools_skill_exists() -> None:
    assert AVAILABLE_TOOLS_MD.is_file(), f"missing: {AVAILABLE_TOOLS_MD}"


def test_available_tools_does_not_list_workspace_or_trajectory() -> None:
    """Agent 可见命令清单严禁出现 workspace/trajectory/io 子命令(信息隔离边界)。

    检查具体的 CLI 子命令名,而不是单词本身(描述里出现 'workspace'/'trajectory'
    解释职责边界是允许的)。
    """
    content = AVAILABLE_TOOLS_MD.read_text(encoding="utf-8")

    # 检查 fence code block 内的 CLI 命令调用
    forbidden_commands = [
        "scrivai-cli workspace ",
        "scrivai-cli trajectory ",
        "scrivai-cli io ",
    ]
    for forbidden in forbidden_commands:
        assert forbidden not in content, f"available-tools/SKILL.md 不应含命令 {forbidden!r}"


def test_all_four_skills_exist() -> None:
    """四份 skill 必须都在。"""
    expected = {
        "available-tools",
        "search-knowledge",
        "inspect-document",
        "render-output",
    }
    skills_dir = PROJECT_ROOT / "skills"
    actual = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    assert expected.issubset(actual), f"缺失 skill 目录:{expected - actual}"


@pytest.mark.parametrize(
    "skill_name",
    ["available-tools", "search-knowledge", "inspect-document", "render-output"],
)
def test_skill_md_has_required_frontmatter(skill_name: str) -> None:
    """每份 SKILL.md 必须有合法 YAML frontmatter,含 name 和 description。"""
    md = PROJECT_ROOT / "skills" / skill_name / "SKILL.md"
    assert md.is_file()
    content = md.read_text(encoding="utf-8")

    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert m is not None, f"{skill_name} 缺 YAML frontmatter"

    import yaml

    fm = yaml.safe_load(m.group(1))
    assert isinstance(fm, dict)
    assert fm.get("name") == skill_name, f"frontmatter name 应为 {skill_name}"
    assert fm.get("description"), f"{skill_name} 缺 description"
