from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
from textExtraction.textExtractor import extract_text

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:4200", "http://127.0.0.1:4200"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        try:
            extracted_text = extract_text(file_path)
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': file.filename,
                'extracted_text': extracted_text
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File upload failed'}), 400

@app.route('/get_processed_details', methods=['GET'])
def get_processed_details():
    # Example: Fetch processed details from a database or file
    # For now, just return a sample response
    processed_details = {
        'summary': 'This is a processed summary.',
        'insights': ['Insight 1', 'Insight 2']
    }
    return jsonify(processed_details)

if __name__ == '__main__':
    app.run(debug=True)