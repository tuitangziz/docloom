"""Run with: python -m streamlit run app.py"""
import json

import streamlit as st

from docloom.answers import excerpt_answer, export_json, export_markdown, generate_answer, source_packet
from docloom.demo import DOCUMENTS
from docloom.evaluation import evaluate
from docloom.ingest import DocumentError
from docloom.library import Library
from docloom.providers import CompatibleAPI, OllamaProvider, ProviderError

st.set_page_config(page_title="Docloom · 文档有据可查", page_icon="📚", layout="wide")
st.html("""<style>
.stApp {background: #f8faf8;}
.block-container {max-width: 1240px; padding-top: 2.5rem;}
h1 {letter-spacing: -.045em; font-weight: 750 !important;}
h2,h3 {letter-spacing: -.025em;}
[data-testid="stSidebar"] {border-right: 1px solid #dfe8e1;}
[data-testid="stMetric"] {background: white; border: 1px solid #dde8e1; border-radius: 14px; padding: 16px 20px;}
[data-testid="stMetricValue"] {font-size: 1.7rem;}
[data-testid="stCode"] {border-radius: 10px;}
.eyebrow {font: 600 12px monospace; letter-spacing: .18em; color: #287565;}
.hero-note {color: #61736c; font-size: 17px; max-width: 740px; line-height: 1.7;}
</style>""")

if "library" not in st.session_state:
    st.session_state.library = Library()
    st.session_state.upload_epoch = 0
library = st.session_state.library


def invalidate_answer():
    for key in ("pending", "answer", "answer_question"):
        st.session_state.pop(key, None)


def clear_session():
    library.clear()
    invalidate_answer()
    st.session_state.upload_epoch += 1
    st.session_state.api_key = ""


with st.sidebar:
    st.markdown("## 📚 Docloom")
    st.caption("让回答回到原文。")
    st.markdown("#### 01 · 导入资料")
    uploaded = st.file_uploader("PDF / DOCX / Markdown / TXT", type=["pdf", "docx", "md", "txt"], accept_multiple_files=True, key=f"uploads_{st.session_state.upload_epoch}", help="每份最多 15 MiB；只处理本机服务收到的文件。扫描 PDF 需要先做 OCR。")
    if st.button("导入所选文档", disabled=not uploaded, use_container_width=True):
        for file in uploaded:
            try:
                doc, added = library.add(file.name, file.getvalue())
                if added:
                    invalidate_answer()
                st.success("已导入：" + doc.filename) if added else st.info("相同内容已存在：" + doc.filename)
                for warning in doc.warnings:
                    st.warning(warning)
            except (DocumentError, ValueError) as exc:
                st.error(str(exc))
    if st.button("载入演示资料", use_container_width=True):
        try:
            for filename, text in DOCUMENTS.items():
                library.add(filename, text.encode("utf-8"))
            invalidate_answer()
            st.success("已载入 3 份虚构示例。")
        except (DocumentError, ValueError) as exc:
            st.error(str(exc))
    st.divider()
    st.markdown("#### 02 · 回答方式")
    mode = st.selectbox("模型连接", ["API 服务", "仅检索原文", "本地 Ollama"], key="provider_mode")
    if mode == "API 服务":
        api_base = st.text_input("Base URL", placeholder="https://your-provider.example/v1", key="api_base")
        api_model = st.text_input("模型名", placeholder="填写服务商提供的模型 ID", key="api_model")
        api_key = st.text_input("API Key", type="password", key="api_key")
        api_style = st.selectbox("请求格式", ["通用兼容（千问等）", "OpenAI 新版参数"], help="新版使用 developer 消息与 max_completion_tokens；通用兼容使用 system 与 max_tokens。")
        st.caption("兼容 Chat Completions 接口。密钥只保留在当前服务会话内，不保存到配置文件。")
    elif mode == "本地 Ollama":
        local_base = st.text_input("Ollama 地址", value="http://127.0.0.1:11434", key="local_base")
        local_model = st.text_input("本地模型名", value="qwen3.5:4b", key="local_model")
        st.caption("接口已预留。需自行安装 Ollama 并下载模型；本工具不会自动下载。建议设置 OLLAMA_NO_CLOUD=1。")
    st.divider()
    st.button("清空文档、回答和密钥", on_click=clear_session, use_container_width=True)
    st.caption("文档保存在会话内存。刷新或重启可能丢失；操作系统可能使用交换文件。")

st.html('<div class="eyebrow">DOCLOOM / DOCUMENT WORKSPACE</div>')
st.title("你的资料，回答的依据。")
st.html('<p class="hero-note">导入资料、找到证据，再让模型整理回答。每条引用都可以展开核对，来源不再藏在答案后面。</p>')
cols = st.columns(3)
cols[0].metric("资料库", f"{len(library.documents)} 份")
cols[1].metric("可检索片段", len(library.index.passages) if library.index else 0)
cols[2].metric("当前方式", mode)
st.write("")
qa_tab, library_tab, eval_tab, privacy_tab = st.tabs(["问答工作台", "原文与文档库", "检索评测", "数据流与隐私"])


def show_sources(hits):
    for i, hit in enumerate(hits, 1):
        with st.expander(f"S{i} · {hit.passage.filename} · {hit.passage.location}", expanded=i == 1):
            st.text(hit.passage.text)
            st.caption(f"BM25 {hit.lexical_score:.3f} · 字符相似度 {hit.char_score:.3f} · 排名融合 {hit.score:.4f}（均非正确率）")


with qa_tab:
    if not library.documents:
        st.info("从左侧导入你的资料，或点击「载入演示资料」立即体验。无需密钥也可以检索。")
    st.markdown("### 先找到值得引用的内容")
    with st.form("question_form"):
        question = st.text_area("你想了解什么？", placeholder="例如：GPU 工作站需要提前多久预约？使用后有哪些要求？", max_chars=2000, height=100, key="question_input")
        a, b = st.columns([3, 1])
        with a:
            doc_ids = st.multiselect("检索范围（留空表示全部资料）", options=list(library.documents), format_func=lambda key: library.documents[key].filename)
        with b:
            top_k = st.slider("最多引用片段数", 1, 8, 4)
        submitted = st.form_submit_button("检索资料", type="primary", disabled=library.index is None)
    if submitted:
        invalidate_answer()
        if not question.strip():
            st.warning("请先输入问题。")
        else:
            hits = library.index.search(question, top_k=top_k, document_ids=set(doc_ids) if doc_ids else None)
            st.session_state.pending = {"question": question.strip(), "hits": hits}
            st.session_state.answer = excerpt_answer(hits)
            st.session_state.answer_question = question.strip()
    pending = st.session_state.get("pending")
    if pending:
        hits = pending["hits"]
        st.caption("当前检索问题：")
        st.text(pending["question"])
        left, right = st.columns([1.15, 1], gap="large")
        with right:
            st.markdown("### 原文证据")
            show_sources(hits)
        with left:
            if hits and mode != "仅检索原文":
                st.markdown("### 用这些片段生成回答")
                if mode == "API 服务":
                    st.info("点击下方按钮后，问题和右侧片段将发送到你配置的 API。原始文件和文件名不会随请求发送；片段正文仍可能含有隐私。")
                else:
                    st.info("问题和片段将发送到你配置的本机 Ollama 服务。")
                with st.expander("查看即将发送的用户消息"):
                    st.json(source_packet(pending["question"], hits))
                if st.button("发送片段并生成回答", type="primary"):
                    try:
                        provider = CompatibleAPI(api_base, api_model, api_key, modern_parameters=api_style == "OpenAI 新版参数") if mode == "API 服务" else OllamaProvider(local_base, local_model)
                        with st.spinner("模型正在整理回答…"):
                            st.session_state.answer = generate_answer(pending["question"], hits, provider)
                    except ProviderError as exc:
                        st.error(str(exc))
            answer = st.session_state.get("answer")
            if answer:
                st.markdown("### " + answer.mode)
                # Plain text avoids executing remote image URLs or untrusted HTML/Markdown.
                st.text(answer.text)
                for warning in answer.warnings:
                    st.warning(warning)
                if answer.mode == "模型回答":
                    for citation in answer.citations:
                        st.caption(f"[{citation.label}] {citation.filename} · {citation.location}")
                        st.text(citation.quote)
                da, db = st.columns(2)
                da.download_button("导出 Markdown", export_markdown(pending["question"], answer), "docloom-answer.md", "text/markdown")
                db.download_button("导出 JSON", export_json(pending["question"], answer), "docloom-answer.json", "application/json")

with library_tab:
    st.markdown("### 文档是可以检查的")
    st.caption("PDF 按物理页码定位，Word 按正文段落或表格行定位，文本按段落起始行定位。")
    if library.documents:
        selected = st.selectbox("查看文档", list(library.documents), format_func=lambda key: library.documents[key].filename)
        document = library.documents[selected]
        st.caption(f"{document.kind.upper()} · {document.byte_size / 1024:.1f} KiB · {len(document.passages)} 个片段")
        for warning in document.warnings:
            st.warning(warning)
        needle = st.text_input("在该文档内筛选文字")
        passages = [p for p in document.passages if needle.lower() in p.text.lower()]
        st.caption(f"匹配 {len(passages)} 个片段；每次最多展示前 50 个。")
        for passage in passages[:50]:
            with st.expander(passage.location):
                st.text(passage.text)
        if st.button("移除这份文档"):
            library.remove({selected})
            invalidate_answer()
            st.session_state.upload_epoch += 1
            st.rerun()
    else:
        st.info("还没有导入资料。")

with eval_tab:
    st.markdown("### 给检索一个可复现的检查")
    st.write("使用 3 份虚构资料、10 个有答案问题和 2 个无答案问题，检查相关片段能否进入前 3 名。仅测试检索，不调用 API，也不读取你的文档。")
    if st.button("运行内置检索评测"):
        report = evaluate()
        e1, e2, e3 = st.columns(3)
        e1.metric("Hit rate @3", f"{report['hit_rate_at_3']:.0%}")
        e2.metric("MRR @3", f"{report['mrr_at_3']:.3f}")
        e3.metric("无答案问题无结果率", f"{report['no_result_rate_on_unanswerable']:.0%}")
        st.dataframe(report["cases"], hide_index=True, use_container_width=True)
        st.download_button("下载评测结果", json.dumps(report, ensure_ascii=False, indent=2), "retrieval-evaluation.json", "application/json")
    st.caption("这是一组小型冒烟测试，不代表通用检索质量或模型回答准确率。")

with privacy_tab:
    st.markdown("### 你可以看清数据去了哪里")
    st.markdown("1. 文件通过浏览器传给本机 Python 服务，在会话内解析和检索。\n2. API 模式只在你点击生成时发送问题和选出的原文片段，供应商的数据处理规则适用。\n3. Ollama 模式连接回环地址；请使用可信的本地运行组件并关闭云模型。\n4. 程序不主动保存文档、密钥、聊天记录或索引，没有内置遥测；系统、浏览器和供应商仍可能留下各自的记录。")
    st.warning("原文引用匹配只能确认文字确实存在，不能证明推论正确。请核对重要结论。")
    st.caption("本工具面向个人电脑，不含多用户鉴权。保持监听 127.0.0.1，不要直接发布到公网。请只导入可信文件。")
