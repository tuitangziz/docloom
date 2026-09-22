# Docloom

**Find the evidence before asking the model.** A personal document Q&A workspace with local parsing and retrieval, opt-in API generation, and an Ollama adapter for future local deployment.

[中文 README](README.md) · [Privacy](docs/privacy.md) · [Architecture](docs/architecture.md)

![Docloom workflow: local retrieval, review excerpts, inspect citations](docs/overview.svg)

[View the actual workspace screenshot](docs/screenshot.jpg) (fictional demo data; no real API connected).

Import PDF, DOCX, Markdown or UTF-8 text; retrieve with BM25 + character TF-IDF rank fusion; inspect the outgoing excerpts; then ask your configured Chat Completions API to produce a cited answer. Quoted text is checked against source passages. Invalid citations or API errors fall back to search results. Export notes as Markdown or JSON.

## Run locally

Python 3.11+ is required. No Docker, GPU or model download is needed for search or API mode.

```bash
git clone https://github.com/tuitangziz/docloom.git
cd docloom
python -m venv .venv
# Activate the virtual environment, then:
python -m pip install -e .
python -m streamlit run app.py
```

Open http://127.0.0.1:8501. Launch from the project directory so the loopback-only server and disabled Streamlit analytics settings take effect. Windows users can run `start.ps1`; Unix users can run `sh start.sh`.

Load the fictional demo or your own documents, enter a question, and retrieve evidence. For generation, enter your provider's Base URL (without `/chat/completions`), model ID and API key in the sidebar. Click the generation button only after reviewing the excerpts. Requests use Bearer authentication, `messages` and non-streaming output. Generic mode uses `system` and `max_tokens=1200`; the modern OpenAI option uses `developer` and `max_completion_tokens=1200`. Reasoning can consume that budget before a complete answer is returned. Vendor-specific or Responses-only endpoints are outside the initial compatibility scope.

## Data boundaries

Files are parsed in the local Python process, not solely in the browser. API mode sends the question and selected excerpts to the configured provider. Filenames and original file bytes are omitted, but excerpt text can still contain sensitive information. Provider policies apply.

The app does not intentionally persist documents, keys, chat or indexes. Session clearing removes its references, not forensic traces in browser/OS memory, swap or provider logs. There is no app telemetry; Streamlit usage statistics are disabled. Do not expose this unauthenticated personal app to the internet.

An Ollama adapter is available in the UI. Install a trusted runtime and local model yourself; use a loopback address and disable cloud support with `OLLAMA_NO_CLOUD=1`. Local transport and optional embedding interfaces have contract tests, but no real local model benchmark is claimed.

## Test and evaluate

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m docloom.evaluation
```

The bundled retrieval smoke set contains 10 answerable and 2 unanswerable questions over 3 fictional documents. Hit rate@3 and MRR@3 are 1.0 on this tiny set; both unanswerable queries return no passages. This is not general retrieval quality or LLM answer accuracy. API tests use simulated responses; bring your own credentials for a real provider check.

Limits: no OCR, no persistent knowledge base, no multi-user authentication, no multi-turn memory. DOCX body paragraphs/tables only. Lexical retrieval can miss paraphrases. Exact quote matching does not validate semantic correctness or eliminate prompt injection. Use trusted files and review important answers.

MIT licensed. See [third-party notices](THIRD_PARTY.md) and [contribution guidance](CONTRIBUTING.md).
