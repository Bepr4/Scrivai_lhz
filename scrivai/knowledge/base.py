"""_BaseLibrary — 三个 Library 的共通基类。

直接代理 qmd Collection 的 add_document / get_document / list_documents /
delete_document / hybrid_search;无内存状态。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from scrivai.models.knowledge import LibraryEntry

if TYPE_CHECKING:
    from qmd import Collection, QmdClient, SearchResult


class _BaseLibrary:
    """RuleLibrary / CaseLibrary / TemplateLibrary 的共通实现。

    子类只需在 __init__ 中传入 collection_name。
    """

    def __init__(self, qmd_client: "QmdClient", collection_name: str) -> None:
        self._collection_name = collection_name
        self._coll: Collection = qmd_client.collection(collection_name)

    @property
    def collection_name(self) -> str:
        return self._collection_name

    def add(self, entry_id: str, markdown: str, metadata: dict[str, Any]) -> LibraryEntry:
        """写入 qmd chunk;entry_id 在 collection 内必须唯一。

        重复抛 ValueError;qmd 的 add_document 自身没有唯一性校验,所以这里 get 一次。
        """
        if self._coll.get_document(entry_id) is not None:
            raise ValueError(
                f"entry_id {entry_id!r} already exists in collection {self._collection_name!r}"
            )
        self._coll.add_document(entry_id, markdown, metadata)
        return LibraryEntry(entry_id=entry_id, markdown=markdown, metadata=dict(metadata))

    def get(self, entry_id: str) -> Optional[LibraryEntry]:
        """按 document_id 取;不存在返回 None。"""
        doc = self._coll.get_document(entry_id)
        if doc is None:
            return None
        return LibraryEntry(
            entry_id=doc["id"],
            markdown=doc["markdown"],
            metadata=dict(doc.get("metadata") or {}),
        )

    def list(self) -> list[str]:
        """返回 collection 内所有 entry_id。"""
        return self._coll.list_documents()

    def delete(self, entry_id: str) -> None:
        """删除 collection 内的 entry;不存在不报错(qmd 行为)。"""
        self._coll.delete_document(entry_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list["SearchResult"]:
        """透传 qmd hybrid_search。"""
        return self._coll.hybrid_search(query, top_k=top_k, filters=filters)
