"""Knowledge Libraries — qmd 的三个 collection 包装(rules / cases / templates)。

参考 docs/design.md §4.7 / docs/superpowers/specs/2026-04-16-scrivai-m0.75-design.md §3。
"""

from scrivai.knowledge.cases import CaseLibrary
from scrivai.knowledge.factory import build_libraries, build_qmd_client_from_config
from scrivai.knowledge.rules import RuleLibrary
from scrivai.knowledge.templates import TemplateLibrary

__all__ = [
    "RuleLibrary",
    "CaseLibrary",
    "TemplateLibrary",
    "build_libraries",
    "build_qmd_client_from_config",
]
