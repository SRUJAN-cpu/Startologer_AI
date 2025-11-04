from flask import Flask, request, jsonify, session, send_from_directory, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from firebase_admin import credentials, initialize_app, auth as firebase_auth
from werkzeug.utils import secure_filename
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.inputProcessService import InputProcessService
from textExtraction.textExtractor import extract_text
from helpers.analysis_helper import analyze_combined_text, gemini_ping, infer_cohort, infer_benchmark_estimates
from helpers.metric_extractor import extract_metrics
from services.benchmark_service import benchmark_metrics, score_from_benchmarks, reload_benchmarks, get_benchmark_source_info
from agents.orchestrator import get_orchestrator
from services.firestore_service import get_firestore_service
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
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_FILE_SIZE_MB', 32)) * 1024 * 1024  # 32MB to match Cloud Run limit

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[os.environ.get('RATELIMIT_DEFAULT', '100 per hour')],
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
)
print(f"[Flask] Rate limiting enabled: {os.environ.get('RATELIMIT_DEFAULT', '100 per hour')}")

# CORS Configuration - Restrict to specific origins in production
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
if ALLOWED_ORIGINS == ['*']:
    print("[WARNING] CORS is wide open. Set ALLOWED_ORIGINS env var for production!")

CORS(app, resources={
    r"/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Trial"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": ALLOWED_ORIGINS != ['*']
    }
})
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

input_service = InputProcessService(upload_folder=UPLOAD_FOLDER)
firestore_service = get_firestore_service()

# File cleanup utility
def cleanup_files(file_paths):
    """Remove uploaded files after processing"""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"[cleanup] Removed {path}")
        except Exception as e:
            print(f"[cleanup] Failed to remove {path}: {e}")

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size limit exceeded"""
    max_size = app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024)
    return jsonify({
        "error": "File too large for upload",
        "details": f"Cloud Run has a {max_size:.0f}MB HTTP request limit. Your file exceeded this limit even after client-side compression.\n\nPlease:\n1. Compress your PDF at https://www.ilovepdf.com/compress_pdf (free)\n2. Split large PDFs into smaller files\n3. Contact support for enterprise upload options"
    }), 413

@app.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limit exceeded"""
    return jsonify({
        "error": "Rate limit exceeded",
        "details": "You have made too many requests. Please try again later.",
        "retry_after": error.description
    }), 429

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

    result = input_service.process_input_data(form_data, files)
    if not result.get('success'):
        return jsonify({'error': result.get('error')}), 500

    # Store in session instead of global variable
    session['last_processed_result'] = result
    return jsonify(result)

@app.route('/get_processed_details', methods=['GET'])
def get_processed_details():
    user, error = verify_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    result = session.get('last_processed_result')
    if result is None:
        return jsonify({'error': 'No processed data available. Please submit data first.'}), 404
    return jsonify(result)

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("20 per hour")  # Stricter limit for expensive analysis endpoint
def analyze_documents():
    """
    Analyzes one or more uploaded documents using multi-agent orchestrator.
    Supports Document AI, Gemini analysis, and benchmark comparison.
    """
    print("="*80)
    print("[backend] ✓✓✓ /api/analyze endpoint HIT - NEW CODE LOADED ✓✓✓")
    print("="*80)

    # Demo mode can be flagged via form field or header
    is_demo = (request.form.get('isDemo') == 'true') or (request.headers.get('X-Trial') == 'true')
    user_id = None

    if not is_demo:
        user, error = verify_token()
        if not user:
            return jsonify({"error": "Unauthorized", "details": error}), 401
        user_id = user.get('uid')
    else:
        # Track trial usage
        ip_address = request.remote_addr or '0.0.0.0'
        user_agent = request.headers.get('User-Agent', 'Unknown')
        trial_status = firestore_service.track_trial_usage(ip_address, user_agent)

        if not trial_status.get('allowed'):
            return jsonify({
                "error": "Trial limit exceeded",
                "details": f"You have used {trial_status['trial_count']}/{trial_status['max_trials']} free trials. Please sign up for continued access.",
                "trial_count": trial_status['trial_count'],
                "max_trials": trial_status['max_trials']
            }), 429

    if not request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = list(request.files.values())
    if not files:
        return jsonify({"error": "No files were provided or files are empty"}), 400

    # Save uploaded files
    saved_paths = []
    file_names = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            saved_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(saved_path)
            saved_paths.append(saved_path)
            file_names.append(filename)

    print(f"[API] Received {len(saved_paths)} files for multi-agent analysis")

    try:
        # Use multi-agent orchestrator for complete analysis
        orchestrator = get_orchestrator()
        result = orchestrator.process(saved_paths)

        # Save to Firestore
        analysis_id = firestore_service.save_analysis(user_id, result, file_names)
        if analysis_id:
            result['analysis_id'] = analysis_id

        # Store in session for potential retrieval
        session['last_analysis_result'] = result

        return jsonify(result)

    except Exception as e:
        print(f"[API] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Analysis failed",
            "details": str(e),
            "success": False
        }), 500

    finally:
        # Always clean up uploaded files
        cleanup_files(saved_paths)

@app.route('/api/analyses/history', methods=['GET'])
def get_analysis_history():
    """Get analysis history for authenticated user"""
    user, error = verify_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = user.get('uid')
    limit = request.args.get('limit', 10, type=int)

    try:
        analyses = firestore_service.get_user_analyses(user_id, limit=limit)
        return jsonify({
            "success": True,
            "analyses": analyses,
            "count": len(analyses)
        })
    except Exception as e:
        print(f"[API] Error fetching analysis history: {e}")
        return jsonify({
            "error": "Failed to fetch analysis history",
            "details": str(e)
        }), 500

@app.route('/api/analyses/<analysis_id>', methods=['GET'])
def get_analysis_by_id(analysis_id):
    """Get a specific analysis by ID"""
    user, error = verify_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        analysis = firestore_service.get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        # Verify user owns this analysis
        if analysis.get('user_id') != user.get('uid'):
            return jsonify({"error": "Unauthorized access to analysis"}), 403

        return jsonify({
            "success": True,
            "analysis": analysis
        })
    except Exception as e:
        print(f"[API] Error fetching analysis: {e}")
        return jsonify({
            "error": "Failed to fetch analysis",
            "details": str(e)
        }), 500

# ===== Static file serving for Angular frontend =====
# Path to the compiled Angular app (dist/frontend/browser)
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend_dist')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_angular(path):
    """Serve Angular static files or index.html for client-side routing"""
    # If it's an API route, let Flask handle it (this shouldn't be reached due to /api prefix)
    if path.startswith('api/'):
        return jsonify({"error": "API endpoint not found"}), 404

    # Check if the requested file exists in the frontend dist folder
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)

    # For all other routes (including client-side routes), serve index.html
    index_path = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return jsonify({
            "error": "Frontend not built",
            "message": "Please build the Angular frontend first"
        }), 404

if __name__ == '__main__':
    # Disable reloader to prevent infinite restart loops
    app.run(debug=True, use_reloader=False)
