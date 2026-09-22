# Architecture and extension points

The UI owns a `Library` in Streamlit session state. No module-level singleton stores user data.

| Module | Responsibility |
| --- | --- |
| `ingest.py` | Byte/file limits, PDF physical pages, DOCX body paragraphs/tables, UTF-8 text lines, overlapping chunks |
| `library.py` | Content-hash deduplication, atomic index replacement, deletion and session limits |
| `retrieval.py` | BM25Plus, char TF-IDF, reciprocal rank fusion; optional normalized local embedding channel |
| `providers.py` | `ChatProvider` protocol, compatible HTTP API, local Ollama, bounded response reads |
| `answers.py` | Evidence packet, JSON schema validation, exact quote checks, conservative fallback, exports |
| `demo.py` / `evaluation.py` | Invented corpus and reproducible retrieval smoke cases |
| `app.py` | Import, review-before-send, generation, sources, library and evaluation UI |

## Retrieval choices

Chinese character bigrams and English tokens feed BM25. Character 2–4-grams help order candidates. Character similarity alone is not sufficient to admit a candidate: unrelated words can share suffixes. A lexical match is required unless a supplied dense embedding meets the optional threshold. RRF combines positive channel ranks using `1/(60 + rank)`. Scores are not calibrated probabilities. These defaults favor small local collections and are deliberately inspectable.

Chunk boundaries stay within one PDF page, DOCX paragraph/table row or text paragraph, so each chunk has a meaningful source location. Chunks are at most 900 characters with up to 120 characters of overlap. Text locations identify the start of the parent paragraph, not the exact first character of every overlapping chunk. PDF physical pages can differ from printed page labels.

## New model adapters

Implement `complete(messages: list[dict[str, str]]) -> str` and return the assistant's text. Use `ProviderError` for safe user-facing errors. The answer engine handles structured content and citations independently of transport.

`CompatibleAPI` uses the Chat Completions wire format. Some providers require different output-limit parameters, reasoning switches or JSON-mode flags; extend this adapter rather than altering parsing and retrieval. Never silently retry a potentially billable request with a different payload.

`OllamaProvider` uses `/api/show` and `/api/chat`, and exposes `embed(texts)` for `/api/embed`. `HybridIndex.set_embeddings(vectors, model)` and `search(..., query_vector=...)` support a future local semantic retrieval UI. Build document/query vectors with the same model. This path is not enabled in the current UI and does not download weights.

## Answer validation is intentionally narrow

The prompt labels document content as data and offers no execution/browsing tools. JSON is parsed with Pydantic; every source ID must exist, every quote must match after whitespace normalization, and inline source markers must match cited IDs. A failure displays raw search evidence instead of presenting the invalid answer as verified.

A model can still draw a false conclusion from a real quote, overlook a relevant passage or be influenced by hostile text. Exact quote validation is a provenance check, not a proof of entailment. Future improvements should include adversarial evaluation, semantic citation checking and better retrieval, with separately reported metrics.
