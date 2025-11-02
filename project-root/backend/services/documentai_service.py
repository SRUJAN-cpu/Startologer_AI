"""
Document AI Service - Advanced document processing with Google Document AI
Provides OCR, entity extraction, and structured data parsing with PyPDF2 fallback
"""

import os
from typing import Dict, List, Optional, Tuple
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from PyPDF2 import PdfReader

class DocumentAIService:
    """
    Service for processing documents using Google Document AI with fallback to PyPDF2
    """

    def __init__(self):
        """Initialize Document AI client if credentials are available"""
        self.client = None
        self.processor_id = None
        self.project_id = None
        self.location = None
        self.enabled = False

        try:
            self.project_id = os.getenv('GCP_PROJECT_ID')
            self.location = os.getenv('GCP_REGION', 'us-central1')
            self.processor_id = os.getenv('DOCUMENTAI_PROCESSOR_ID')

            if self.project_id and self.processor_id:
                # Initialize Document AI client
                opts = ClientOptions(api_endpoint=f"{self.location}-documentai.googleapis.com")
                self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
                self.enabled = True
                print(f"[DocumentAI] Initialized successfully (project={self.project_id}, location={self.location})")
            else:
                print("[DocumentAI] Not configured. Missing GCP_PROJECT_ID or DOCUMENTAI_PROCESSOR_ID. Using PyPDF2 fallback.")
        except Exception as e:
            print(f"[DocumentAI] Initialization failed: {e}. Using PyPDF2 fallback.")
            self.enabled = False

    def process_document(self, file_path: str, mime_type: str = "application/pdf") -> Dict:
        """
        Process a document using Document AI or fallback to PyPDF2

        Args:
            file_path: Path to the document file
            mime_type: MIME type of the document

        Returns:
            Dict containing:
                - text: Extracted text content
                - entities: List of detected entities (name, type, confidence)
                - tables: List of extracted tables
                - metadata: Document metadata
                - method: 'documentai' or 'pypdf2'
        """
        if self.enabled:
            try:
                return self._process_with_documentai(file_path, mime_type)
            except Exception as e:
                print(f"[DocumentAI] Error processing {file_path}: {e}. Falling back to PyPDF2.")

        # Fallback to PyPDF2
        return self._process_with_pypdf2(file_path)

    def _process_with_documentai(self, file_path: str, mime_type: str) -> Dict:
        """Process document using Google Document AI"""
        # Read the file
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Build the processor name
        processor_name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"

        # Create the request
        raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
        request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

        # Process the document
        result = self.client.process_document(request=request)
        document = result.document

        # Extract text
        text = document.text

        # Extract entities
        entities = []
        for entity in document.entities:
            entities.append({
                "type": entity.type_,
                "mention_text": entity.mention_text,
                "confidence": entity.confidence,
                "normalized_value": entity.normalized_value.text if entity.normalized_value else None
            })

        # Extract tables
        tables = []
        for page in document.pages:
            for table in page.tables:
                table_data = []
                for row in table.body_rows:
                    row_data = []
                    for cell in row.cells:
                        cell_text = self._get_text_from_layout(document.text, cell.layout)
                        row_data.append(cell_text)
                    table_data.append(row_data)
                tables.append(table_data)

        # Extract metadata
        metadata = {
            "page_count": len(document.pages),
            "mime_type": mime_type,
            "language": document.pages[0].detected_languages[0].language_code if document.pages and document.pages[0].detected_languages else "en"
        }

        print(f"[DocumentAI] Processed {file_path}: {len(entities)} entities, {len(tables)} tables, {metadata['page_count']} pages")

        return {
            "text": text,
            "entities": entities,
            "tables": tables,
            "metadata": metadata,
            "method": "documentai"
        }

    def _process_with_pypdf2(self, file_path: str) -> Dict:
        """Fallback: Process PDF using PyPDF2"""
        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page in reader.pages:
                text_parts.append(page.extract_text())

            text = "\n\n".join(text_parts)

            print(f"[PyPDF2] Processed {file_path}: {len(reader.pages)} pages")

            return {
                "text": text,
                "entities": [],
                "tables": [],
                "metadata": {
                    "page_count": len(reader.pages),
                    "mime_type": "application/pdf",
                    "language": "unknown"
                },
                "method": "pypdf2"
            }
        except Exception as e:
            print(f"[PyPDF2] Error processing {file_path}: {e}")
            return {
                "text": "",
                "entities": [],
                "tables": [],
                "metadata": {"error": str(e)},
                "method": "pypdf2_error"
            }

    def _get_text_from_layout(self, document_text: str, layout: documentai.Document.Page.Layout) -> str:
        """Extract text from a layout element"""
        if not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""

        text_segments = []
        for segment in layout.text_anchor.text_segments:
            start_index = int(segment.start_index) if segment.start_index else 0
            end_index = int(segment.end_index) if segment.end_index else len(document_text)
            text_segments.append(document_text[start_index:end_index])

        return "".join(text_segments).strip()

    def extract_key_metrics(self, entities: List[Dict]) -> Dict:
        """
        Extract financial and business metrics from Document AI entities

        Args:
            entities: List of entities from Document AI

        Returns:
            Dict of extracted metrics (revenue, funding, dates, etc.)
        """
        metrics = {}

        for entity in entities:
            entity_type = entity.get("type", "").lower()
            mention_text = entity.get("mention_text", "")
            normalized = entity.get("normalized_value")

            # Extract money values
            if "money" in entity_type or "revenue" in entity_type or "funding" in entity_type:
                if normalized:
                    metrics.setdefault("financial_values", []).append({
                        "type": entity_type,
                        "value": normalized,
                        "raw": mention_text
                    })

            # Extract dates
            elif "date" in entity_type:
                if normalized:
                    metrics.setdefault("dates", []).append({
                        "type": entity_type,
                        "value": normalized,
                        "raw": mention_text
                    })

            # Extract organization names
            elif "organization" in entity_type or "company" in entity_type:
                metrics.setdefault("organizations", []).append(mention_text)

            # Extract person names (founders)
            elif "person" in entity_type:
                metrics.setdefault("people", []).append(mention_text)

        return metrics


# Global instance
_document_ai_service = None

def get_documentai_service() -> DocumentAIService:
    """Get or create the global DocumentAIService instance"""
    global _document_ai_service
    if _document_ai_service is None:
        _document_ai_service = DocumentAIService()
    return _document_ai_service
