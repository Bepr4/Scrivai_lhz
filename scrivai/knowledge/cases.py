"""CaseLibrary — 历史定稿(经专家审核的优质样本),collection 名固定 'cases'。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scrivai.knowledge.base import _BaseLibrary

if TYPE_CHECKING:
    from qmd import QmdClient


class CaseLibrary(_BaseLibrary):
    """案例知识库,固定 collection 'cases'。"""

    def __init__(self, qmd_client: "QmdClient") -> None:
        super().__init__(qmd_client, "cases")
