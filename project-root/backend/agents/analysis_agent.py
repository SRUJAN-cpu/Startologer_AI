"""
Analysis Agent - Responsible for AI-powered startup analysis
Uses Gemini API for intelligent evaluation and insights
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from helpers.analysis_helper import analyze_combined_text, infer_cohort, infer_benchmark_estimates, extract_metrics_with_llm
from helpers.metric_extractor import extract_metrics


class AnalysisAgent:
    """
    Agent responsible for analyzing startup documents and generating insights
    Uses Google Gemini AI for intelligent evaluation
    """

    def __init__(self):
        self.name = "AnalysisAgent"

    def process(self, combined_text: str, parser_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze combined text from documents and generate investment insights

        Args:
            combined_text: Combined text from all documents
            parser_result: Results from DocumentParserAgent (entities, tables, metrics)

        Returns:
            Dict containing:
                - executive_summary: High-level summary
                - market_analysis: Market opportunity assessment
                - risks: Identified risks with impact levels
                - recommendations: Actionable recommendations
                - cohort: Inferred sector/stage
                - extracted_metrics: Financial/business metrics
                - llm_benchmark: LLM-estimated benchmarks
                - llm_status: Status of LLM API calls
        """
        # Step 1: Get LLM-powered analysis
        llm_analysis = analyze_combined_text(combined_text)
        llm_ok = bool(llm_analysis.get('llmStatus', {}).get('ok'))

        # Step 2: Extract metrics using multiple methods
        # 2a. Regex-based extraction (fast but limited)
        regex_metrics = extract_metrics(combined_text)
        print(f"[AnalysisAgent] Regex extracted metrics: {regex_metrics}")

        # 2b. LLM-based extraction (comprehensive but requires API)
        llm_metrics = {}
        if llm_ok:
            try:
                print(f"[AnalysisAgent] Attempting LLM metric extraction...")
                llm_metrics = extract_metrics_with_llm(combined_text)
                print(f"[AnalysisAgent] LLM extracted metrics: {llm_metrics}")
            except Exception as e:
                print(f"[AnalysisAgent] LLM metric extraction failed: {e}")
                llm_metrics = {}
        else:
            print(f"[AnalysisAgent] LLM not available, skipping LLM metric extraction")

        # Merge metrics: LLM takes precedence over regex when both exist
        extracted_metrics = {**regex_metrics, **llm_metrics}
        print(f"[AnalysisAgent] Final extracted_metrics: {extracted_metrics}")

        # Enrich metrics with Document AI entities
        if 'key_metrics' in parser_result:
            doc_ai_metrics = parser_result['key_metrics']

            # Add financial values from Document AI
            if 'financial_values' in doc_ai_metrics:
                extracted_metrics['documentai_financial'] = doc_ai_metrics['financial_values']

            # Add organizations (potential competitors/partners)
            if 'organizations' in doc_ai_metrics:
                extracted_metrics['organizations'] = doc_ai_metrics['organizations']

            # Add people (potential founders)
            if 'people' in doc_ai_metrics:
                extracted_metrics['founders'] = doc_ai_metrics['people']

        # Step 3: Infer cohort (sector + stage)
        # Clean sector/stage: remove newlines and extra whitespace
        raw_sector = extracted_metrics.get('sector') or ''
        raw_stage = extracted_metrics.get('stage') or ''
        print(f"[AnalysisAgent] Raw sector before cleaning: {repr(raw_sector)}")
        print(f"[AnalysisAgent] Raw stage before cleaning: {repr(raw_stage)}")

        sector = raw_sector.replace('\n', ' ').replace('\r', ' ').strip().lower()
        stage = raw_stage.replace('\n', ' ').replace('\r', ' ').strip().lower()
        # Collapse multiple spaces into one
        import re
        sector = re.sub(r'\s+', ' ', sector)
        stage = re.sub(r'\s+', ' ', stage)
        print(f"[AnalysisAgent] Cleaned sector: {repr(sector)}, stage: {repr(stage)}")
        cohort_source = 'extracted' if (sector and stage) else 'default'

        # Use LLM to infer cohort if missing and LLM is available
        if (not sector or not stage) and llm_ok:
            guess = infer_cohort(combined_text)
            if guess.get('sector') or guess.get('stage'):
                cohort_source = 'llm'
            sector = sector or guess.get('sector') or ''
            stage = stage or guess.get('stage') or ''

        # Normalize sector and stage
        sector_before_norm = sector
        sector = self._normalize_sector(sector) or 'saas'
        stage = self._normalize_stage(stage) or 'seed'
        print(f"[AnalysisAgent] Before normalization: sector={repr(sector_before_norm)}")
        print(f"[AnalysisAgent] After normalization: sector={repr(sector)}, stage={repr(stage)}, source={cohort_source}")

        # Step 4: Get LLM benchmark estimates (always attempt if LLM available)
        # This provides context even when specific metrics aren't extracted
        llm_benchmark = {}
        if llm_ok:
            try:
                llm_benchmark = infer_benchmark_estimates(combined_text, sector, stage, extracted_metrics)
                # Ensure we have at least estimates to show in charts
                if not llm_benchmark or not llm_benchmark.get('estimates'):
                    llm_benchmark = None
            except Exception as e:
                print(f"[AnalysisAgent] LLM benchmark estimation failed: {e}")
                llm_benchmark = None

        # FALLBACK: If LLM is unavailable or failed, use default benchmarks as estimates
        # This ensures charts always render even when Gemini API is down
        if not llm_benchmark:
            from helpers.analysis_helper import _get_default_benchmarks
            print(f"[AnalysisAgent] Using default benchmark estimates for {sector}/{stage}")
            llm_benchmark = _get_default_benchmarks(sector, stage)

        # Step 5: Synthesize regulation info if missing
        llm_analysis = self._ensure_regulation_info(llm_analysis, sector)

        # Create clean extracted metrics with normalized sector/stage
        clean_metrics = {k: v for k, v in extracted_metrics.items() if k not in ['sector', 'stage']}
        clean_metrics['sector'] = sector
        clean_metrics['stage'] = stage

        result = {
            **llm_analysis,  # Includes executiveSummary, marketAnalysis, risks, recommendations
            "extractedMetrics": clean_metrics,
            "cohort": {
                "sector": sector,
                "stage": stage,
                "source": cohort_source
            },
            "llmBenchmark": llm_benchmark,  # Always present now (fallback to defaults)
            "llmStatus": llm_analysis.get('llmStatus', {}),
            "agent": self.name,
            "processing_info": {
                "text_length": len(combined_text),
                "llm_available": llm_ok,
                "documentai_entities": len(parser_result.get('entities', [])),
                "documentai_tables": len(parser_result.get('tables', []))
            }
        }

        print(f"[AnalysisAgent] Final result - llmBenchmark present: {bool(llm_benchmark)}, has estimates: {bool(llm_benchmark.get('estimates') if llm_benchmark else False)}")
        return result

    def _normalize_sector(self, sector: str) -> str:
        """Normalize sector names to standard values"""
        if not sector:
            return 'saas'

        sector = sector.lower().strip()

        # Remove common noise words and clean up
        noise_words = ['linkedin', 'facebook', 'twitter', 'instagram', 'social', 'media', 'platform']
        for word in noise_words:
            sector = sector.replace(word, '').strip()

        # Mapping of common variants to standard names
        mappings = {
            'saas': ['saas', 'software', 'software as a service', 'b2b saas', 'enterprise software', 's a a s'],
            'fintech': ['fintech', 'finance', 'financial services', 'payments', 'banking', 'bfsi'],
            'healthtech': ['healthtech', 'healthcare', 'health', 'medical', 'med tech', 'digital health'],
            'ecommerce': ['ecommerce', 'e-commerce', 'marketplace', 'retail', 'commerce', 'resale'],
            'ai-ml': ['ai', 'ml', 'artificial intelligence', 'machine learning', 'ai/ml', 'deep learning'],
            'edtech': ['edtech', 'education', 'e-learning', 'learning'],
            'logistics': ['logistics', 'supply chain', 'transportation', 'delivery'],
            'hr-tech': ['hr', 'hr tech', 'human resources', 'workforce', 'recruitment']
        }

        for standard, variants in mappings.items():
            if any(variant in sector for variant in variants):
                return standard

        # If nothing matches and sector is very short (like 's'), default to saas
        if len(sector) <= 2:
            return 'saas'

        return sector or 'saas'

    def _normalize_stage(self, stage: str) -> str:
        """Normalize stage names to standard values"""
        stage = stage.lower().strip()

        # Direct mapping
        if stage in ['pre-seed', 'preseed']:
            return 'pre-seed'
        elif stage in ['seed']:
            return 'seed'
        elif stage in ['series a', 'series-a', 'a']:
            return 'series-a'
        elif stage in ['series b', 'series-b', 'b']:
            return 'series-b'
        elif stage in ['series c', 'series-c', 'c']:
            return 'series-c'
        elif stage in ['growth', 'late stage', 'late-stage']:
            return 'growth'

        return stage or 'seed'

    def _ensure_regulation_info(self, analysis: Dict, sector: str) -> Dict:
        """Ensure regulation field is populated based on sector"""
        try:
            reg = (analysis.get('marketAnalysis', {}).get('regulation') or '').strip().lower()
            placeholders = {'n/a', 'na', 'unknown', 'not specified', 'none', 'no data'}

            if (not reg) or (reg in placeholders):
                default_reg = self._get_sector_regulation(sector)
                if 'marketAnalysis' not in analysis:
                    analysis['marketAnalysis'] = {}
                analysis['marketAnalysis']['regulation'] = default_reg

        except Exception as e:
            pass

        return analysis

    def _get_sector_regulation(self, sector: str) -> str:
        """Get sector-specific regulation information"""
        regulations = {
            'fintech': "Financial services typically require licensing and ongoing KYC/AML controls; data privacy and PCI-like standards may apply across markets.",
            'healthtech': "Healthcare offerings face patient data protection (e.g., HIPAA/GDPR) and clinical/medical device guidelines; consent and record-keeping are critical.",
            'hr-tech': "HR solutions must align with labor and employment laws, consented data processing, and cross-border transfers under GDPR/DPDP where applicable.",
            'ecommerce': "Marketplaces must comply with consumer protection, platform liability, taxation, and seller KYC where mandated; data privacy applies.",
            'ai-ml': "AI solutions should address data provenance, privacy, model transparency, and emerging AI governance rules; sector-specific obligations may apply.",
            'saas': "SaaS platforms generally adhere to data privacy/security (GDPR/DPDP), contractual SLAs, and sector-specific obligations if processing regulated data.",
            'edtech': "EdTech platforms must comply with student data protection laws (COPPA, FERPA), parental consent requirements, and educational content regulations.",
            'logistics': "Logistics operations require compliance with transportation regulations, customs, labor laws, and data security for tracking information."
        }

        return regulations.get(sector, "General compliance considerations include data privacy, information security, and fair business practices; specific licenses may be needed depending on geography and offering.")
