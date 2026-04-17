"""M0.75 T0.15 contract tests:agents/*.yaml 都能被 load_pes_config 加载。

参考 docs/superpowers/specs/2026-04-16-scrivai-m0.75-design.md §6.4。
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = PROJECT_ROOT / "agents"


@pytest.mark.parametrize("yaml_name", ["extractor.yaml", "auditor.yaml", "generator.yaml"])
def test_load_pes_config(yaml_name: str) -> None:
    """load_pes_config 加载三份 YAML 全部通过且字段完整。"""
    from scrivai.pes.config import load_pes_config

    path = AGENTS_DIR / yaml_name
    assert path.is_file(), f"缺 {path}"

    cfg = load_pes_config(path)
    expected_name = yaml_name.removesuffix(".yaml")
    assert cfg.name == expected_name
    assert cfg.prompt_text  # 非空
    assert "available-tools" in cfg.default_skills
    assert set(cfg.phases.keys()) == {"plan", "execute", "summarize"}
    for phase_name in ("plan", "execute", "summarize"):
        phase = cfg.phases[phase_name]
        assert phase.allowed_tools
        assert phase.max_turns >= 1
        assert phase.required_outputs
