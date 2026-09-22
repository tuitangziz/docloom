"""Session-owned library; importing this module creates no global document store."""
from .ingest import DocumentError, parse_document
from .models import Document
from .retrieval import HybridIndex


class Library:
    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.index: HybridIndex | None = None

    def add(self, name: str, data: bytes) -> tuple[Document, bool]:
        document = parse_document(name, data)
        if document.id in self.documents:
            return self.documents[document.id], False
        if len(self.documents) >= 30 or sum(len(d.passages) for d in self.documents.values()) + len(document.passages) > 5000:
            raise DocumentError("当前会话最多 30 份文档、5000 个片段。请先移除部分文档。")
        # Build before committing state so a failed import leaves a usable library.
        passages = [p for d in self.documents.values() for p in d.passages] + document.passages
        index = HybridIndex(passages)
        self.documents[document.id] = document
        self.index = index
        return document, True

    def remove(self, ids: set[str]):
        remaining = {key: doc for key, doc in self.documents.items() if key not in ids}
        passages = [p for d in remaining.values() for p in d.passages]
        index = HybridIndex(passages) if passages else None
        self.documents, self.index = remaining, index

    def clear(self):
        self.documents.clear()
        self.index = None
