"""
Configuration for StartupEval AI ADK Agents
Manages environment variables and Google Cloud settings
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ADKConfig:
    """Configuration manager for ADK agents"""

    # Google Cloud Configuration
    PROJECT_ID: str = os.getenv('GCP_PROJECT_ID', '')
    REGION: str = os.getenv('GCP_REGION', 'us-central1')

    # Document AI Configuration
    DOCUMENTAI_PROCESSOR_ID: str = os.getenv('DOCUMENTAI_PROCESSOR_ID', '')
    DOCUMENTAI_LOCATION: str = os.getenv('GCP_REGION', 'us')

    # Gemini/Vertex AI Configuration
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    MODEL_NAME: str = os.getenv('ADK_MODEL_NAME', 'gemini-2.0-flash')

    # Cloud Storage Configuration
    GCS_BUCKET_NAME: str = os.getenv('GCS_BUCKET_NAME', f'{PROJECT_ID}-startup-eval')
    GCS_UPLOAD_FOLDER: str = os.getenv('GCS_UPLOAD_FOLDER', 'uploads')
    GCS_REPORTS_FOLDER: str = os.getenv('GCS_REPORTS_FOLDER', 'reports')

    # Firestore Configuration
    FIRESTORE_COLLECTION: str = os.getenv('FIRESTORE_COLLECTION', 'analyses')

    # Application Settings
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_FILE_SIZE_MB: int = int(os.getenv('MAX_FILE_SIZE_MB', '10'))
    ALLOWED_EXTENSIONS: set = {'pdf', 'docx', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'tiff'}

    # ADK Settings
    SESSION_SERVICE: str = os.getenv('ADK_SESSION_SERVICE', 'memory')  # 'memory' or 'firestore'
    ENABLE_TOOL_CONFIRMATION: bool = os.getenv('ADK_ENABLE_CONFIRMATION', 'false').lower() == 'true'

    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """
        Validate required configuration

        Returns:
            (is_valid, error_message)
        """
        if not cls.PROJECT_ID:
            return False, "GCP_PROJECT_ID is required"

        if not cls.DOCUMENTAI_PROCESSOR_ID:
            return False, "DOCUMENTAI_PROCESSOR_ID is required"

        if not cls.GEMINI_API_KEY:
            return False, "GEMINI_API_KEY is required"

        return True, None

    @classmethod
    def get_documentai_processor_name(cls) -> str:
        """Get full Document AI processor resource name"""
        return f"projects/{cls.PROJECT_ID}/locations/{cls.DOCUMENTAI_LOCATION}/processors/{cls.DOCUMENTAI_PROCESSOR_ID}"

    @classmethod
    def get_gcs_upload_path(cls, filename: str) -> str:
        """Get GCS path for uploaded file"""
        return f"gs://{cls.GCS_BUCKET_NAME}/{cls.GCS_UPLOAD_FOLDER}/{filename}"

    @classmethod
    def get_gcs_report_path(cls, report_id: str) -> str:
        """Get GCS path for evaluation report"""
        return f"gs://{cls.GCS_BUCKET_NAME}/{cls.GCS_REPORTS_FOLDER}/{report_id}.pdf"

    @classmethod
    def to_dict(cls) -> dict:
        """Convert configuration to dictionary (for logging)"""
        return {
            'project_id': cls.PROJECT_ID,
            'region': cls.REGION,
            'model_name': cls.MODEL_NAME,
            'gcs_bucket': cls.GCS_BUCKET_NAME,
            'session_service': cls.SESSION_SERVICE,
            'documentai_configured': bool(cls.DOCUMENTAI_PROCESSOR_ID),
            'gemini_configured': bool(cls.GEMINI_API_KEY)
        }


# Validate configuration on import
is_valid, error = ADKConfig.validate()
if not is_valid:
    print(f"[ADK] Configuration Warning: {error}")
    print("[ADK] Some features may not work without proper configuration.")
    print("[ADK] Please set required environment variables in .env file")
else:
    print("[ADK] Configuration validated successfully")
    print(f"[ADK]    Project: {ADKConfig.PROJECT_ID}")
    print(f"[ADK]    Model: {ADKConfig.MODEL_NAME}")
