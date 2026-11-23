"""Document ingestion and chunking for the compliance knowledge base."""

import hashlib
import re
from pathlib import Path

import chromadb
from src.config import AppConfig
from src.models import get_embedding_function


def parse_document_metadata(content: str, file_path: str) -> dict:
    """Extract metadata from the document header."""
    metadata = {"source_file": Path(file_path).name}

    patterns = {
        "document_id": r"\*\*Document ID:\*\*\s*(.+)",
        "version": r"\*\*Version:\*\*\s*(.+)",
        "effective_date": r"\*\*Effective Date:\*\*\s*(.+)",
        "last_reviewed": r"\*\*Last Reviewed:\*\*\s*(.+)",
        "owner": r"\*\*Owner:\*\*\s*(.+)",
        "classification": r"\*\*Classification:\*\*\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1).strip()

    title_match = re.match(r"#\s+(.+)", content)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    return metadata


def chunk_document(content: str, chunk_size: int = 800, chunk_overlap: int = 200) -> list[dict]:
    """Split a document into chunks, respecting section boundaries."""
    sections = re.split(r"\n(?=##\s)", content)
    chunks = []
    current_section = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        section_title_match = re.match(r"##\s+(.+)", section)
        section_title = section_title_match.group(1) if section_title_match else ""

        if len(section) <= chunk_size:
            chunks.append({
                "text": section,
                "section": section_title,
            })
        else:
            paragraphs = section.split("\n\n")
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) > chunk_size and current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "section": section_title,
                    })
                    overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = current_chunk + "\n\n" + para if current_chunk else para

            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "section": section_title,
                })

    return chunks


def generate_chunk_id(doc_id: str, chunk_index: int) -> str:
    raw = f"{doc_id}_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_documents(config: AppConfig, documents_dir: str = "src/knowledge/documents") -> int:
    """Ingest all markdown documents from the directory into ChromaDB."""
    client = chromadb.PersistentClient(path=config.chroma.persist_dir)
    embedding_fn = get_embedding_function(config)

    collection = client.get_or_create_collection(
        name=config.chroma.collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids = set(collection.get()["ids"]) if collection.count() > 0 else set()

    docs_path = Path(documents_dir)
    total_chunks = 0

    for md_file in sorted(docs_path.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        doc_metadata = parse_document_metadata(content, str(md_file))
        doc_id = doc_metadata.get("document_id", md_file.stem)

        chunks = chunk_document(content)

        ids = []
        texts = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = generate_chunk_id(doc_id, i)

            if chunk_id in existing_ids:
                continue

            ids.append(chunk_id)
            texts.append(chunk["text"])
            metadatas.append({
                **doc_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "section": chunk.get("section", ""),
            })

        if ids:
            collection.add(documents=texts, ids=ids, metadatas=metadatas)
            total_chunks += len(ids)
            print(f"Ingested {len(ids)} chunks from {md_file.name} (doc_id={doc_id})")
        else:
            print(f"Skipped {md_file.name} — already ingested")

    print(f"Total: {total_chunks} new chunks ingested. Collection size: {collection.count()}")
    return total_chunks


if __name__ == "__main__":
    from src.config import load_config
    config = load_config()
    ingest_documents(config)
