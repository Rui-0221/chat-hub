from __future__ import annotations

import asyncio
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.core.config import settings


HANDBOOK_VERSION = "V1.0-demo"
HANDBOOK_EFFECTIVE_DATE = "2026-08-24"


@lru_cache(maxsize=1)
def get_handbook_store() -> Chroma:
    settings.chroma_directory.mkdir(parents=True, exist_ok=True)
    embeddings = OllamaEmbeddings(
        model=settings.embedding_model,
        keep_alive=3_600,
    )
    return Chroma(
        collection_name=settings.chroma_collection,
        persist_directory=str(settings.chroma_directory),
        embedding_function=embeddings,
        create_collection_if_not_exists=True,
    )


def load_handbook_documents(path: Path | None = None) -> list[Document]:
    handbook_path = path or settings.handbook_path
    text = handbook_path.read_text(encoding="utf-8")

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "document"),
            ("##", "policy"),
            ("###", "section"),
        ],
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)
    chunk_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        separators=["\n### ", "\n## ", "\n\n", "\n", "。", "；", "，", ""],
    )
    chunks = chunk_splitter.split_documents(sections)

    for index, document in enumerate(chunks):
        document.metadata.update(
            {
                "source": handbook_path.name,
                "version": HANDBOOK_VERSION,
                "effective_date": HANDBOOK_EFFECTIVE_DATE,
                "chunk_index": index,
            }
        )
    return chunks


def stable_document_id(document: Document) -> str:
    identity = "|".join(
        [
            document.metadata.get("source", "handbook"),
            document.metadata.get("policy", ""),
            document.metadata.get("section", ""),
            document.page_content,
        ]
    )
    return sha256(identity.encode("utf-8")).hexdigest()


def seed_handbook() -> tuple[int, int]:
    """Upsert current chunks, then remove stale chunks without emptying the store first."""
    store = get_handbook_store()
    documents = load_handbook_documents()
    document_ids = [stable_document_id(document) for document in documents]
    current = store.get()
    previous_ids = set(current.get("ids", []))

    store.add_documents(documents, ids=document_ids)
    stale_ids = previous_ids.difference(document_ids)
    if stale_ids:
        store.delete(ids=sorted(stale_ids))
    return len(documents), len(stale_ids)


async def search_handbook(question: str, *, limit: int = 4) -> str:
    store = get_handbook_store()
    documents = await asyncio.to_thread(store.similarity_search, question, k=limit)
    if not documents:
        return "知识库尚未建立，请先运行公司手册索引脚本。"

    excerpts: list[str] = []
    for document in documents:
        policy = document.metadata.get("policy", "公司员工手册")
        section = document.metadata.get("section")
        heading = f"{policy} / {section}" if section else str(policy)
        excerpts.append(
            f"【{heading}｜版本 {document.metadata.get('version', HANDBOOK_VERSION)}】\n"
            f"{document.page_content}"
        )
    return "\n\n".join(excerpts)
