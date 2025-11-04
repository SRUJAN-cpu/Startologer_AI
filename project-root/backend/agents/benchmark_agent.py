"""
Benchmark Agent - Responsible for comparing startup metrics against benchmarks
Uses historical benchmark data and generates investment scores
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.benchmark_service import benchmark_metrics, score_from_benchmarks


class BenchmarkAgent:
    """
    Agent responsible for benchmark comparison and scoring
    Compares company metrics against sector/stage benchmarks
    """

    def __init__(self):
        self.name = "BenchmarkAgent"

    def process(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare startup metrics against benchmarks and generate score

        Args:
            analysis_result: Results from AnalysisAgent containing metrics and cohort

        Returns:
            Dict containing:
                - benchmarks: Detailed benchmark comparisons
                - score: Composite score with verdict
                - verdict_explanation: Reasoning for the verdict
                - agent: Agent name
        """
        # Extract metrics and cohort info
        extracted_metrics = analysis_result.get('extractedMetrics', {})
        cohort = analysis_result.get('cohort', {})
        sector = cohort.get('sector', 'saas')
        stage = cohort.get('stage', 'seed')

        print(f"[BenchmarkAgent] Received extractedMetrics: {extracted_metrics}")
        print(f"[BenchmarkAgent] Cohort: sector={sector}, stage={stage}")

        # Perform benchmark comparison
        try:
            benchmarks = benchmark_metrics(extracted_metrics, sector, stage)
            print(f"[BenchmarkAgent] Benchmark results: {benchmarks}")
        except Exception as e:
            print(f"[BenchmarkAgent] Benchmark comparison failed: {e}")
            import traceback
            traceback.print_exc()
            benchmarks = {}

        # Calculate composite score
        try:
            score = score_from_benchmarks(benchmarks)
        except Exception as e:
            score = {
                "composite": None,
                "verdict": "Insufficient Data",
                "weights": {},
                "metricScores": {}
            }

        # Generate verdict explanation
        verdict_explanation = self._generate_verdict_explanation(
            score, benchmarks, sector, stage
        )

        result = {
            "benchmarks": benchmarks,
            "score": score,
            "verdictExplanation": verdict_explanation,
            "agent": self.name
        }

        return result

    def _generate_verdict_explanation(
        self,
        score: Dict,
        benchmarks: Dict,
        sector: str,
        stage: str
    ) -> str:
        """Generate human-readable explanation for the verdict"""

        verdict = score.get('verdict', 'Insufficient Data')
        composite = score.get('composite')

        if composite is None:
            return f"Insufficient benchmark data available for {sector}/{stage} cohort. Consider manual evaluation based on qualitative factors."

        # Count metrics above/below median
        above_median = sum(1 for b in benchmarks.values() if b.get('status') == 'above')
        below_median = sum(1 for b in benchmarks.values() if b.get('status') == 'below')
        total_metrics = len(benchmarks)

        explanation_parts = [
            f"**Verdict: {verdict}**",
            f"\nComposite Score: {composite:.1f}/100",
            f"\nCohort: {sector.title()}/{stage.title()}",
            f"\n**Benchmark Performance:**",
            f"- {above_median}/{total_metrics} metrics above median",
            f"- {below_median}/{total_metrics} metrics below median"
        ]

        # Add specific insights based on verdict
        if verdict == "Proceed":
            explanation_parts.append(
                "\n**Recommendation:** Strong metrics relative to cohort. Consider advancing to due diligence."
            )
        elif verdict == "Track":
            explanation_parts.append(
                "\n**Recommendation:** Mixed performance. Monitor progress and re-evaluate in 3-6 months."
            )
        elif verdict == "Pass":
            explanation_parts.append(
                "\n**Recommendation:** Metrics below cohort standards. Requires significant improvement before investment."
            )

        # Highlight top performing metrics
        if benchmarks:
            top_metrics = sorted(
                [(k, v) for k, v in benchmarks.items() if v.get('percentile', 0) >= 75],
                key=lambda x: x[1].get('percentile', 0),
                reverse=True
            )[:3]

            if top_metrics:
                explanation_parts.append("\n**Top Strengths:**")
                for metric_name, metric_data in top_metrics:
                    percentile = metric_data.get('percentile', 0)
                    explanation_parts.append(f"- {metric_name}: {percentile:.0f}th percentile")

            # Highlight areas of concern
            weak_metrics = sorted(
                [(k, v) for k, v in benchmarks.items() if v.get('percentile', 100) <= 25],
                key=lambda x: x[1].get('percentile', 0)
            )[:3]

            if weak_metrics:
                explanation_parts.append("\n**Areas for Improvement:**")
                for metric_name, metric_data in weak_metrics:
                    percentile = metric_data.get('percentile', 0)
                    explanation_parts.append(f"- {metric_name}: {percentile:.0f}th percentile")

        return "\n".join(explanation_parts)
