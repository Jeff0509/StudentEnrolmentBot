
import csv
import hashlib

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
VECTOR_DB_DIR = PROJECT_ROOT / "vector_db"

# Local embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunk settings
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# ChromaDB collection
COLLECTION_NAME = "enrolment_knowledge"


def get_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


def get_collection():
    client = chromadb.PersistentClient(
        path=str(VECTOR_DB_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    return collection


# -------------------------------------------------
# Document readers
# -------------------------------------------------

def read_pdf(file_path):
    reader = PdfReader(str(file_path))
    results = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            results.append({
                "text": text,
                "location": f"Page {page_number}"
            })

    return results


def read_docx(file_path):
    document = Document(str(file_path))

    text_parts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    # Also extract Word table contents
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells]
            text_parts.append(" | ".join(values))

    return [{
        "text": "\n".join(text_parts),
        "location": "Document"
    }]


def read_txt(file_path):
    text = file_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    return [{
        "text": text,
        "location": "Text file"
    }]


def read_csv(file_path):
    results = []

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline=""
    ) as file:

        reader = csv.reader(file)

        headers = next(reader, [])

        for row_number, row in enumerate(reader, start=2):
            results.append({
                "text": (
                    "Columns: " + " | ".join(headers)
                    + "\nValues: " + " | ".join(row)
                ),
                "location": f"Row {row_number}"
            })

    return results


def read_xlsx(file_path):
    workbook = load_workbook(
        filename=file_path,
        read_only=True,
        data_only=True
    )

    results = []

    for sheet in workbook.worksheets:

        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            continue

        headers = [
            str(value) if value is not None else ""
            for value in rows[0]
        ]

        for row_number, row in enumerate(rows[1:], start=2):

            values = [
                str(value) if value is not None else ""
                for value in row
            ]

            if any(values):
                results.append({
                    "text": (
                        f"Sheet: {sheet.title}\n"
                        f"Columns: {' | '.join(headers)}\n"
                        f"Values: {' | '.join(values)}"
                    ),
                    "location": (
                        f"Sheet {sheet.title}, Row {row_number}"
                    )
                })

    workbook.close()
    return results


def read_document(file_path):

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(file_path)

    if extension == ".docx":
        return read_docx(file_path)

    if extension in [".txt", ".md"]:
        return read_txt(file_path)

    if extension == ".csv":
        return read_csv(file_path)

    if extension == ".xlsx":
        return read_xlsx(file_path)

    return []


# -------------------------------------------------
# Text chunking
# -------------------------------------------------

def split_into_chunks(text):

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


# -------------------------------------------------
# Document ingestion
# -------------------------------------------------

def ingest_documents():

    if not DOCUMENTS_DIR.exists():
        DOCUMENTS_DIR.mkdir(parents=True)

    model = get_embedding_model()
    collection = get_collection()

    supported_extensions = {
        ".pdf", ".docx", ".txt",
        ".md", ".csv", ".xlsx"
    }

    files = [
        file for file in DOCUMENTS_DIR.rglob("*")
        if file.is_file()
        and file.suffix.lower() in supported_extensions
    ]

    if not files:
        print("No supported documents found.")
        print(f"Please add documents to: {DOCUMENTS_DIR}")
        return

    total_chunks = 0

    for file_path in files:

        relative_path = file_path.relative_to(
            DOCUMENTS_DIR
        ).as_posix()

        print(f"\nProcessing: {relative_path}")

        # Remove previous chunks for this file
        collection.delete(
            where={"source": relative_path}
        )

        pages = read_document(file_path)

        documents = []
        metadatas = []
        ids = []

        for page in pages:

            chunks = split_into_chunks(
                page["text"]
            )

            for index, chunk in enumerate(chunks):

                unique_id = hashlib.sha256(
                    f"{relative_path}:{index}".encode("utf-8")
                ).hexdigest()

                ids.append(unique_id)
                documents.append(chunk)

                metadatas.append({
                    "source": relative_path,
                    "location": page["location"],
                    "chunk": index
                })

        if not documents:
            print("No extractable text found.")
            continue

        embeddings = model.encode(
            documents,
            show_progress_bar=False
        ).tolist()

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        total_chunks += len(documents)

        print(f"Chunks created: {len(documents)}")

    print("\n--------------------------------")
    print("DOCUMENT INGESTION COMPLETE")
    print("--------------------------------")
    print(f"Documents scanned: {len(files)}")
    print(f"Chunks processed: {total_chunks}")
    print(f"Total chunks in database: {collection.count()}")


# -------------------------------------------------
# Semantic search
# -------------------------------------------------

def search_knowledge(question, top_k=5):

    model = get_embedding_model()
    collection = get_collection()

    if collection.count() == 0:
        print("Knowledge base is empty.")
        return []

    query_embedding = model.encode(
        [question]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    matches = []

    for i, document in enumerate(results["documents"][0]):

        matches.append({
            "text": document,
            "source": results["metadatas"][0][i]["source"],
            "location": results["metadatas"][0][i]["location"],
            "distance": results["distances"][0][i]
        })

    return matches


# -------------------------------------------------
# Test
# -------------------------------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "search":

        question = " ".join(sys.argv[2:])

        if not question:
            question = "What's the main profit of the business?"

        matches = search_knowledge(question)

        print("\nRAG SEARCH RESULTS")
        print("--------------------------------")

        for index, match in enumerate(matches, start=1):

            print(f"\nResult {index}")
            print(f"Source: {match['source']}")
            print(f"Location: {match['location']}")
            print(f"Distance: {match['distance']:.4f}")
            print(f"Content:\n{match['text']}")

    else:
        ingest_documents()
