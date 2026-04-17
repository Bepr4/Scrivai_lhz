"""Scrivai IO 工具 — 文档格式转换 + docxtpl 渲染。

参考 docs/design.md §4.8 / docs/superpowers/specs/2026-04-16-scrivai-m0.75-design.md §4。
"""

from scrivai.io.convert import doc_to_markdown, docx_to_markdown, pdf_to_markdown
from scrivai.io.render import DocxRenderer

__all__ = [
    "docx_to_markdown",
    "doc_to_markdown",
    "pdf_to_markdown",
    "DocxRenderer",
]
