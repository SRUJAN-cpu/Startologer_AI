from flask import Flask, request, jsonify
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.inputProcessService import InputProcessService

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

input_service = InputProcessService(upload_folder=UPLOAD_FOLDER)

@app.route('/submit', methods=['POST'])
def submit():
    form_data = {
        'idea': request.form.get('idea'),
        'target_audience': request.form.get('target_audience'),
        'meeting_transcript': request.form.get('meeting_transcript')
    }
    files = {
        'pitchdeck': request.files.get('pitchdeck')
    }

    is_valid, error_message = input_service.validate_required_fields(form_data)
    if not is_valid:
        return jsonify({'error': error_message}), 400

    result = input_service.process_input_data(form_data, files)
    if not result.get('success'):
        return jsonify({'error': result.get('error')}), 500

    return jsonify(result)

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