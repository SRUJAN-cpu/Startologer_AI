"""
Document Parser Agent - Responsible for document ingestion and extraction
Uses Document AI for advanced parsing with PyPDF2 fallback
"""

import os
import sys
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.documentai_service import get_documentai_service
from textExtraction.textExtractor import extract_text


class DocumentParserAgent:
    """
    Agent responsible for parsing and extracting information from documents
    Uses Google Document AI for advanced extraction, falls back to textExtractor
    """

    def __init__(self):
        self.documentai_service = get_documentai_service()
        self.name = "DocumentParserAgent"

    def process(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Process multiple documents and extract structured information

        Args:
            file_paths: List of file paths to process

        Returns:
            Dict containing:
                - combined_text: All extracted text combined
                - files_processed: List of processed files with metadata
                - entities: Aggregated entities from all documents
                - tables: Aggregated tables from all documents
                - metrics: Extracted key metrics
                - method: Processing method used
        """
        combined_text_parts = []
        all_entities = []
        all_tables = []
        files_processed = []
        processing_methods = set()

        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)

                # Determine MIME type
                mime_type = self._get_mime_type(file_path)

                # Use Document AI for PDFs and images
                if mime_type in ["application/pdf", "image/png", "image/jpeg", "image/tiff"]:
                    result = self.documentai_service.process_document(file_path, mime_type)
                    text = result.get("text", "")
                    entities = result.get("entities", [])
                    tables = result.get("tables", [])
                    method = result.get("method", "unknown")
                    metadata = result.get("metadata", {})
                else:
                    # Fall back to textExtractor for other formats (PPTX, DOCX, TXT)
                    text = extract_text(file_path)
                    entities = []
                    tables = []
                    method = "textextractor"
                    metadata = {"file_type": mime_type}

                if text and text.strip():
                    combined_text_parts.append(f"==== {filename} ====\n{text}")
                    processing_methods.add(method)

                    files_processed.append({
                        "filename": filename,
                        "method": method,
                        "entities_count": len(entities),
                        "tables_count": len(tables),
                        "text_length": len(text),
                        "metadata": metadata
                    })

                    all_entities.extend(entities)
                    all_tables.extend(tables)

            except Exception as e:
                # Silently handle processing errors
                pass
                files_processed.append({
                    "filename": os.path.basename(file_path),
                    "error": str(e),
                    "method": "error"
                })

        combined_text = "\n\n".join(combined_text_parts)

        # Extract key metrics from entities
        key_metrics = self.documentai_service.extract_key_metrics(all_entities)

        result = {
            "combined_text": combined_text,
            "files_processed": files_processed,
            "entities": all_entities,
            "tables": all_tables,
            "key_metrics": key_metrics,
            "methods_used": list(processing_methods),
            "total_text_length": len(combined_text),
            "agent": self.name
        }

        return result

    def _get_mime_type(self, file_path: str) -> str:
        """Determine MIME type from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain"
        }
        return mime_types.get(ext, "application/octet-stream")
