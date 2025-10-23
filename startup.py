import os
import re
import uuid
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

import fitz  # PyMuPDF
import pdfplumber
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

app = FastAPI()

CHROMA_DIR = "chromadb_store"
DOCUMENTS_DIR = "docs"
MARKDOWN_DIR = "markdowns"
EMBED_MODEL = "BAAI/bge-large-en-v1.5"

os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(MARKDOWN_DIR, exist_ok=True)

embedder = SentenceTransformer(EMBED_MODEL)
chromadb_client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))

def sanitize_collection_name(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r'[^a-zA-Z0-9._-]', '', name)
    name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
    name = re.sub(r'[^a-zA-Z0-9]+$', '', name)
    if len(name) < 3:
        name = "col_" + name
    if len(name) > 512:
        name = name[:512]
    return name

def advanced_clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    freq_lines = {}
    for line in lines:
        freq_lines[line] = freq_lines.get(line, 0) + 1
    repeated_lines = set(line for line, count in freq_lines.items() if count > 3)
    filtered_lines = [line for line in lines if line not in repeated_lines]
    filtered_text = "\n".join(filtered_lines)
    filtered_text = re.sub(r'(\bpage\b|\bp\b)?\.?\s*\b\d{1,3}\b(/?\d{1,3})?', '', filtered_text, flags=re.I)
    boilerplates = [
        r"copyright.*\d{4}",
        r"all rights reserved",
        r"this document is for",
        r"confidential",
        r"unauthorized use is prohibited"
    ]
    for pattern in boilerplates:
        filtered_text = re.sub(pattern, '', filtered_text, flags=re.I)
    filtered_text = re.sub(r'-\n', '', filtered_text)
    filtered_text = re.sub(r'\n+', '\n', filtered_text)
    paragraphs = [re.sub(r'\s+', ' ', para.strip()) for para in filtered_text.split('\n') if para.strip()]
    cleaned_text = "\n\n".join(paragraphs)
    return cleaned_text

def chunk_text(text: str, max_words=300) -> List[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    for w in words:
        current_chunk.append(w)
        if len(current_chunk) >= max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def extract_tables_from_pdf_page(pdf_path: str, page_num: int) -> List[str]:
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                raw_tables = page.extract_tables()
                for tbl in raw_tables:
                    if tbl:
                        tbl_str = "\n".join([" | ".join(str(cell or "") for cell in row) for row in tbl])
                        tables.append(tbl_str)
    except Exception as e:
        print(f"Error extracting tables from page {page_num}: {e}")
    return tables

def pdf_to_markdown(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    md = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # First try standard text extraction
        raw_text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES)
        
        cleaned_text = advanced_clean_text(raw_text)

        # Fallback: if cleaned_text is empty, try blocks extraction
        if not cleaned_text.strip():
            blocks = page.get_text("blocks")
            text_blocks = [block[4] for block in blocks if block[4].strip()]
            cleaned_text = "\n\n".join([advanced_clean_text(tb) for tb in text_blocks if tb.strip()])
        
        tables = extract_tables_from_pdf_page(pdf_path, page_num)
        md.append(f"# Page {page_num + 1}\n")
        if cleaned_text.strip():
            md.append(cleaned_text + "\n")
        else:
            md.append("_No extractable text found on this page._\n")

        if tables:
            md.append("## Tables\n")
            for i, table in enumerate(tables, start=1):
                md.append(f"### Table {i}\n``````\n")
    return "\n".join(md)

def embed_markdown_and_store(chunks: List[str], collection_name: str) -> int:
    collection = chromadb_client.get_or_create_collection(name=collection_name)
    count = 0
    for chunk in chunks:
        embedding = embedder.encode(chunk).tolist()
        metadata = {"source": "markdown_chunk"}
        collection.add(
            documents=[chunk],
            metadatas=[metadata],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())]
        )
        count += 1
    return count

@app.post("/upload_markdown", summary="Upload PDF, convert to markdown, embed markdown, and store")
async def upload_markdown(
    file: UploadFile = File(...),
    collection_name: str = Form(...)
):
    if not collection_name.strip():
        raise HTTPException(status_code=400, detail="Collection name cannot be empty.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    pdf_path = os.path.join(DOCUMENTS_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    markdown_text = pdf_to_markdown(pdf_path)
    md_name = f"{Path(file.filename).stem}.md"
    md_path = os.path.join(MARKDOWN_DIR, md_name)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    safe_collection_name = sanitize_collection_name(collection_name)
    chunks = chunk_text(markdown_text)
    count = embed_markdown_and_store(chunks, safe_collection_name)
    return JSONResponse({
        "message": f"Uploaded PDF, converted to markdown, embedded {count} chunks into collection '{safe_collection_name}'.",
        "markdown_file": md_name,
        "pdf_file": file.filename,
    })

@app.get("/list_collections", summary="List ChromaDB collections")
def list_collections():
    try:
        collections = chromadb_client.list_collections()
        return {"collections": [c.name for c in collections]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_collection/{collection_name}", summary="Delete ChromaDB collection")
def delete_collection(collection_name: str):
    try:
        chromadb_client.delete_collection(name=collection_name)
        return {"message": f"Deleted collection '{collection_name}' successfully."}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
