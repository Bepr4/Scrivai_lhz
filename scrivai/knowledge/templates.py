"""TemplateLibrary — 模板文件供相似度匹配,collection 名固定 'templates'。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scrivai.knowledge.base import _BaseLibrary

if TYPE_CHECKING:
    from qmd import QmdClient


class TemplateLibrary(_BaseLibrary):
    """模板知识库,固定 collection 'templates'。"""

    def __init__(self, qmd_client: "QmdClient") -> None:
        super().__init__(qmd_client, "templates")
