from flask import Flask, request, jsonify
import os
from textExtraction.textExtractor import extract_text

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/submit', methods=['POST'])
def submit():
    idea = request.form.get('idea')
    target_audience = request.form.get('target_audience')
    meeting_transcript = request.form.get('meeting_transcript')
    file = request.files.get('pitchdeck')
    extracted_text = None

    if not idea or not target_audience:
        return jsonify({'error': 'idea and target_audience are required fields.'}), 400
    
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        extracted_text = extract_text(file_path)
    return jsonify({
        'idea': idea,
        'target_audience': target_audience,
        'meeting_transcript': meeting_transcript,
        'pitchdeck_text': extracted_text
    })

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