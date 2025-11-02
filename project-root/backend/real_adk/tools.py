"""
Tools for StartupEval AI ADK Agents
Tools are regular Python functions that agents can call

In ADK, tools are discovered via:
- Function name
- Docstring (becomes tool description)
- Type hints (become parameter schema)
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Google Cloud imports
from google.cloud import storage
from google.cloud import documentai_v1 as documentai
from google.cloud import firestore
import google.generativeai as genai

from .config import ADKConfig


# ============================================================================
# DOCUMENT PARSING TOOLS (DocParserAgent)
# ============================================================================

def upload_to_gcs(
    local_file_path: str,
    destination_blob_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to Google Cloud Storage.

    This tool uploads local files to GCS for processing by Document AI
    and storage. The file becomes accessible via a gs:// URI.

    Args:
        local_file_path: Path to the local file to upload
        destination_blob_name: Optional custom name in GCS (defaults to filename)

    Returns:
        Dictionary with:
            - gcs_uri: Full gs:// URI of uploaded file
            - bucket: Bucket name
            - blob_name: Object name in bucket
            - success: Boolean indicating success
            - error: Error message if failed
    """
    try:
        if not destination_blob_name:
            destination_blob_name = os.path.basename(local_file_path)

        # Initialize GCS client
        storage_client = storage.Client(project=ADKConfig.PROJECT_ID)
        bucket = storage_client.bucket(ADKConfig.GCS_BUCKET_NAME)
        blob = bucket.blob(f"{ADKConfig.GCS_UPLOAD_FOLDER}/{destination_blob_name}")

        # Upload file
        blob.upload_from_filename(local_file_path)

        gcs_uri = f"gs://{ADKConfig.GCS_BUCKET_NAME}/{ADKConfig.GCS_UPLOAD_FOLDER}/{destination_blob_name}"

        print(f"[OK] Uploaded {local_file_path} to {gcs_uri}")

        return {
            'success': True,
            'gcs_uri': gcs_uri,
            'bucket': ADKConfig.GCS_BUCKET_NAME,
            'blob_name': f"{ADKConfig.GCS_UPLOAD_FOLDER}/{destination_blob_name}",
            'filename': destination_blob_name
        }

    except Exception as e:
        print(f"[ERROR] Error uploading to GCS: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def parse_document_with_docai(gcs_uri: str) -> Dict[str, Any]:
    """
    Parse a document using Google Document AI OCR and entity extraction.

    This tool uses Document AI to extract text, entities (companies, people,
    dates, money values), and tables from PDFs and images.

    Args:
        gcs_uri: Google Cloud Storage URI (gs://bucket/path/file.pdf)

    Returns:
        Dictionary with:
            - text: Full extracted text
            - entities: List of extracted entities
            - tables: List of extracted tables
            - page_count: Number of pages
            - language: Detected language
            - success: Boolean indicating success
    """
    try:
        print(f"📄 Parsing document with Document AI: {gcs_uri}")

        # Initialize Document AI client
        client = documentai.DocumentProcessorServiceClient()

        # Get file from GCS
        storage_client = storage.Client()
        bucket_name = gcs_uri.split('/')[2]
        blob_path = '/'.join(gcs_uri.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        file_content = blob.download_as_bytes()

        # Determine MIME type from extension
        ext = os.path.splitext(gcs_uri)[1].lower()
        mime_type_map = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff'
        }
        mime_type = mime_type_map.get(ext, 'application/pdf')

        # Create processing request
        raw_document = documentai.RawDocument(
            content=file_content,
            mime_type=mime_type
        )

        processor_name = ADKConfig.get_documentai_processor_name()
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document
        )

        # Process document
        result = client.process_document(request=request)
        document = result.document

        # Extract entities
        entities = []
        for entity in document.entities:
            entities.append({
                'type': entity.type_,
                'mention_text': entity.mention_text,
                'confidence': entity.confidence,
                'normalized_value': entity.normalized_value.text if entity.normalized_value else None
            })

        # Extract tables
        tables = []
        for page in document.pages:
            for table in page.tables:
                table_data = []
                for row in table.body_rows:
                    row_data = []
                    for cell in row.cells:
                        cell_text = ''.join([
                            document.text[segment.start_index:segment.end_index]
                            for segment in cell.layout.text_anchor.text_segments
                        ])
                        row_data.append(cell_text)
                    table_data.append(row_data)
                tables.append(table_data)

        print(f"[OK] Parsed document: {len(document.text)} chars, {len(entities)} entities, {len(tables)} tables")

        return {
            'success': True,
            'text': document.text,
            'entities': entities,
            'tables': tables,
            'page_count': len(document.pages),
            'language': document.pages[0].detected_languages[0].language_code if document.pages[0].detected_languages else 'unknown'
        }

    except Exception as e:
        print(f"[ERROR] Error parsing document: {e}")
        return {
            'success': False,
            'error': str(e),
            'text': '',
            'entities': [],
            'tables': []
        }


def extract_entities_and_kpis(entities: List[Dict]) -> Dict[str, Any]:
    """
    Extract key performance indicators (KPIs) from Document AI entities.

    This tool analyzes entities extracted by Document AI and categorizes
    them into financial values, dates, organizations, and people.

    Args:
        entities: List of entities from Document AI

    Returns:
        Dictionary with categorized KPIs:
            - financial_values: Money amounts
            - dates: Important dates
            - organizations: Company names
            - people: Person names
            - metrics: Extracted business metrics
    """
    financial_values = []
    dates = []
    organizations = []
    people = []

    for entity in entities:
        entity_type = entity.get('type', '').lower()
        mention_text = entity.get('mention_text', '')

        if 'money' in entity_type or 'price' in entity_type:
            financial_values.append({
                'text': mention_text,
                'normalized': entity.get('normalized_value'),
                'confidence': entity.get('confidence')
            })
        elif 'date' in entity_type:
            dates.append(mention_text)
        elif 'organization' in entity_type or 'company' in entity_type:
            organizations.append(mention_text)
        elif 'person' in entity_type:
            people.append(mention_text)

    return {
        'financial_values': financial_values,
        'dates': dates,
        'organizations': organizations,
        'people': people,
        'total_entities': len(entities)
    }


# ============================================================================
# ANALYSIS TOOLS (AnalysisAgent)
# ============================================================================

def analyze_with_gemini(
    combined_text: str,
    analysis_type: str = "startup_evaluation"
) -> Dict[str, Any]:
    """
    Analyze startup documents using Google Gemini AI.

    This tool uses Gemini to generate comprehensive startup evaluations
    including executive summary, market analysis, risks, and recommendations.

    Args:
        combined_text: Full text from all startup documents
        analysis_type: Type of analysis ("startup_evaluation", "financial", "market")

    Returns:
        Dictionary with:
            - executive_summary: 2-4 sentence summary
            - market_analysis: Market opportunity assessment
            - risks: List of identified risks
            - recommendations: Actionable recommendations
            - success: Boolean indicating success
    """
    try:
        print(f"🤖 Analyzing with Gemini: {len(combined_text)} chars")

        # Configure Gemini
        genai.configure(api_key=ADKConfig.GEMINI_API_KEY)
        model = genai.GenerativeModel(ADKConfig.MODEL_NAME)

        # Create analysis prompt
        prompt = f"""You are an expert venture capital analyst. Analyze the following startup documents and provide a comprehensive evaluation.

DOCUMENTS:
{combined_text[:8000]}  # Limit to 8000 chars for token management

Provide your analysis in the following JSON format:
{{
  "executiveSummary": "2-4 sentence high-level summary",
  "marketAnalysis": {{
    "tam": "Total Addressable Market (global market size in dollars)",
    "sam": "Serviceable Addressable Market (target regions/segments in dollars)",
    "som": "Serviceable Obtainable Market (realistic 3-5 year capture in dollars)",
    "marketSize": "Overall market size description",
    "growthRate": "Market growth rate and trends (YoY %)",
    "competition": {{
      "competitors": ["List of 3-5 main competitors"],
      "positioning": "How this startup compares and differentiates"
    }},
    "entryBarriers": "Barriers to entry assessment",
    "regulation": "Regulatory considerations"
  }},
  "risks": [
    {{
      "factor": "Risk name",
      "impact": "high|medium|low",
      "description": "Risk description and mitigation strategies"
    }}
  ],
  "recommendations": [
    {{
      "title": "Recommendation title",
      "description": "Detailed actionable recommendation"
    }}
  ]
}}

IMPORTANT: For TAM/SAM/SOM, provide specific dollar amounts with reasoning. For competition, list actual competitor names if mentioned in documents.

Respond ONLY with valid JSON, no markdown formatting."""

        # Generate analysis
        response = model.generate_content(prompt)
        analysis_text = response.text

        # Clean JSON (remove markdown code blocks if present)
        if '```json' in analysis_text:
            analysis_text = analysis_text.split('```json')[1].split('```')[0]
        elif '```' in analysis_text:
            analysis_text = analysis_text.split('```')[1].split('```')[0]

        # Parse JSON
        analysis = json.loads(analysis_text)

        print(f"[OK] Gemini analysis complete")

        return {
            'success': True,
            **analysis,
            'llmStatus': {'ok': True, 'model': ADKConfig.MODEL_NAME}
        }

    except Exception as e:
        print(f"[ERROR] Error in Gemini analysis: {e}")
        return {
            'success': False,
            'error': str(e),
            'executiveSummary': f"Analysis failed: {str(e)}",
            'marketAnalysis': {},
            'risks': [],
            'recommendations': [],
            'llmStatus': {'ok': False, 'error': str(e)}
        }


def extract_financial_metrics(text: str) -> Dict[str, Any]:
    """
    Extract financial and business metrics from text using regex patterns.

    This tool extracts ARR, MRR, CAC, LTV, churn rate, growth rates,
    and other key metrics from document text.

    Args:
        text: Text to extract metrics from

    Returns:
        Dictionary with extracted metrics:
            - arr: Annual Recurring Revenue
            - mrr: Monthly Recurring Revenue
            - cac: Customer Acquisition Cost
            - ltv: Lifetime Value
            - churn_rate: Monthly churn rate
            - growth_yoy: Year-over-year growth
            - growth_mom: Month-over-month growth
            - sector: Business sector
            - stage: Funding stage
    """
    import re

    metrics = {}

    # ARR patterns
    arr_patterns = [
        r'ARR[:\s]+\$?([\d,\.]+)\s*([KkMmBb])?',
        r'Annual Recurring Revenue[:\s]+\$?([\d,\.]+)\s*([KkMmBb])?'
    ]
    for pattern in arr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(',', ''))
            multiplier = {'k': 1000, 'm': 1000000, 'b': 1000000000}.get(
                match.group(2).lower() if match.group(2) else 'm', 1
            )
            metrics['arr'] = int(value * multiplier)
            break

    # MRR patterns
    mrr_patterns = [
        r'MRR[:\s]+\$?([\d,\.]+)\s*([KkMmBb])?',
        r'Monthly Recurring Revenue[:\s]+\$?([\d,\.]+)\s*([KkMmBb])?'
    ]
    for pattern in mrr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(',', ''))
            multiplier = {'k': 1000, 'm': 1000000}.get(
                match.group(2).lower() if match.group(2) else 'k', 1
            )
            metrics['mrr'] = int(value * multiplier)
            break

    # CAC patterns
    cac_match = re.search(r'CAC[:\s]+\$?([\d,\.]+)', text, re.IGNORECASE)
    if cac_match:
        metrics['cac'] = float(cac_match.group(1).replace(',', ''))

    # LTV patterns
    ltv_match = re.search(r'LTV[:\s]+\$?([\d,\.]+)', text, re.IGNORECASE)
    if ltv_match:
        metrics['ltv'] = float(ltv_match.group(1).replace(',', ''))

    # Churn rate
    churn_match = re.search(r'churn[:\s]+([\d\.]+)%?', text, re.IGNORECASE)
    if churn_match:
        metrics['churnRate'] = float(churn_match.group(1))

    # Sector detection
    sector_keywords = {
        'saas': ['saas', 'software as a service', 'b2b software'],
        'fintech': ['fintech', 'financial technology', 'payments'],
        'healthtech': ['healthtech', 'healthcare', 'medical'],
        'ecommerce': ['ecommerce', 'e-commerce', 'marketplace'],
        'ai-ml': ['artificial intelligence', 'machine learning', 'ai/ml']
    }
    for sector, keywords in sector_keywords.items():
        if any(keyword in text.lower() for keyword in keywords):
            metrics['sector'] = sector
            break

    # Stage detection
    stage_keywords = ['seed', 'series a', 'series b', 'pre-seed']
    for stage in stage_keywords:
        if stage in text.lower():
            metrics['stage'] = stage.replace(' ', '-')
            break

    print(f"[OK] Extracted {len(metrics)} metrics")
    return metrics


# ============================================================================
# BENCHMARKING & REPORTING TOOLS (DocReportAgent)
# ============================================================================

def compare_benchmarks(
    extracted_metrics: Dict[str, Any],
    sector: str,
    stage: str
) -> Dict[str, Any]:
    """
    Compare startup metrics against industry benchmarks.

    This tool compares the startup's metrics (ARR, MRR, CAC, etc.) against
    benchmark data for similar companies in the same sector and stage.

    Args:
        extracted_metrics: Metrics extracted from startup documents
        sector: Business sector (e.g., 'saas', 'fintech')
        stage: Funding stage (e.g., 'seed', 'series-a')

    Returns:
        Dictionary with benchmark comparisons for each metric:
            - company_value: Startup's value
            - median: Benchmark median
            - percentile: Startup's percentile ranking
            - status: 'above' or 'below' median
    """
    # Import benchmark service (uses existing benchmark data)
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from services.benchmark_service import benchmark_metrics

    benchmarks = benchmark_metrics(extracted_metrics, sector, stage)

    print(f"[OK] Compared {len(benchmarks)} metrics against {sector}/{stage} benchmarks")

    return benchmarks


def detect_red_flags(
    analysis_result: Dict[str, Any],
    extracted_metrics: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect specific red flags in startup data.

    This tool identifies critical warning signs including inflated TAM,
    high churn, poor unit economics, and inconsistent metrics.

    Args:
        analysis_result: Gemini analysis results with market analysis
        extracted_metrics: Extracted financial metrics

    Returns:
        List of red flags with type, severity, and description:
            - type: Red flag category
            - severity: 'high', 'medium', or 'low'
            - description: Detailed explanation
            - detected: Boolean indicating if flag is present
    """
    red_flags = []

    # Check for inflated TAM (TAM > $500B is often suspicious)
    market_analysis = analysis_result.get('marketAnalysis', {})
    tam_text = market_analysis.get('tam', '') or market_analysis.get('marketSize', '')

    if tam_text:
        # Look for suspicious TAM indicators
        if any(word in tam_text.lower() for word in ['trillion', 'inflated', 'unrealistic', 'overstated']):
            red_flags.append({
                'type': 'inflated_tam',
                'severity': 'high',
                'description': f'Market size claims may be inflated: {tam_text[:100]}',
                'detected': True
            })
        # Check for extremely large TAM (>$1T)
        import re
        tam_numbers = re.findall(r'\$?([\d,\.]+)\s*(trillion|T)', tam_text, re.IGNORECASE)
        if tam_numbers:
            red_flags.append({
                'type': 'inflated_tam',
                'severity': 'medium',
                'description': f'TAM exceeds $1 trillion - verify market sizing methodology',
                'detected': True
            })

    # Check for high churn rate (>5% monthly is concerning for SaaS)
    churn_rate = extracted_metrics.get('churnRate', 0)
    if churn_rate > 5:
        severity = 'high' if churn_rate > 10 else 'medium'
        red_flags.append({
            'type': 'high_churn',
            'severity': severity,
            'description': f'Monthly churn rate of {churn_rate}% is above healthy threshold (3-5% for SaaS)',
            'detected': True
        })

    # Check for poor unit economics (LTV:CAC ratio < 3:1)
    ltv = extracted_metrics.get('ltv')
    cac = extracted_metrics.get('cac')
    if ltv and cac and cac > 0:
        ltv_cac_ratio = ltv / cac
        if ltv_cac_ratio < 3:
            red_flags.append({
                'type': 'poor_unit_economics',
                'severity': 'high',
                'description': f'LTV:CAC ratio of {ltv_cac_ratio:.1f}:1 is below healthy threshold (3:1)',
                'detected': True
            })

    # Check for negative or very low growth
    growth_mom = extracted_metrics.get('growth_mom')
    if growth_mom is not None and growth_mom < 5:
        red_flags.append({
            'type': 'low_growth',
            'severity': 'medium',
            'description': f'Month-over-month growth of {growth_mom}% is below expected rate (10-20% for early stage)',
            'detected': True
        })

    # Check for inconsistent ARR/MRR relationship (ARR should be ~12x MRR)
    arr = extracted_metrics.get('arr')
    mrr = extracted_metrics.get('mrr')
    if arr and mrr and mrr > 0:
        arr_mrr_ratio = arr / mrr
        if arr_mrr_ratio < 10 or arr_mrr_ratio > 14:
            red_flags.append({
                'type': 'inconsistent_metrics',
                'severity': 'medium',
                'description': f'ARR/MRR ratio of {arr_mrr_ratio:.1f}x is inconsistent (expected ~12x)',
                'detected': True
            })

    # Check for missing critical metrics
    critical_metrics = ['arr', 'mrr', 'cac', 'ltv']
    missing_metrics = [m for m in critical_metrics if not extracted_metrics.get(m)]
    if len(missing_metrics) >= 3:
        red_flags.append({
            'type': 'insufficient_data',
            'severity': 'low',
            'description': f'Missing critical metrics: {", ".join(missing_metrics)}',
            'detected': True
        })

    if red_flags:
        print(f"[WARN]  Detected {len(red_flags)} red flags")
    else:
        print(f"[OK] No critical red flags detected")

    return red_flags


def calculate_investment_score(benchmarks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate composite investment score and verdict from benchmarks.

    This tool calculates an overall investment score (0-100) based on how
    the startup performs against benchmarks, and assigns a verdict.

    Args:
        benchmarks: Benchmark comparison results

    Returns:
        Dictionary with:
            - composite: Overall score (0-100)
            - verdict: 'Proceed', 'Track', or 'Pass'
            - weights: Metric weights used
            - metric_scores: Individual metric scores
    """
    # Import scoring service
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from services.benchmark_service import score_from_benchmarks

    score = score_from_benchmarks(benchmarks)

    print(f"[OK] Calculated score: {score.get('composite', 'N/A')}, verdict: {score.get('verdict', 'N/A')}")

    return score


def generate_evaluation_report(
    analysis_result: Dict[str, Any],
    benchmarks: Dict[str, Any],
    score: Dict[str, Any],
    red_flags: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive startup evaluation report.

    This tool combines all analysis, benchmarks, scoring, and red flags into a
    structured report ready for presentation or PDF generation.

    Args:
        analysis_result: Gemini analysis results
        benchmarks: Benchmark comparisons
        score: Investment score and verdict
        red_flags: Optional list of detected red flags

    Returns:
        Complete evaluation report dictionary with red flags
    """
    report = {
        'report_id': f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        'generated_at': datetime.utcnow().isoformat(),
        'executiveSummary': analysis_result.get('executiveSummary', ''),
        'marketAnalysis': analysis_result.get('marketAnalysis', {}),
        'risks': analysis_result.get('risks', []),
        'redFlags': red_flags if red_flags is not None else [],
        'recommendations': analysis_result.get('recommendations', []),
        'benchmarks': benchmarks,
        'score': score,
        'verdict': score.get('verdict', 'Insufficient Data')
    }

    print(f"[OK] Generated evaluation report: {report['report_id']}")

    return report


def save_report_to_gcs(report: Dict[str, Any], report_id: str) -> Dict[str, str]:
    """
    Save evaluation report to Google Cloud Storage.

    This tool saves the final report as JSON to GCS for storage and retrieval.

    Args:
        report: Complete evaluation report
        report_id: Unique report identifier

    Returns:
        Dictionary with:
            - gcs_uri: Full gs:// URI of saved report
            - success: Boolean indicating success
    """
    try:
        # Initialize GCS client
        storage_client = storage.Client(project=ADKConfig.PROJECT_ID)
        bucket = storage_client.bucket(ADKConfig.GCS_BUCKET_NAME)
        blob = bucket.blob(f"{ADKConfig.GCS_REPORTS_FOLDER}/{report_id}.json")

        # Save report as JSON
        blob.upload_from_string(
            json.dumps(report, indent=2),
            content_type='application/json'
        )

        gcs_uri = f"gs://{ADKConfig.GCS_BUCKET_NAME}/{ADKConfig.GCS_REPORTS_FOLDER}/{report_id}.json"

        print(f"[OK] Saved report to {gcs_uri}")

        return {
            'success': True,
            'gcs_uri': gcs_uri,
            'report_id': report_id
        }

    except Exception as e:
        print(f"[ERROR] Error saving report: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def save_to_firestore(report: Dict[str, Any], user_id: str) -> Dict[str, str]:
    """
    Save evaluation report to Firestore database.

    This tool persists the report in Firestore for user access and history.

    Args:
        report: Complete evaluation report
        user_id: User ID for the report

    Returns:
        Dictionary with:
            - document_id: Firestore document ID
            - success: Boolean indicating success
    """
    try:
        # Initialize Firestore client
        db = firestore.Client(project=ADKConfig.PROJECT_ID)

        # Create document
        doc_ref = db.collection(ADKConfig.FIRESTORE_COLLECTION).document()

        # Add metadata
        report_data = {
            **report,
            'user_id': user_id,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        # Save to Firestore
        doc_ref.set(report_data)

        print(f"[OK] Saved report to Firestore: {doc_ref.id}")

        return {
            'success': True,
            'document_id': doc_ref.id
        }

    except Exception as e:
        print(f"[ERROR] Error saving to Firestore: {e}")
        return {
            'success': False,
            'error': str(e)
        }
