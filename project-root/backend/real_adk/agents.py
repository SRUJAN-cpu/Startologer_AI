"""
ADK Agents for StartupEval AI
Agents defined using Google's real ADK (LlmAgent class)

Agent Architecture:
    RootAgent (Orchestrator)
        ├── DocParserAgent (Document parsing)
        ├── AnalysisAgent (AI analysis)
        └── DocReportAgent (Benchmarking & reporting)
"""

from google.adk.agents import LlmAgent
from typing import List

from .config import ADKConfig
from .tools import (
    # Document Parsing Tools
    upload_to_gcs,
    parse_document_with_docai,
    extract_entities_and_kpis,

    # Analysis Tools
    analyze_with_gemini,
    extract_financial_metrics,

    # Reporting Tools
    compare_benchmarks,
    detect_red_flags,
    calculate_investment_score,
    generate_evaluation_report,
    save_report_to_gcs,
    save_to_firestore
)


def create_doc_parser_agent() -> LlmAgent:
    """
    Create Document Parser Agent

    This agent handles document upload, parsing, and entity extraction.
    It uses Document AI for OCR and entity recognition.

    Capabilities:
    - Upload files to Google Cloud Storage
    - Parse PDFs and images with Document AI
    - Extract entities, KPIs, and financial data
    - Structure data for downstream analysis

    Returns:
        Configured LlmAgent for document parsing
    """
    return LlmAgent(
        model=ADKConfig.MODEL_NAME,
        name="DocParserAgent",

        instruction="""You are a specialized document parsing agent for startup evaluation.

Your responsibilities:
1. Upload user documents to Google Cloud Storage
2. Use Document AI to parse PDFs and extract text
3. Extract entities (companies, people, dates, financial values)
4. Extract KPIs and business metrics from the documents
5. Structure all data for downstream analysis

When handling documents:
- First upload to GCS to get gs:// URI
- Then parse with Document AI
- Extract and categorize all entities
- Return structured JSON with all extracted data

Be thorough and accurate. The quality of your extraction directly impacts
the downstream analysis and evaluation.""",

        description="""Parses startup documents (pitch decks, financials) using Document AI.
Extracts text, entities, tables, and KPIs. First agent in the evaluation pipeline.""",

        tools=[
            upload_to_gcs,
            parse_document_with_docai,
            extract_entities_and_kpis
        ],

        output_key="parsed_documents"
    )


def create_analysis_agent() -> LlmAgent:
    """
    Create Analysis Agent

    This agent performs AI-powered analysis of startup documents using Gemini.
    It generates executive summaries, market analysis, risk assessment, and
    recommendations.

    Capabilities:
    - Analyze combined text with Gemini AI
    - Generate executive summaries
    - Perform market opportunity analysis
    - Identify and assess risks
    - Extract financial metrics (ARR, MRR, CAC, LTV, etc.)
    - Provide actionable recommendations

    Returns:
        Configured LlmAgent for startup analysis
    """
    return LlmAgent(
        model=ADKConfig.MODEL_NAME,
        name="AnalysisAgent",

        instruction="""You are an expert venture capital analyst specialized in startup evaluation.

Your responsibilities:
1. Analyze parsed startup documents comprehensively
2. Generate concise executive summaries (2-4 sentences)
3. Assess market opportunity (size, growth, competition)
4. Identify and evaluate risks (high/medium/low impact)
5. Extract financial metrics (ARR, MRR, CAC, LTV, churn, growth)
6. Provide actionable investment recommendations

Analysis Guidelines:
- Be objective and data-driven
- Focus on key value drivers and risks
- Extract all quantifiable metrics
- Assess market dynamics and competitive position
- Consider regulatory and execution risks
- Provide clear, actionable recommendations

Use the analyze_with_gemini tool for comprehensive AI analysis, and
extract_financial_metrics for quantitative metric extraction.""",

        description="""AI-powered startup analyst using Gemini. Generates executive summaries,
market analysis, risk assessments, and recommendations. Extracts financial metrics.""",

        tools=[
            analyze_with_gemini,
            extract_financial_metrics
        ],

        output_key="analysis_result"
    )


def create_doc_report_agent() -> LlmAgent:
    """
    Create Document Report Agent

    This agent performs benchmarking, scoring, and report generation.
    It compares the startup against industry benchmarks and produces
    final evaluation reports.

    Capabilities:
    - Compare metrics against industry benchmarks
    - Calculate composite investment scores
    - Generate verdict (Proceed/Track/Pass)
    - Create comprehensive evaluation reports
    - Save reports to GCS and Firestore

    Returns:
        Configured LlmAgent for reporting and benchmarking
    """
    return LlmAgent(
        model=ADKConfig.MODEL_NAME,
        name="DocReportAgent",

        instruction="""You are a specialized reporting agent for startup evaluation.

Your responsibilities:
1. Compare startup metrics against industry benchmarks
2. Detect red flags (inflated TAM, high churn, poor unit economics)
3. Calculate composite investment score (0-100)
4. Determine verdict: Proceed (strong), Track (monitor), or Pass (weak)
5. Generate comprehensive evaluation reports
6. Save reports to Google Cloud Storage and Firestore

Benchmarking Guidelines:
- Use sector-specific benchmarks (SaaS, FinTech, etc.)
- Consider funding stage (seed, Series A, etc.)
- Compare key metrics: ARR, MRR, CAC, LTV, churn, growth
- Calculate percentile rankings for each metric
- Weight metrics appropriately for composite score

Red Flag Detection:
- Use detect_red_flags tool with analysis results and metrics
- Identify: inflated TAM, high churn (>5%), poor LTV:CAC (<3:1)
- Check for inconsistent metrics and missing data
- Include red flags in final report

Verdict Criteria:
- Proceed: Score > 65, strong metrics relative to cohort, no high-severity red flags
- Track: Score 45-65, mixed performance, monitor progress
- Pass: Score < 45, below cohort standards, or multiple high-severity red flags

Generate detailed reports with:
- Executive summary
- Market analysis with TAM/SAM/SOM
- Risk assessment
- Red flags (explicit detection results)
- Benchmark comparisons
- Investment score and verdict
- Actionable recommendations""",

        description="""Benchmarking and reporting agent. Compares metrics against industry data,
calculates investment scores, determines verdicts, and generates final reports.""",

        tools=[
            compare_benchmarks,
            detect_red_flags,
            calculate_investment_score,
            generate_evaluation_report,
            save_report_to_gcs,
            save_to_firestore
        ],

        output_key="final_report"
    )


def create_startup_eval_root_agent() -> LlmAgent:
    """
    Create Root Orchestrator Agent

    This is the main entry point for the StartupEval AI system.
    It coordinates the three specialized sub-agents in a hierarchical
    multi-agent architecture.

    Agent Flow:
        User Request → RootAgent
            ↓
            ├── DocParserAgent: Parse documents, extract entities
            │      ↓
            ├── AnalysisAgent: Gemini analysis, metric extraction
            │      ↓
            └── DocReportAgent: Benchmarking, scoring, report generation

    The root agent intelligently routes requests to the appropriate
    sub-agent based on the task requirements.

    Returns:
        Configured root LlmAgent with all sub-agents
    """
    # Create specialized sub-agents
    doc_parser = create_doc_parser_agent()
    analyzer = create_analysis_agent()
    reporter = create_doc_report_agent()

    # Create root orchestrator with sub-agents
    root_agent = LlmAgent(
        model=ADKConfig.MODEL_NAME,
        name="StartupEvalRootAgent",

        instruction="""You are the orchestrator for StartupEval AI, an intelligent startup evaluation platform.

Your role is to coordinate specialized agents to evaluate startups comprehensively:

1. DocParserAgent: Handles document upload and parsing
   - Use for: "Parse these documents", "Extract data from PDFs"
   - Uploads files to GCS and uses Document AI for extraction

2. AnalysisAgent: Performs AI-powered analysis
   - Use for: "Analyze this startup", "Generate evaluation"
   - Uses Gemini for comprehensive analysis and metric extraction

3. DocReportAgent: Benchmarking and reporting
   - Use for: "Compare to benchmarks", "Generate report", "Calculate score"
   - Compares metrics, scores startup, generates final reports

Orchestration Guidelines:
- For new evaluations: Route through all agents sequentially
  (Parser → Analyzer → Reporter)
- For specific tasks: Route to the appropriate specialized agent
- Ensure data flows correctly between agents
- Validate outputs before passing to next agent
- Handle errors gracefully and provide user feedback

When a user uploads documents for evaluation:
1. Route to DocParserAgent to parse and extract data
2. Pass extracted data to AnalysisAgent for comprehensive analysis
3. Pass analysis to DocReportAgent for benchmarking and final report
4. Return complete evaluation to user

Be efficient and ensure all agents work together seamlessly.""",

        description="""Root orchestrator for StartupEval AI. Coordinates document parsing,
AI analysis, and benchmarking agents to produce comprehensive startup evaluations.""",

        sub_agents=[doc_parser, analyzer, reporter],

        output_key="evaluation_result"
    )

    return root_agent


# ============================================================================
# Agent Factory Functions
# ============================================================================

def get_startup_eval_agent() -> LlmAgent:
    """
    Get the fully configured StartupEval AI agent.

    This is the main entry point for using the agent system.
    Call this function to get the root agent with all sub-agents configured.

    Returns:
        Root LlmAgent ready for startup evaluation

    Example:
        ```python
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from real_adk.agents import get_startup_eval_agent

        # Get agent
        agent = get_startup_eval_agent()

        # Create runner with session
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, session_service=session_service)

        # Process user request
        response = runner.run(
            user_id="user123",
            prompt="Evaluate these startup documents",
            artifacts={"file_paths": ["path/to/doc1.pdf", "path/to/doc2.pdf"]}
        )
        ```
    """
    print("[START] Initializing StartupEval AI Agent System")
    print(f"   Model: {ADKConfig.MODEL_NAME}")
    print(f"   Project: {ADKConfig.PROJECT_ID}")

    agent = create_startup_eval_root_agent()

    print("[OK] Agent system ready")
    return agent


def list_agent_capabilities() -> dict:
    """
    List all agent capabilities and tools.

    Returns:
        Dictionary with agent names, descriptions, and available tools
    """
    return {
        "RootAgent": {
            "name": "StartupEvalRootAgent",
            "description": "Orchestrates all sub-agents for complete startup evaluation",
            "sub_agents": ["DocParserAgent", "AnalysisAgent", "DocReportAgent"]
        },
        "DocParserAgent": {
            "name": "DocParserAgent",
            "description": "Parses documents using Document AI and extracts entities",
            "tools": [
                "upload_to_gcs",
                "parse_document_with_docai",
                "extract_entities_and_kpis"
            ]
        },
        "AnalysisAgent": {
            "name": "AnalysisAgent",
            "description": "Performs AI-powered startup analysis with Gemini",
            "tools": [
                "analyze_with_gemini",
                "extract_financial_metrics"
            ]
        },
        "DocReportAgent": {
            "name": "DocReportAgent",
            "description": "Benchmarks metrics and generates evaluation reports",
            "tools": [
                "compare_benchmarks",
                "detect_red_flags",
                "calculate_investment_score",
                "generate_evaluation_report",
                "save_report_to_gcs",
                "save_to_firestore"
            ]
        }
    }
