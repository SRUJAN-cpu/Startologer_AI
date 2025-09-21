import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv

# Prefer a current Gemini model/endpoint; many older v1beta models are deprecated
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

def _ensure_api_key_loaded() -> str | None:
    """Try to obtain GEMINI_API_KEY; attempt .env loads if missing."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key
    # Try to find .env from current working dir
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                print(f"[analysis_helper] Loaded GEMINI_API_KEY via {dotenv_path}")
            except Exception:
                pass
            return api_key
    # Fallback: explicit relative to backend folder
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    explicit_path = os.path.join(backend_dir, '.env')
    if os.path.exists(explicit_path):
        load_dotenv(explicit_path, override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                print(f"[analysis_helper] Loaded GEMINI_API_KEY via explicit path {explicit_path}")
            except Exception:
                pass
            return api_key
    return None


def analyze_combined_text(text: str) -> Dict[str, Any]:
    """
    Call Gemini to analyze the combined text content and return a structured AnalysisResult.
    Falls back to a heuristic/dummy result if API key is missing or request fails.
    """
    if not text or len(text.strip()) == 0:
        return _dummy_result("No text extracted from documents.")

    api_key = _ensure_api_key_loaded()
    if not api_key:
        # No API key configured; return fallback
        return _dummy_result("Gemini API key not configured. Returning placeholder analysis.")

    prompt = """
You are an experienced venture capital investment analyst.
Your job is to rigorously analyze startup-related documents and produce ONLY a valid JSON object.
Follow the schema EXACTLY — no extra text, no explanations, no placeholders, no "N/A".
If information is missing, intelligently infer reasonable assumptions based on typical startups in the sector/stage.

OUTPUT SCHEMA:
{{
    "executiveSummary": string,  // 2–4 sentences summarizing the opportunity
    "marketAnalysis": {{
        "marketSize": string,      // concise estimate or characterization
        "growthRate": string,      // CAGR or directional growth
        "competition": string,     // key players, substitutes, or competitive dynamics
        "entryBarriers": string,   // capital, tech, network effects, distribution, brand, etc.
        "regulation": string       // practical regulatory landscape (1–3 sentences). Always provide something plausible; never write placeholders.
    }},
    "risks": [
        {{
            "factor": string,
            "impact": "low" | "medium" | "high",
            "description": string     // concrete risk description, not vague
        }}
    ],
    "recommendations": [
        {{
            "title": string,
            "description": string     // actionable suggestions for founders or investors
        }}
    ]
}}

RULES:
- Output must be STRICT JSON, parseable without errors.
- Be concise but analytical, as if writing due diligence notes for a VC firm.
- Never include commentary outside the JSON block.
- If data is not explicitly in the document, infer based on common industry knowledge.
- Keep all values realistic, professional, and startup-relevant.

DOCUMENT CONTENT (trimmed):
{doc}
""".format(doc=text[:8000])

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}

    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        # Try to parse JSON; if it fails, fallback
        import json
        try:
            parsed = json.loads(raw_text)
            result = _coerce_result(parsed)
            try:
                result['llmStatus'] = {'ok': True}
            except Exception:
                pass
            return result
        except Exception:
            # try to strip code fences and re-parse
            cleaned = _strip_code_fences(raw_text)
            try:
                parsed = json.loads(cleaned)
                result = _coerce_result(parsed)
                try:
                    result['llmStatus'] = {'ok': True}
                except Exception:
                    pass
                return result
            except Exception:
                # last resort: extract the first top-level JSON object
                maybe = _extract_json_object(cleaned)
                if maybe:
                    try:
                        parsed = json.loads(maybe)
                        result = _coerce_result(parsed)
                        try:
                            result['llmStatus'] = {'ok': True}
                        except Exception:
                            pass
                        return result
                    except Exception:
                        pass
                return _dummy_result("Model returned non-JSON output. Showing placeholder analysis.")
    except requests.HTTPError as http_err:
        # Gracefully handle quota/rate-limit without long waits
        status = getattr(resp, 'status_code', None) or 0
        retry_after = None
        try:
            j = resp.json()
            # RetryInfo may be present in seconds
            for d in j.get('error', {}).get('details', []) or []:
                if d.get('@type', '').endswith('RetryInfo'):
                    ra = d.get('retryDelay') or ''
                    # retryDelay like '26s'
                    if isinstance(ra, str) and ra.endswith('s'):
                        try:
                            retry_after = int(float(ra[:-1]))
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            _ = resp.text  # not surfaced to users
        except Exception:
            pass
        # Keep neutral text for users; attach details via llmStatus for diagnostics
        out = _dummy_result("LLM service is temporarily unavailable.")
        out['llmStatus'] = { 'ok': False, 'status': status, 'retryAfterSec': retry_after }
        return out
    except Exception as e:
        out = _dummy_result("LLM service is temporarily unavailable.")
        try:
            out['llmStatus'] = { 'ok': False, 'error': str(e) }
        except Exception:
            pass
        return out


def infer_cohort(text: str) -> Dict[str, Any]:
    """Use LLM to infer sector/stage from raw text. Returns lowercase keys.
    Output example: {"sector": "saas", "stage": "seed"}
    """
    api_key = _ensure_api_key_loaded()
    if not api_key:
        return {}
    prompt = f"""
    Read the startup documents below and output STRICT JSON with:
    {{
      "sector": string,  // short, lowercase label (examples: saas, fintech, bfsi, ites, hr, ecommerce, healthtech, edtech, mobility, logistics, gaming, marketplace, ai, security, proptech, media, travel, resale)
      "stage": string    // one of: pre-seed, seed, angel, series a, series b, series c, growth
    }}
    If unclear, leave the value as an empty string. Only return JSON.

    DOCUMENT (trimmed):
    {text[:6000]}
    """

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload, timeout=40)
        resp.raise_for_status()
        data = resp.json()
        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        import json
        cleaned = _strip_code_fences(raw_text)
        try:
            obj = json.loads(cleaned)
        except Exception:
            maybe = _extract_json_object(cleaned)
            if not maybe:
                return {}
            try:
                obj = json.loads(maybe)
            except Exception:
                return {}
        sec = (obj.get("sector") or "").strip().lower()
        stg = (obj.get("stage") or "").strip().lower()
        return {"sector": sec, "stage": stg}
    except Exception:
        return {}


def infer_benchmark_estimates(text: str, sector: str, stage: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the LLM to suggest benchmark medians for the given cohort and provide qualitative comparisons.
    Returns a dict like:
    {
      "cohort": {"sector": "saas", "stage": "seed"},
      "estimates": {
         "growthYoY": {"median": 60, "unit": "%"},
         "cac": {"median": 200, "unit": "USD"}
      },
      "relative": {"growthYoY": "above", "cac": "below"},
      "notes": "LLM-estimated; validate with local dataset"
    }
    """
    api_key = _ensure_api_key_loaded()
    if not api_key:
        return {}
    # Only include metrics we have values for
    present = {k: v for k, v in (metrics or {}).items() if v is not None}
    if not present:
        return {}
    prompt = (
        "You are a VC analyst. Based on the documents and the cohort, suggest typical medians for the given metrics "
        "and qualitatively compare the company's values vs those medians. Output STRICT JSON only with this schema:\n"
        "{\n  \"cohort\": {\"sector\": string, \"stage\": string},\n  \"estimates\": { [metric: string]: { \"median\": number, \"unit\": string } },\n  \"relative\": { [metric: string]: \"above\"|\"near\"|\"below\" },\n  \"notes\": string\n}\n\n"
        f"Cohort: sector='{sector}', stage='{stage}'.\n"
        f"Company metrics (unit as implied): {present}.\n"
        "Use conservative, broadly-cited figures for early-stage startups. If uncertain for a metric, omit it."
    )

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload, timeout=50)
        resp.raise_for_status()
        data = resp.json()
        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        import json
        cleaned = _strip_code_fences(raw_text)
        try:
            obj = json.loads(cleaned)
        except Exception:
            maybe = _extract_json_object(cleaned)
            if not maybe:
                return {}
            try:
                obj = json.loads(maybe)
            except Exception:
                return {}
        # Light normalization of fields
        out: Dict[str, Any] = {
            "cohort": {
                "sector": (obj.get("cohort", {}).get("sector") or sector or "").strip().lower(),
                "stage": (obj.get("cohort", {}).get("stage") or stage or "").strip().lower()
            },
            "estimates": obj.get("estimates") or {},
            "relative": obj.get("relative") or {},
            "notes": obj.get("notes") or "Estimates are directional; validate against dataset medians for the cohort."
        }
        return out
    except Exception:
        return {}


def gemini_ping() -> Dict[str, Any]:
    """Lightweight connectivity check for Gemini API with current configuration."""
    api_key = _ensure_api_key_loaded()
    if not api_key:
        return {"ok": False, "geminiKeyPresent": False, "error": "GEMINI_API_KEY not configured"}
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    payload = {"contents": [{"parts": [{"text": "ping"}]}]}
    try:
        resp = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload, timeout=20)
        status = resp.status_code
        if status >= 200 and status < 300:
            txt = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return {"ok": True, "status": status, "geminiKeyPresent": True, "textPreview": txt[:120]}
        return {"ok": False, "status": status, "geminiKeyPresent": True, "error": resp.text}
    except Exception as e:
        return {"ok": False, "geminiKeyPresent": True, "error": str(e)}


def _coerce_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure required keys exist with defaults
    return {
        "executiveSummary": obj.get("executiveSummary") or "Summary not provided.",
        "marketAnalysis": {
            "marketSize": obj.get("marketAnalysis", {}).get("marketSize") or "N/A",
            "growthRate": obj.get("marketAnalysis", {}).get("growthRate") or "N/A",
            "competition": obj.get("marketAnalysis", {}).get("competition") or "N/A",
            "entryBarriers": obj.get("marketAnalysis", {}).get("entryBarriers") or "N/A",
            "regulation": obj.get("marketAnalysis", {}).get("regulation") or "N/A",
        },
        "risks": [
            {
                "factor": r.get("factor", "Unknown"),
                "impact": r.get("impact", "medium"),
                "description": r.get("description", "")
            }
            for r in obj.get("risks", [])
        ] or [
            {"factor": "Information Risk", "impact": "medium", "description": "Insufficient data in documents."}
        ],
        "recommendations": [
            {
                "title": rec.get("title", "Next Steps"),
                "description": rec.get("description", "Provide more details to improve analysis quality.")
            }
            for rec in obj.get("recommendations", [])
        ] or [
            {"title": "Provide More Data", "description": "Upload more comprehensive documents for deeper insights."}
        ]
    }


def _dummy_result(reason: str) -> Dict[str, Any]:
    # Neutral, user-friendly fallback without exposing backend error details
    return {
        "executiveSummary": (
            "Preliminary summary based on the uploaded documents. "
            "Some details may be inferred; please review benchmarks, risks, and recommendations for context."
        ),
        "marketAnalysis": {
            "marketSize": "N/A",
            "growthRate": "N/A",
            "competition": "Unknown",
            "entryBarriers": "Unknown",
            "regulation": "Unknown"
        },
        "risks": [
            {"factor": "Data Quality", "impact": "medium", "description": "Limited or missing data may affect analysis accuracy."}
        ],
        "recommendations": [
            {"title": "Add Financials", "description": "Include revenue projections and unit economics for better assessment."},
            {"title": "Clarify GTM", "description": "Detail your go-to-market plan and milestones."}
        ]
    }


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith('```'):
        # remove leading ```json or ```
        first_nl = t.find('\n')
        if first_nl != -1:
            t = t[first_nl + 1 :]
        if t.endswith('```'):
            t = t[: -3]
    return t.strip()


def _extract_json_object(text: str) -> str | None:
    """Extract the first plausible top-level JSON object from text."""
    import re
    # naive approach: find content between the first '{' and its matching '}' using a stack
    start = text.find('{')
    if start == -1:
        return None
    stack = []
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            stack.append('{')
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack:
                    return text[start : i + 1]
    return None
