"""
StartupEval AI - Main Application
Flask API with Google ADK Integration

This application exposes the ADK agent system via REST API endpoints.
Supports both local development and Cloud Run deployment.
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from typing import Dict, Any

# Google ADK imports
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, FirestoreSessionService

# Local imports
from .config import ADKConfig
from .agents import get_startup_eval_agent, list_agent_capabilities


# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__)
CORS(app)

# Configure upload folder
os.makedirs(ADKConfig.UPLOAD_FOLDER, exist_ok=True)

# Initialize ADK components
agent = get_startup_eval_agent()

# Choose session service based on configuration
if ADKConfig.SESSION_SERVICE == 'firestore':
    session_service = FirestoreSessionService(
        project_id=ADKConfig.PROJECT_ID,
        collection_name="adk_sessions"
    )
else:
    session_service = InMemorySessionService()

# Create ADK runner
runner = Runner(agent=agent, session_service=session_service)


# ============================================================================
# Helper Functions
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ADKConfig.ALLOWED_EXTENSIONS


def save_uploaded_files(files) -> list[str]:
    """
    Save uploaded files to local filesystem

    Returns:
        List of saved file paths
    """
    saved_paths = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(ADKConfig.UPLOAD_FOLDER, filename)
            file.save(filepath)
            saved_paths.append(filepath)
        else:
            raise ValueError(f"Invalid file type: {file.filename}")

    return saved_paths


def cleanup_files(file_paths: list[str]) -> None:
    """Delete uploaded files after processing"""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            pass  # Silently ignore cleanup errors


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/adk/health', methods=['GET'])
def health_check():
    """
    Health check endpoint

    Returns:
        System health status
    """
    return jsonify({
        'status': 'healthy',
        'service': 'StartupEval AI',
        'adk_version': '1.0.0',
        'model': ADKConfig.MODEL_NAME,
        'project': ADKConfig.PROJECT_ID
    })


@app.route('/api/adk/capabilities', methods=['GET'])
def get_capabilities():
    """
    List agent capabilities

    Returns:
        All agents, sub-agents, and available tools
    """
    return jsonify(list_agent_capabilities())


@app.route('/api/adk/evaluate', methods=['POST'])
def evaluate_startup():
    """
    Main evaluation endpoint

    Accepts file uploads and processes them through the ADK agent pipeline.

    Request:
        - files: One or more files (PDF, DOCX, PPTX, images)
        - user_id: Optional user identifier

    Returns:
        Complete startup evaluation with analysis and scores

    Example:
        curl -X POST http://localhost:8080/api/adk/evaluate \\
             -F "files=@pitch_deck.pdf" \\
             -F "files=@financials.xlsx" \\
             -H "X-User-ID: user123"
    """
    try:
        # Validate request
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400

        # Get user ID
        user_id = request.headers.get('X-User-ID', 'anonymous')

        # Save uploaded files
        saved_paths = save_uploaded_files(files)

        # Prepare ADK prompt
        prompt = f"""Please evaluate these startup documents:

Files uploaded: {', '.join([os.path.basename(p) for p in saved_paths])}

Process these documents through the complete evaluation pipeline:
1. Parse all documents and extract text, entities, and KPIs
2. Perform comprehensive AI analysis
3. Compare metrics against industry benchmarks
4. Calculate investment score and verdict
5. Generate final evaluation report

User ID: {user_id}
"""

        # Run ADK agent
        response = runner.run(
            user_id=user_id,
            prompt=prompt,
            artifacts={
                'file_paths': saved_paths,
                'user_id': user_id
            }
        )

        # Clean up uploaded files
        cleanup_files(saved_paths)

        # Extract result from response
        # ADK stores outputs in session.state using output_key
        session_state = response.session.state if hasattr(response, 'session') else {}

        evaluation_result = session_state.get('evaluation_result', {})

        return jsonify({
            'success': True,
            'result': evaluation_result,
            'session_id': response.session.session_id if hasattr(response, 'session') else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/adk/session/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Retrieve session data

    Args:
        session_id: ADK session identifier

    Returns:
        Session state and history
    """
    try:
        session = session_service.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        return jsonify({
            'success': True,
            'session': {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'state': session.state,
                'created_at': session.metadata.get('created_at') if hasattr(session, 'metadata') else None
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/adk/sessions/user/<user_id>', methods=['GET'])
def get_user_sessions(user_id: str):
    """
    Get all sessions for a user

    Args:
        user_id: User identifier

    Returns:
        List of user sessions
    """
    try:
        # Note: This depends on session service implementation
        # InMemorySessionService might not support this query

        return jsonify({
            'success': True,
            'message': 'Session listing by user requires Firestore session service',
            'user_id': user_id
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# Command-Line Interface
# ============================================================================

def run_cli_evaluation(file_paths: list[str], user_id: str = "cli_user"):
    """
    Run evaluation from command line

    Args:
        file_paths: List of file paths to evaluate
        user_id: Optional user identifier

    Returns:
        Evaluation result
    """
    prompt = f"""Please evaluate these startup documents:

Files: {', '.join([os.path.basename(p) for p in file_paths])}

Process these documents through the complete evaluation pipeline.
"""

    response = runner.run(
        user_id=user_id,
        prompt=prompt,
        artifacts={
            'file_paths': file_paths,
            'user_id': user_id
        }
    )

    session_state = response.session.state if hasattr(response, 'session') else {}
    evaluation_result = session_state.get('evaluation_result', {})

    return evaluation_result


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='StartupEval AI - ADK Application')
    parser.add_argument('--mode', choices=['server', 'cli'], default='server',
                        help='Run mode: server (Flask API) or cli (command line)')
    parser.add_argument('--files', nargs='+', help='Files to evaluate (CLI mode only)')
    parser.add_argument('--user', default='cli_user', help='User ID (CLI mode only)')
    parser.add_argument('--port', type=int, default=8080, help='Server port')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')

    args = parser.parse_args()

    if args.mode == 'cli':
        if not args.files:
            print("Error: --files required for CLI mode")
            print("Example: python app.py --mode cli --files pitch_deck.pdf financials.xlsx")
            sys.exit(1)

        run_cli_evaluation(args.files, args.user)

    else:
        # Server mode
        app.run(host=args.host, port=args.port, debug=False)
