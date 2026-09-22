# Third-party software

Docloom source is MIT licensed. Dependencies are installed separately and retain their licenses. No model weights or third-party document collections are bundled.

| Direct dependency | Purpose | Project |
| --- | --- | --- |
| Streamlit | Local web UI and AppTest | https://github.com/streamlit/streamlit |
| pypdf | PDF text extraction | https://github.com/py-pdf/pypdf |
| python-docx | Word body and table extraction | https://github.com/python-openxml/python-docx |
| scikit-learn | Sparse character TF-IDF | https://github.com/scikit-learn/scikit-learn |
| NumPy | Ranking/vector operations | https://github.com/numpy/numpy |
| rank-bm25 | BM25 retrieval | https://github.com/dorianbrown/rank_bm25 |
| HTTPX | API transport | https://github.com/encode/httpx |
| Pydantic | Model-output validation | https://github.com/pydantic/pydantic |
| pytest | Tests | https://github.com/pytest-dev/pytest |
| ReportLab | Synthetic in-memory PDF test fixtures | https://www.reportlab.com/ |

Consult each upstream distribution's LICENSE for redistribution obligations, including transitive dependencies. API services and optional models have separate terms/licenses. The built-in demo documents are fictional text authored for this repository.
