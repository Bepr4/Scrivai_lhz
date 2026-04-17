"""Knowledge factory — 构建 QmdClient 与三个 Library。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import qmd

from scrivai.knowledge.cases import CaseLibrary
from scrivai.knowledge.rules import RuleLibrary
from scrivai.knowledge.templates import TemplateLibrary

if TYPE_CHECKING:
    from qmd import QmdClient


def build_qmd_client_from_config(db_path: str | Path) -> "QmdClient":
    """封装 qmd.connect;统一 ~ 展开。"""
    return qmd.connect(str(Path(db_path).expanduser()))


def build_libraries(
    qmd_client: "QmdClient",
) -> tuple[RuleLibrary, CaseLibrary, TemplateLibrary]:
    """一次性构建三兄弟。"""
    return (
        RuleLibrary(qmd_client),
        CaseLibrary(qmd_client),
        TemplateLibrary(qmd_client),
    )
