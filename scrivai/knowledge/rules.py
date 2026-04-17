"""RuleLibrary — 法规 / 指引 / 标准的 markdown 分块,collection 名固定 'rules'。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scrivai.knowledge.base import _BaseLibrary

if TYPE_CHECKING:
    from qmd import QmdClient


class RuleLibrary(_BaseLibrary):
    """规则知识库,固定 collection 'rules'。"""

    def __init__(self, qmd_client: "QmdClient") -> None:
        super().__init__(qmd_client, "rules")
