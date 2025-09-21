from flask import Blueprint, request, jsonify
from services.document_processor import DocumentProcessor
from werkzeug.utils import secure_filename
import os

document_routes = Blueprint('document_routes', __name__)
processor = DocumentProcessor()

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@document_routes.route('/api/process-documents', methods=['POST'])
async def process_documents():
    try:
        # Check if files were uploaded
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
            
        files = request.files.getlist('files[]')
        documents = []
        
        for file in files:
            if file and allowed_file(file.filename):
                # Validate file size
                file.seek(0, os.SEEK_END)
                size = file.tell()
                if size > MAX_FILE_SIZE:
                    return jsonify({'error': f'File {file.filename} exceeds size limit'}), 400
                
                # Reset file pointer and read content
                file.seek(0)
                content = file.read()
                mime_type = processor.get_mime_type(file.filename)
                documents.append((content, mime_type))
        
        # Process all documents
        results = await processor.process_multiple_documents(documents)
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500