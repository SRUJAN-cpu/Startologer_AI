import requests

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with your actual API key

def get_processed_data(details):
    """
    Send details to Google Gemini and get processed data back.
    :param details: dict with fields like idea, target_audience, etc.
    :return: dict with processed data from Gemini
    """
    prompt = (
        f"Idea: {details.get('idea')}\n"
        f"Target Audience: {details.get('target_audience')}\n"
        f"Meeting Transcript: {details.get('meeting_transcript')}\n"
        f"Pitchdeck Text: {details.get('pitchdeck_text')}\n"
        "Please analyze and summarize the above information."
    )

    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "key": GEMINI_API_KEY
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=data)
    response.raise_for_status()
    result = response.json()
    # Extract the generated text from the response
    processed_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    return {"summary": processed_text}