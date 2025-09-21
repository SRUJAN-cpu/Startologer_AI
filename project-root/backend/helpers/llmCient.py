import requests
import os
from dotenv import load_dotenv, find_dotenv

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
# Load environment variables (from a local .env file, if present; search upwards)
_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(_dotenv_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Diagnostic log (non-sensitive): whether key exists
try:
    print(f"[llmCient] GEMINI_API_KEY present: {bool(GEMINI_API_KEY)} (loaded from: {_dotenv_path or 'env only'})")
except Exception:
    pass

def get_processed_data(details):
    """
    Send startup details to Google Gemini for investment analysis.
    :param details: dict with fields like idea, target_audience, etc.
    :return: dict with structured investment analysis from Gemini
    """
    prompt = f"""
    You are an experienced startup investment analyst. Analyze the following startup information and provide a comprehensive investment evaluation:

    STARTUP INFORMATION:
    Business Idea: {details.get('idea', 'Not provided')}
    Target Audience: {details.get('target_audience', 'Not provided')}
    Meeting Transcript: {details.get('meeting_transcript', 'Not provided')}
    Pitch Deck Content: {details.get('pitchdeck_text', 'Not provided')}

    Please provide a structured analysis with the following sections:

    1. EXECUTIVE SUMMARY (2-3 sentences)
    - Overall investment thesis and recommendation

    2. MARKET OPPORTUNITY
    - Market size assessment (TAM/SAM/SOM )
    - Market timing and trends
    - Competitive landscape insights

    3. BUSINESS MODEL EVALUATION
    - Revenue model clarity
    - Scalability potential
    - Unit economics (if available)

    4. FOUNDER & TEAM ASSESSMENT
    - Founder-market fit
    - Team composition and experience
    - Execution capability indicators

    5. TRACTION & METRICS
    - Customer acquisition and retention
    - Growth trajectory
    - Key performance indicators

    6. RISK FACTORS
    - Technical risks
    - Market risks
    - Execution risks
    - Red flags (if any)

    7. INVESTMENT RECOMMENDATION
    - Investment grade (A/B/C/D)
    - Key reasons for recommendation
    - Suggested next steps

    Format your response as a structured analysis that an investor can quickly digest.
    """

    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "key": GEMINI_API_KEY
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        if not GEMINI_API_KEY:
            return {
                "error": "GEMINI_API_KEY not configured",
                "investment_analysis": "Analysis unavailable: missing API key"
            }
        print("Sending payload:", payload)
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
        print("Gemini response:", response.text)
        result = response.json()
        # Extract the generated text from the response
        processed_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {
            "investment_analysis": processed_text,
            "analysis_type": "startup_evaluation",
            "timestamp": "2025-09-19"
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"API request failed: {str(e)}",
            "investment_analysis": "Analysis unavailable due to API error"
        }
    except Exception as e:
        return {
            "error": f"Processing failed: {str(e)}",
            "investment_analysis": "Analysis unavailable due to processing error"
        }

def get_risk_assessment(details):
    """
    Specialized function for risk assessment and red flag detection.
    """
    prompt = f"""
    As a startup risk analyst, identify potential red flags and risks in this startup:

    STARTUP DATA:
    {details.get('idea', 'Not provided')}
    Target Market: {details.get('target_audience', 'Not provided')}
    Additional Context: {details.get('meeting_transcript', 'Not provided')}

    Focus on:
    1. Market size inflation indicators
    2. Unrealistic growth projections
    3. Competitive blindness
    4. Technical feasibility concerns
    5. Team/founder red flags
    6. Financial inconsistencies

    Provide a risk score (1-10) and specific concerns.
    """

    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "key": GEMINI_API_KEY
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    try:
        if not GEMINI_API_KEY:
            return {
                "error": "GEMINI_API_KEY not configured",
                "risk_assessment": "Risk assessment unavailable: missing API key"
            }
        print("Sending risk assessment payload:", payload)
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
        print("Gemini risk response:", response.text)
        result = response.json()
        risk_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {
            "risk_assessment": risk_text,
            "analysis_type": "risk_assessment",
            "timestamp": "2025-09-19"
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"API request failed: {str(e)}",
            "risk_assessment": "Risk assessment unavailable due to API error"
        }
    except Exception as e:
        return {
            "error": f"Processing failed: {str(e)}",
            "risk_assessment": "Risk assessment unavailable due to processing error"
        }