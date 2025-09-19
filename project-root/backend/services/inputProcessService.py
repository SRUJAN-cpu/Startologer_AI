import os
from textExtraction.textExtractor import extract_text
from helpers.llmCient import get_processed_data, get_risk_assessment

class InputProcessService:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
    
    def process_input_data(self, form_data, files):
        """
        Process all input data including text fields and uploaded files.
        
        :param form_data: Dictionary containing text inputs (idea, target_audience, etc.)
        :param files: Dictionary containing uploaded files
        :return: Dictionary with processed results from LLM
        """
        # Extract text inputs
        idea = form_data.get('idea')
        target_audience = form_data.get('target_audience')
        meeting_transcript = form_data.get('meeting_transcript', '')
        
        # Process uploaded file if present
        pitchdeck_text = ''
        file = files.get('pitchdeck')
        if file:
            file_path = os.path.join(self.upload_folder, file.filename)
            file.save(file_path)
            try:
                pitchdeck_text = extract_text(file_path)
            except Exception as e:
                print(f"Error extracting text from file: {e}")
                pitchdeck_text = "Error processing uploaded file"
            finally:
                # Optional: Clean up uploaded file after processing
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # Prepare data for LLM processing
        details = {
            'idea': idea,
            'target_audience': target_audience,
            'meeting_transcript': meeting_transcript,
            'pitchdeck_text': pitchdeck_text
        }
        
        # Get processed results from LLM
        try:
            investment_analysis = get_processed_data(details)
            risk_assessment = get_risk_assessment(details)
            return {
                'success': True,
                'data': {
                    'investment_analysis': investment_analysis,
                    'risk_assessment': risk_assessment
                },
                'input_summary': {
                    'idea': idea,
                    'target_audience': target_audience,
                    'has_transcript': bool(meeting_transcript),
                    'has_pitchdeck': bool(pitchdeck_text)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"LLM processing failed: {str(e)}",
                'data': None
            }

    def validate_required_fields(self, form_data):
        """
        Validate that required fields are present.
        
        :param form_data: Dictionary containing form inputs
        :return: Tuple (is_valid, error_message)
        """
        idea = form_data.get('idea')
        target_audience = form_data.get('target_audience')
        
        if not idea or not target_audience:
            return False, "idea and target_audience are required fields"
        
        return True, None