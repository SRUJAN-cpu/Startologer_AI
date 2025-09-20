from flask import Flask, request, jsonify
from firebase_admin import credentials, initialize_app, auth as firebase_auth
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.inputProcessService import InputProcessService

cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred)

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

input_service = InputProcessService(upload_folder=UPLOAD_FOLDER)
last_processed_result = None

def verify_token():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token, None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"

@app.route('/submit', methods=['POST'])
def submit():
    user, error = verify_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    form_data = {
        'idea': request.form.get('idea'),
        'target_audience': request.form.get('target_audience'),
        'meeting_transcript': request.form.get('meeting_transcript')
    }
    files = {'pitchdeck': request.files.get('pitchdeck')}

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
    user, error = verify_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    global last_processed_result
    if last_processed_result is None:
        return jsonify({'error': 'No processed data available. Please submit data first.'}), 404
    return jsonify(last_processed_result)

if __name__ == '__main__':
    app.run(debug=True)
