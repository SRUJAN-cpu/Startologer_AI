import os
import requests
from PyPDF2 import PdfReader
from io import BytesIO
from dotenv import load_dotenv

class DocumentProcessor:
    def __init__(self):
        load_dotenv()
        # Gemini API settings
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    async def process_document(self, content: bytes, mime_type: str) -> str:
        """Extract text from PDF using PyPDF2 instead of Document AI"""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    async def analyze_text(self, text: str) -> str:
        """Analyze text using Gemini API"""
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "key": self.gemini_api_key
        }
        prompt = f"""
        Analyze this startup document and provide insights on:
        1. Business Model
        2. Market Opportunity
        3. Team Capabilities
        4. Risk Assessment
        5. Investment Potential

        Document text:
        {text[:8000]}  # Limit text length to avoid token limits
        """
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }

        try:
            response = requests.post(
                self.gemini_api_url, 
                headers=headers, 
                params=params, 
                json=payload
            )
            result = response.json()
            return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except Exception as e:
            raise Exception(f"Error analyzing text with Gemini: {str(e)}")