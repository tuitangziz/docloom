"""Bounded UTF-8/PDF/DOCX parsing. No input files are written to disk."""
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import re
import zipfile

from docx import Document as WordDocument
from docx.table import Table
from pypdf import PdfReader

from .models import Document, Passage

MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_TEXT_CHARS = 1_500_000
MAX_PAGES = 300
MAX_PASSAGES = 4000
SUPPORTED = {".pdf", ".docx", ".md", ".txt"}


class DocumentError(ValueError):
    """An input cannot be processed within the documented limits."""


def display_name(name: str) -> str:
    name = PurePosixPath(str(name).replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:180] or "document.txt"


def split_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    if not 0 <= overlap < size:
        raise ValueError("overlap must be smaller than the chunk size")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Prefer a nearby paragraph or sentence boundary without dropping text.
            boundary = max(text.rfind(mark, start + size // 2, end) for mark in ("\n", "。", ". ", "！", "？"))
            if boundary > start:
                end = boundary + 1
        part = text[start:end].strip()
        if part:
            chunks.append(part)
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _word_units(data: bytes):
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2500 or sum(e.file_size for e in entries) > 60 * 1024 * 1024:
                raise DocumentError("DOCX 解压后过大，已拒绝处理。")
            if "word/document.xml" not in archive.namelist():
                raise DocumentError("不是有效的 DOCX 文档。")
        doc = WordDocument(BytesIO(data))
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("DOCX 无法读取，请检查文件是否完整。") from exc
    paragraph, table_number = 0, 0
    for block in doc.iter_inner_content():
        if isinstance(block, Table):
            table_number += 1
            for row_number, row in enumerate(block.rows, 1):
                yield f"表格 {table_number} · 行 {row_number}", " | ".join(cell.text for cell in row.cells)
        else:
            paragraph += 1
            yield f"段落 {paragraph}", block.text


def parse_document(name: str, data: bytes) -> Document:
    name = display_name(name)
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise DocumentError("支持 PDF、DOCX、Markdown 和 TXT 文件。")
    if not data or len(data) > MAX_FILE_BYTES:
        raise DocumentError("文件为空或超过 15 MiB。")
    document_id = sha256(data).hexdigest()[:20]
    warnings, units = [], []
    if suffix == ".pdf":
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("暂不处理加密 PDF，请先导出不加密的副本。")
            if len(reader.pages) > MAX_PAGES:
                raise DocumentError("PDF 超过 300 页，请先拆分。")
            empty = 0
            total = 0
            for page_number, page in enumerate(reader.pages, 1):
                contents = page.get_contents()
                if contents and len(contents.get_data()) > 10 * 1024 * 1024:
                    raise DocumentError("PDF 单页内容流过大，请压缩或拆分后重试。")
                text = page.extract_text() or ""
                total += len(text)
                if total > MAX_TEXT_CHARS:
                    raise DocumentError("提取文本超过 150 万字符，请拆分文档。")
                if not text.strip():
                    empty += 1
                units.append((f"PDF 第 {page_number} 页", text))
            if empty:
                warnings.append(f"{empty} 页没有可提取文字；扫描页需先做 OCR，本工具不含 OCR。")
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("PDF 解析失败，请尝试重新导出。") from exc
    elif suffix == ".docx":
        units = list(_word_units(data))
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentError("文本文件需使用 UTF-8 编码。") from exc
        if "\x00" in text:
            raise DocumentError("文件包含二进制数据，不是受支持的文本。")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Keep paragraph line numbers rather than inventing PDF-style pages.
        for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text):
            start_line = text.count("\n", 0, match.start()) + 1
            units.append((f"起始行 {start_line}", match.group()))
    if sum(len(text) for _, text in units) > MAX_TEXT_CHARS:
        raise DocumentError("提取文本超过 150 万字符，请拆分文档。")
    passages = []
    for location, text in units:
        for index, chunk in enumerate(split_text(text), 1):
            passages.append(Passage(f"{document_id}:{len(passages) + 1}", document_id, name, f"{location} · 片段 {index}", chunk))
            if len(passages) > MAX_PASSAGES:
                raise DocumentError("文档片段过多，请拆分后导入。")
    if not passages:
        raise DocumentError("没有可提取的文字。扫描文档需要先做 OCR。")
    return Document(document_id, name, suffix[1:], len(data), passages, warnings)
