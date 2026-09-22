# Contributing

Start with a reproducible problem and a small, fictional document. Include input format, Python version, expected result and actual behavior. Do not attach private documents, full local paths, credentials or raw provider logs.

Install with `python -m pip install -e ".[test]"`; run `python -m pytest -q` and `python -m docloom.evaluation`. Add tests for meaningful parsing, retrieval, privacy or provider behavior changes. Keep generated fixtures in memory or ignored temporary directories.

New providers should implement the `ChatProvider` protocol. Preserve explicit review before remote submission, safe errors and exact-quote validation. Report actual provider/model verification separately from mocked contract tests.

Before your first commit, configure your repository author email to the GitHub noreply address shown in your GitHub email settings. Run `python scripts/install_git_hooks.py` to install the optional local privacy guards, and inspect the staged diff. Hooks are an extra guard, not a guarantee that content is safe to publish.

Use demo data with empty credentials for screenshots. Save sharp PNGs at the original browser capture resolution; do not upscale a blurry image. To replace the README image, replace `docs/screenshot.jpg`, inspect the diff and metadata, then commit and push. GitHub displays the committed file.
