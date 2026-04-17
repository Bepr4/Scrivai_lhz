"""M0.75 T0.11 contract tests for Knowledge Libraries.

参考 docs/superpowers/specs/2026-04-16-scrivai-m0.75-design.md §3。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def qmd_client(tmp_path: Path):
    from scrivai.knowledge import build_qmd_client_from_config

    return build_qmd_client_from_config(tmp_path / "test.db")


@pytest.fixture
def libraries(qmd_client):
    from scrivai.knowledge import build_libraries

    return build_libraries(qmd_client)


def test_library_crud(libraries) -> None:
    """add → get → list → delete → get returns None。"""
    rules, _, _ = libraries
    entry = rules.add(
        entry_id="rule-001",
        markdown="围标串标的认定标准",
        metadata={"title": "招投标法 §32"},
    )
    assert entry.entry_id == "rule-001"
    assert entry.markdown == "围标串标的认定标准"
    assert entry.metadata == {"title": "招投标法 §32"}

    got = rules.get("rule-001")
    assert got is not None
    assert got.entry_id == "rule-001"
    assert got.markdown == "围标串标的认定标准"

    assert "rule-001" in rules.list()

    rules.delete("rule-001")
    assert rules.get("rule-001") is None
    assert "rule-001" not in rules.list()


def test_entry_id_uniqueness_in_collection(libraries) -> None:
    """同 entry_id 在同一 collection 内 add 两次 → ValueError。"""
    rules, _, _ = libraries
    rules.add(entry_id="dup-001", markdown="first", metadata={})
    with pytest.raises(ValueError, match="already exists"):
        rules.add(entry_id="dup-001", markdown="second", metadata={})


def test_cross_collection_isolation(libraries) -> None:
    """rules 和 cases 各 add 同 entry_id → 互不影响。"""
    rules, cases, _ = libraries
    rules.add(entry_id="x-001", markdown="from rules", metadata={})
    cases.add(entry_id="x-001", markdown="from cases", metadata={})

    r = rules.get("x-001")
    c = cases.get("x-001")
    assert r is not None and r.markdown == "from rules"
    assert c is not None and c.markdown == "from cases"


def test_search_returns_results(libraries) -> None:
    """add 几条 → search 返回 list[SearchResult](非空)。"""
    rules, _, _ = libraries
    rules.add(entry_id="r-1", markdown="围标串标的认定标准", metadata={})
    rules.add(entry_id="r-2", markdown="政府采购的供应商资格", metadata={})

    results = rules.search(query="围标", top_k=5)
    assert isinstance(results, list)
    assert len(results) >= 1
