"""Scrivai SDK 核心模块。

提供文档生成与审核能力。
"""

from core.audit.engine import AuditEngine, AuditResult
from core.generation.context import GenerationContext
from core.generation.engine import GenerationEngine
from core.knowledge.store import KnowledgeStore, SearchResult
from core.llm import LLMClient, LLMConfig
from core.project import Project, ProjectConfig

__all__ = [
    # 入口
    "Project",
    "ProjectConfig",
    # LLM
    "LLMClient",
    "LLMConfig",
    # 知识库
    "KnowledgeStore",
    "SearchResult",
    # 生成
    "GenerationEngine",
    "GenerationContext",
    # 审核
    "AuditEngine",
    "AuditResult",
]
