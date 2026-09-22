"""Small reproducible retrieval smoke benchmark, not an LLM quality score."""
import json

from .demo import CASES, DOCUMENTS
from .library import Library


def evaluate() -> dict:
    library = Library()
    for filename, text in DOCUMENTS.items():
        library.add(filename, text.encode("utf-8"))
    rows, reciprocal, found, negative_correct = [], 0.0, 0, 0
    for query, filename, phrase in CASES:
        hits = library.index.search(query, top_k=3)
        rank = next((i for i, hit in enumerate(hits, 1) if hit.passage.filename == filename and phrase in hit.passage.text), None) if filename else None
        if filename:
            found += rank is not None
            reciprocal += 1 / rank if rank else 0
        else:
            negative_correct += not hits
        rows.append({"question": query, "expected_document": filename, "rank_at_3": rank, "returned": len(hits)})
    positive = sum(filename is not None for _, filename, _ in CASES)
    negative = len(CASES) - positive
    return {"scope": "Synthetic retrieval smoke cases; not answer accuracy or a general benchmark", "answerable_cases": positive, "unanswerable_cases": negative, "hit_rate_at_3": found / positive, "mrr_at_3": reciprocal / positive, "no_result_rate_on_unanswerable": negative_correct / negative, "cases": rows}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
