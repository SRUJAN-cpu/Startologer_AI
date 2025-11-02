"""
Multi-Agent Orchestrator - Coordinates all agents for complete startup analysis
Manages the workflow: Document Parsing → Analysis → Benchmarking
"""

import os
import sys
import time
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from agents.document_parser_agent import DocumentParserAgent
from agents.analysis_agent import AnalysisAgent
from agents.benchmark_agent import BenchmarkAgent


class MultiAgentOrchestrator:
    """
    Orchestrator that coordinates multiple agents to perform comprehensive startup evaluation

    Workflow:
    1. DocumentParserAgent: Extract and structure information from documents
    2. AnalysisAgent: Generate AI-powered insights and analysis
    3. BenchmarkAgent: Compare metrics against industry benchmarks
    """

    def __init__(self):
        self.parser_agent = DocumentParserAgent()
        self.analysis_agent = AnalysisAgent()
        self.benchmark_agent = BenchmarkAgent()
        self.name = "MultiAgentOrchestrator"

    def process(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Orchestrate complete analysis pipeline

        Args:
            file_paths: List of document file paths to analyze

        Returns:
            Comprehensive analysis result containing:
                - Executive summary
                - Market analysis
                - Risks and recommendations
                - Benchmark comparisons
                - Scores and verdict
                - Processing metadata
        """
        start_time = time.time()

        try:
            # Phase 1: Document Parsing
            parser_start = time.time()
            parser_result = self.parser_agent.process(file_paths)
            parser_time = time.time() - parser_start

            combined_text = parser_result.get('combined_text', '')

            if not combined_text or not combined_text.strip():
                return self._create_error_response(
                    "No text could be extracted from the provided documents",
                    parser_result
                )

            # Phase 2: AI Analysis
            analysis_start = time.time()
            analysis_result = self.analysis_agent.process(combined_text, parser_result)
            analysis_time = time.time() - analysis_start

            # Phase 3: Benchmark Comparison
            benchmark_start = time.time()
            benchmark_result = self.benchmark_agent.process(analysis_result)
            benchmark_time = time.time() - benchmark_start

            # Combine all results
            total_time = time.time() - start_time

            final_result = self._combine_results(
                parser_result,
                analysis_result,
                benchmark_result,
                {
                    "total_time": total_time,
                    "parser_time": parser_time,
                    "analysis_time": analysis_time,
                    "benchmark_time": benchmark_time,
                    "files_processed": len(file_paths)
                }
            )

            return final_result

        except Exception as e:
            return self._create_error_response(str(e))

    def _combine_results(
        self,
        parser_result: Dict,
        analysis_result: Dict,
        benchmark_result: Dict,
        timing: Dict
    ) -> Dict[str, Any]:
        """Combine results from all agents into final analysis"""

        # Extract key components
        executive_summary = analysis_result.get('executiveSummary', 'No summary available')
        market_analysis = analysis_result.get('marketAnalysis', {})
        risks = analysis_result.get('risks', [])
        recommendations = analysis_result.get('recommendations', [])
        extracted_metrics = analysis_result.get('extractedMetrics', {})
        cohort = analysis_result.get('cohort', {})
        llm_benchmark = analysis_result.get('llmBenchmark')
        llm_status = analysis_result.get('llmStatus', {})
        benchmarks = benchmark_result.get('benchmarks', {})
        score = benchmark_result.get('score', {})
        verdict_explanation = benchmark_result.get('verdictExplanation', '')

        # Create comprehensive result
        result = {
            # Analysis outputs
            "executiveSummary": executive_summary,
            "marketAnalysis": market_analysis,
            "risks": risks,
            "recommendations": recommendations,

            # Metrics and cohort
            "extractedMetrics": extracted_metrics,
            "cohort": cohort,

            # Benchmarking
            "benchmarks": benchmarks,
            "score": score,
            "verdictExplanation": verdict_explanation,

            # LLM context
            "llmBenchmark": llm_benchmark,
            "llmStatus": llm_status,

            # Processing metadata
            "processingInfo": {
                "files_processed": parser_result.get('files_processed', []),
                "methods_used": parser_result.get('methods_used', []),
                "total_text_length": parser_result.get('total_text_length', 0),
                "entities_extracted": len(parser_result.get('entities', [])),
                "tables_extracted": len(parser_result.get('tables', [])),
                "timing": timing,
                "orchestrator": self.name
            },

            # Success indicator
            "success": True
        }

        return result

    def _create_error_response(self, error_message: str, parser_result: Dict = None) -> Dict[str, Any]:
        """Create error response with available information"""
        return {
            "success": False,
            "error": error_message,
            "executiveSummary": f"Analysis failed: {error_message}",
            "marketAnalysis": {
                "marketSize": "N/A",
                "growthRate": "N/A",
                "competition": "N/A",
                "entryBarriers": "N/A",
                "regulation": "N/A"
            },
            "risks": [{
                "factor": "Data Processing Error",
                "impact": "high",
                "description": error_message
            }],
            "recommendations": [{
                "title": "Resubmit Documents",
                "description": "Please ensure documents are readable and try again."
            }],
            "extractedMetrics": {},
            "cohort": {"sector": "unknown", "stage": "unknown", "source": "error"},
            "benchmarks": {},
            "score": {"composite": None, "verdict": "Error"},
            "llmStatus": {"ok": False, "error": error_message},
            "processingInfo": {
                "files_processed": parser_result.get('files_processed', []) if parser_result else [],
                "error": error_message
            }
        }


# Global instance
_orchestrator = None

def get_orchestrator() -> MultiAgentOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator
