"""Local BM25 + character TF-IDF rank fusion, with optional local embeddings."""
import re

import numpy as np
from rank_bm25 import BM25Plus
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import Hit, Passage

STOPWORDS = set("the a an is are was were to of in on at for with and or what how when where why please tell me about does do can 我 你 的 了 是 在 和 与 请 问 什么 怎么 如何 多少 哪些 是否 告诉 根据 文档 资料 内容".split())


def tokenize(text: str) -> list[str]:
    result = []
    for part in re.findall(r"[a-zA-Z0-9_]+|[\u3400-\u9fff]+", text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", part):
            # Bigrams work across Chinese word-boundary variations, without a download.
            result.extend(part[i:i + 2] for i in range(max(0, len(part) - 1)) if part[i:i + 2] not in STOPWORDS)
        elif part not in STOPWORDS:
            result.append(part)
    return result


class HybridIndex:
    def __init__(self, passages: list[Passage]):
        if not passages:
            raise ValueError("No passages to index")
        self.passages = passages
        self.tokens = [tokenize(p.text) for p in passages]
        self.bm25 = BM25Plus([tokens or ["__empty__"] for tokens in self.tokens], delta=0)
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=40000, sublinear_tf=True)
        try:
            self.matrix = self.vectorizer.fit_transform([p.text for p in passages])
        except ValueError:
            self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 1))
            self.matrix = self.vectorizer.fit_transform([p.text for p in passages])
        self.dense = None
        self.embedding_model = None

    def set_embeddings(self, vectors, model: str):
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(self.passages) or not np.isfinite(matrix).all():
            raise ValueError("Invalid embedding matrix")
        lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
        if (lengths == 0).any():
            raise ValueError("Zero embedding vector")
        self.dense = matrix / lengths
        self.embedding_model = model

    def search(self, query: str, top_k: int = 5, document_ids: set[str] | None = None, query_vector=None) -> list[Hit]:
        query = query.strip()
        if not query or not 1 <= top_k <= 12:
            return []
        lexical = np.asarray(self.bm25.get_scores(tokenize(query)))
        char = (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()
        dense = None
        if query_vector is not None:
            if self.dense is None:
                raise ValueError("Embeddings have not been indexed")
            vector = np.asarray(query_vector, dtype=np.float32)
            if vector.ndim != 1 or vector.shape[0] != self.dense.shape[1] or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
                raise ValueError("Invalid query embedding")
            dense = self.dense @ (vector / np.linalg.norm(vector))
        allowed = np.array([document_ids is None or p.document_id in document_ids for p in self.passages])
        # Thresholds are heuristics, never probabilities or guarantees of relevance.
        # Character overlap alone matches unrelated English suffixes. Use it for
        # ranking, but require lexical evidence (or a dense match) for admission.
        relevant = lexical > 0
        if len(query) == 1:
            relevant |= np.array([query.lower() in p.text.lower() for p in self.passages])
        if dense is not None:
            relevant |= dense >= 0.45
        eligible = np.where(allowed & relevant)[0]
        if len(eligible) == 0:
            return []
        scores = np.zeros(len(self.passages))
        for channel in [lexical, char] + ([dense] if dense is not None else []):
            ranked = sorted(eligible, key=lambda i: (-float(channel[i]), self.passages[i].id))
            for rank, i in enumerate(ranked, 1):
                if channel[i] > 0:
                    scores[i] += 1 / (60 + rank)
        ranked = sorted(eligible, key=lambda i: (-scores[i], self.passages[i].id))[:top_k]
        return [Hit(self.passages[i], float(scores[i]), float(lexical[i]), float(char[i]), float(dense[i]) if dense is not None else None) for i in ranked]
