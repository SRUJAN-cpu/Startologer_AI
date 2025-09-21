from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, initialize_app, auth as firebase_auth
from werkzeug.utils import secure_filename
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.inputProcessService import InputProcessService
from textExtraction.textExtractor import extract_text
from helpers.analysis_helper import analyze_combined_text, gemini_ping, infer_cohort, infer_benchmark_estimates
from helpers.metric_extractor import extract_metrics
from services.benchmark_service import benchmark_metrics, score_from_benchmarks, reload_benchmarks, get_benchmark_source_info
try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    load_dotenv = None
    find_dotenv = None

FIREBASE_ENABLED = False
svc_key_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
if os.path.exists(svc_key_path):
    try:
        cred = credentials.Certificate(svc_key_path)
        initialize_app(cred)
        FIREBASE_ENABLED = True
        print("[backend] Firebase Admin initialized with serviceAccountKey.json")
    except Exception as e:
        print(f"[backend] Failed to initialize Firebase Admin: {e}")
else:
    print("[backend] serviceAccountKey.json not found; Firebase features disabled. Demo mode only.")

app = Flask(__name__)
# Broaden CORS to simplify fast external hosting (Render/ngrok/Cloudflare Tunnel)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Trial"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

input_service = InputProcessService(upload_folder=UPLOAD_FOLDER)
last_processed_result = None

def verify_token():
    if not FIREBASE_ENABLED:
        return None, "Firebase not configured"
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token, None
    except Exception as e:
        return None, f"Invalid token: {str(e)}"

@app.route('/api/health/env', methods=['GET'])
def env_health():
    """Return whether GEMINI_API_KEY is visible to this process."""
    dotenv_path = None
    if find_dotenv and load_dotenv:
        try:
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path)
        except Exception:
            pass
    present = bool(os.getenv('GEMINI_API_KEY'))
    return jsonify({
        'geminiKeyPresent': present,
        'dotenvPath': dotenv_path
    })

@app.route('/api/health/gemini', methods=['GET'])
def gemini_health():
    """Ping Gemini with a tiny payload to verify key + connectivity."""
    try:
        result = gemini_ping()
        return jsonify(result), (200 if result.get('ok') else 500)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/benchmarks/info', methods=['GET'])
def benchmarks_info():
    try:
        return jsonify({"ok": True, "info": get_benchmark_source_info()}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/benchmarks/reload', methods=['POST'])
def benchmarks_reload():
    try:
        info = reload_benchmarks()
        return jsonify({"ok": True, "info": info}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit():
    user, error = verify_token()
    if not user:
        if request.headers.get('X-Trial') == 'true':
            user = None  # proceed as anonymous trial
        else:
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

@app.route('/api/analyze', methods=['POST'])
def analyze_documents():
    """
    Analyzes one or more uploaded documents.
    For now, it saves the files and returns a dummy analysis result.
    """
    # Demo mode can be flagged via form field or header
    is_demo = (request.form.get('isDemo') == 'true') or (request.headers.get('X-Trial') == 'true')
    if not is_demo:
        user, error = verify_token()
        if not user:
            return jsonify({"error": "Unauthorized", "details": error}), 401

    if not request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = list(request.files.values())
    if not files:
        return jsonify({"error": "No files were provided or files are empty"}), 400

    saved_files = []
    extracted_chunks = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            saved_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(saved_path)
            saved_files.append(filename)
            try:
                text = extract_text(saved_path)
                if text and text.strip():
                    extracted_chunks.append(f"==== {filename} ===\n{text}")
            except Exception as e:
                print(f"Error extracting text from {filename}: {e}")
            finally:
                # Optional: keep uploaded files if needed; else clean up
                pass

    if not extracted_chunks:
        print("No text could be extracted from uploaded files.")

    combined_text = "\n\n".join(extracted_chunks)
    print(f"Received {len(saved_files)} files for analysis: {', '.join(saved_files)}")

    # Call analysis helper (uses Gemini if configured; otherwise returns fallback) and propagate status
    result = analyze_combined_text(combined_text)
    llm_ok = bool(result.get('llmStatus', {}).get('ok'))

    # Extract metrics and infer cohort for benchmarking
    try:
        metrics = extract_metrics(combined_text)
        sector = (metrics.get('sector') or '').strip().lower()
        stage = (metrics.get('stage') or '').strip().lower()
        cohort_source = 'extracted' if (sector and stage) else 'default'
        # Fallback to LLM inference if missing (only if LLM healthy)
        if (not sector or not stage) and llm_ok:
            guess = infer_cohort(combined_text)
            if guess.get('sector') or guess.get('stage'):
                cohort_source = 'llm'
            sector = sector or guess.get('sector') or ''
            stage = stage or guess.get('stage') or ''
        # Normalize a few common variants
        sector = (sector or '').replace('&', ' and ').replace('/', ' ').strip() or 'resale'
        stage = (stage or '').replace('pre seed', 'pre-seed').replace('preseed', 'pre-seed').strip() or 'seed'

        bench = benchmark_metrics(metrics, sector, stage)
        score = score_from_benchmarks(bench)
        result['extractedMetrics'] = metrics
        # Also surface the resolved cohort and its source for UI/debug clarity
        result.setdefault('extractedMetrics', {})
        result['extractedMetrics']['sector'] = sector
        result['extractedMetrics']['stage'] = stage
        result['cohort'] = { 'sector': sector, 'stage': stage, 'source': cohort_source }
        result['benchmarks'] = bench
        # Optional: LLM-estimated benchmark context (qualitative + rough medians) only if LLM healthy
        if llm_ok:
            try:
                llm_est = infer_benchmark_estimates(combined_text, sector, stage, metrics)
                if llm_est:
                    result['llmBenchmark'] = llm_est
            except Exception:
                pass
        result['score'] = score
    except Exception as e:
        print(f"[backend] metrics/benchmark failed: {e}")

    # Ensure we never surface a placeholder for regulation. If missing or placeholder-like, synthesize a brief, sector-aware note.
    try:
        reg = (result.get('marketAnalysis', {}).get('regulation') or '').strip().lower()
        placeholders = {'n/a', 'na', 'unknown', 'not specified', 'not specified in document', 'none', 'no data'}
        if (not reg) or (reg in placeholders):
            # Use resolved sector from extracted metrics or cohort
            sec_hint = ''
            try:
                sec_hint = (result.get('extractedMetrics', {}).get('sector') or result.get('cohort', {}).get('sector') or '').lower()
            except Exception:
                sec_hint = ''
            default_reg = "General compliance considerations include data privacy, information security, and fair business practices; specific licenses may be needed depending on geography and offering."
            if 'fin' in sec_hint or 'bfsi' in sec_hint or 'payments' in sec_hint:
                default_reg = "Financial services typically require licensing and ongoing KYC/AML controls; data privacy and PCI-like standards may apply across markets."
            elif 'health' in sec_hint or 'med' in sec_hint:
                default_reg = "Healthcare offerings face patient data protection (e.g., HIPAA/GDPR) and clinical/medical device guidelines; consent and record-keeping are critical."
            elif 'hr' in sec_hint or 'workforce' in sec_hint:
                default_reg = "HR solutions must align with labor and employment laws, consented data processing, and cross-border transfers under GDPR/DPDP where applicable."
            elif 'marketplace' in sec_hint or 'ecom' in sec_hint or 'commerce' in sec_hint:
                default_reg = "Marketplaces must comply with consumer protection, platform liability, taxation, and seller KYC where mandated; data privacy applies."
            elif 'ai' in sec_hint or 'ml' in sec_hint:
                default_reg = "AI solutions should address data provenance, privacy, model transparency, and emerging AI governance rules; sector-specific obligations may apply."
            elif 'saas' in sec_hint or 'software' in sec_hint or 'it' in sec_hint:
                default_reg = "SaaS platforms generally adhere to data privacy/security (GDPR/DPDP), contractual SLAs, and sector-specific obligations if processing regulated data."
            result.setdefault('marketAnalysis', {})['regulation'] = default_reg
    except Exception:
        pass

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
