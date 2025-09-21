import asyncio
from services.document_processor import DocumentProcessor
import os
from dotenv import load_dotenv
import json

async def test_document_processor():
    # Load environment variables
    load_dotenv()
    
    # Initialize processor
    processor = DocumentProcessor()
    
    # Use your existing PDF file
    test_file = "test.pdf"
    
    try:
        # Read test file
        with open(test_file, 'rb') as f:
            content = f.read()
        
        print("Processing document...")
        extracted_text = await processor.process_document(
            content=content,
            mime_type='application/pdf'
        )
        
        print("Analyzing content...")
        analysis = await processor.analyze_text(extracted_text)
        
        print("\n=== Results ===")
        print("\nDocument Overview:")
        print("-" * 50)
        print(f"Text Length: {len(extracted_text)} characters")
        print(f"Preview: {extracted_text[:200]}...")
        
        print("\nAI Analysis:")
        print("-" * 50)
        try:
            # Try to format analysis as JSON for better readability
            analysis_dict = json.loads(analysis) if isinstance(analysis, str) else analysis
            print(json.dumps(analysis_dict, indent=2))
        except:
            # If not JSON, print as is
            print(analysis)
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        raise e

if __name__ == "__main__":
    asyncio.run(test_document_processor())