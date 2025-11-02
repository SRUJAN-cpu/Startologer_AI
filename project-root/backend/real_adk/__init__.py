"""
StartupEval AI - Built with Google's Real ADK
Event-driven startup evaluation platform using Google AI Agent Development Kit

This implementation uses the ACTUAL Google ADK (not custom decorators)
"""

from .tools import *
from .agents import *

__all__ = [
    # Tools
    'upload_to_gcs',
    'parse_document_with_docai',
    'extract_entities_and_kpis',
    'analyze_with_gemini',
    'extract_financial_metrics',
    'compare_benchmarks',
    'generate_evaluation_report',
    'save_report_to_gcs',

    # Agents
    'create_doc_parser_agent',
    'create_analysis_agent',
    'create_doc_report_agent',
    'create_startup_eval_root_agent'
]
