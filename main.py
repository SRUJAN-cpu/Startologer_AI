from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import vision, bigquery
from google.cloud import aiplatform as vertex_ai
from google.cloud.aiplatform.gapic.schema import predict
from google.cloud.aiplatform.gapic import PredictionServiceClient
from typing import List
import uvicorn
import tempfile
import os
import json
import asyncio

app = FastAPI()

# Allow CORS for testing frontend (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Cloud clients once
vision_client = vision.ImageAnnotatorClient()
bigquery_client = bigquery.Client()
vertex_ai.init(project="YOUR_PROJECT_ID", location="YOUR_PROJECT_LOCATION")
prediction_client = PredictionServiceClient()

# Vertex AI endpoints and models
VERTEX_NLP_ENDPOINT = "projects/YOUR_PROJECT_ID/locations/YOUR_PROJECT_LOCATION/endpoints/YOUR_ENDPOINT_ID"

# Utility: Save uploaded file to temp and return path
async def save_temp_file(upload_file: UploadFile) -> str:
    suffix = os.path.splitext(upload_file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        content = await upload_file.read()
        tmp_file.write(content)
        return tmp_file.name

# Function: Extract text from PDF/image via Vision API
def extract_text_from_file(file_path: str) -> str:
    with open(file_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = vision_client.document_text_detection(image=image)
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")

    return response.full_text_annotation.text

# Function: Call Vertex AI NLP model for text analysis (e.g. summarization, entity extraction)
def vertex_ai_nlp_analyze(text: str) -> dict:
    instance = predict.instance.TextSnippet(content=text, mime_type="text/plain")
    instances = [instance]
    response = prediction_client.predict(endpoint=VERTEX_NLP_ENDPOINT, instances=instances)
    # Assuming response.predictions contains JSON with extracted info
    output = response.predictions[0]
    return output

# Function: BigQuery benchmark query example
def bigquery_benchmark_query(sector: str) -> dict:
    query = f"""
    SELECT startup_name, metric, value
    FROM `YOUR_PROJECT.YOUR_DATASET.startup_metrics`
    WHERE sector = @sector
    ORDER BY value DESC
    LIMIT 5
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("sector", "STRING", sector)
        ]
    )
    query_job = bigquery_client.query(query, job_config=job_config)
    results = query_job.result()
    benchmarks = []
    for row in results:
        benchmarks.append({"startup_name": row.startup_name, "metric": row.metric, "value": row.value})
    return {"benchmarks": benchmarks}

# Function: Simple risk flagging logic
def detect_risks(structured_notes: dict) -> List[str]:
    flags = []
    # Example: Check for inconsistent revenue growth
    revenue_growth = structured_notes.get("revenue_growth", None)
    if revenue_growth and (revenue_growth > 200 or revenue_growth < -50):
        flags.append("Unusually high or negative revenue growth detected.")
    # Add more rules as needed
    return flags

@app.post("/evaluate-startup/")
async def evaluate_startup(pitchdeck: UploadFile = File(...), sector: str = "tech"):
    try:
        # Step 1: Save upload file
        file_path = await save_temp_file(pitchdeck)

        # Step 2: Extract text using Vision API
        raw_text = extract_text_from_file(file_path)

        # Step 3: Analyze text with Vertex AI NLP model
        ai_analysis = vertex_ai_nlp_analyze(raw_text)

        # Step 4: Query BigQuery for benchmarking data
        benchmarks = bigquery_benchmark_query(sector)

        # Step 5: Risk flag detection based on AI analysis output
        risks = detect_risks(ai_analysis)

        # Clean up temp file
        os.remove(file_path)

        # Prepare response
        result = {
            "structured_notes": ai_analysis,
            "benchmarks": benchmarks,
            "risk_flags": risks,
            "summary": ai_analysis.get("summary", "No summary available")
        }
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
                          
