from flask import Flask, request, jsonify
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.inputProcessService import InputProcessService

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

input_service = InputProcessService(upload_folder=UPLOAD_FOLDER)

# Global variable to store last processed result
last_processed_result = None

@app.route('/submit', methods=['POST'])
def submit():
    # Dummy input data for development/testing
    form_data = {
        'idea': 'Dummy startup idea',
        'target_audience': 'Dummy target audience',
        'meeting_transcript': 'Dummy transcript',
        'dummy': True
    }
    files = {
        'pitchdeck': None
    }

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

    global last_processed_result
    result = input_service.process_input_data(form_data, files)
    if not result.get('success'):
        return jsonify({'error': result.get('error')}), 500
    last_processed_result = result
    return jsonify(result)

@app.route('/get_processed_details', methods=['GET'])
def get_processed_details():
    global last_processed_result
    if last_processed_result is None:
        return jsonify({'error': 'No processed data available. Please submit data first.'}), 404
    return jsonify(last_processed_result)

if __name__ == '__main__':
    app.run(debug=True)