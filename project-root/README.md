# README.md# Startologer_AI Backend Setup

## Prerequisites

- Python 3.10+
- pip (Python package manager)
- (Optional) [Virtualenv](https://virtualenv.pypa.io/en/latest/) for isolated environments

## Installation

1. **Clone the repository**

   ```sh
   git clone <your-repo-url>
   cd Startologer_AI/project-root/backend
   ```

2. **Create and activate a virtual environment (recommended)**

   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

## Configuration

- Set your Google Gemini API key in `helpers/llmCient.py`:
  ```python
  GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
  ```

## Running the Backend

1. **Start the Flask server**

   ```sh
   python Endpoints/initialEndpoints.py
   ```

2. **API Endpoints**
   - `POST /submit`  
     Accepts idea, target audience, meeting transcript, and pitchdeck (ppt/pdf) file.
   - `GET /get_processed_details`  
     Returns processed details (sample or from Gemini).

## File Uploads

- Uploaded files are stored in `backend/uploads/`.

## Text Extraction

- PPTX and PDF files are processed using `textExtraction/textExtractor.py`.

## LLM Integration

- Details are sent to Google Gemini via `helpers/llmCient.py`.

## Notes

- Ensure your API key is kept secure.
