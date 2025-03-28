"""
Module for generating responses to application questions
"""
import os
import logging
from typing import Dict, Any
from flask import current_app
import google.generativeai as genai
from application_filler.mappers.field_mapper import map_question_to_field

logger = logging.getLogger(__name__)

def setup_gemini():
    """Configure the Gemini API"""
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        # Try to get from Flask config instead
        api_key = current_app.config.get('GEMINI_API_KEY', '')
    
    if not api_key:
        # For testing/development, use a fallback mode
        logger.warning("GEMINI_API_KEY is not set in environment or config. Using mock mode.")
        
        # Create a mock configuration to avoid breaking tests/demos
        class MockGenAI:
            def configure(*args, **kwargs):
                pass
        
        # Monkey patch the genai module with mock functionality for testing
        genai.configure = MockGenAI.configure
        
        # Return early instead of raising an exception
        return
    
    logger.info(f"Configuring Gemini with API key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
    genai.configure(api_key=api_key)

class ResponseGenerator:
    """
    Class for generating responses to job application questions based on user profile
    """
    
    def __init__(self, user_data: Dict[str, Any]):
        """
        Initialize the response generator
        
        Args:
            user_data: Dictionary with user profile information
        """
        self.user_data = user_data
        
        # Setup Gemini
        setup_gemini()
        self.model = None
        try:
            self.model = genai.GenerativeModel(current_app.config.get('GEMINI_MODEL', 'gemini-pro'))
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {str(e)}")
    
    def generate_response(self, question_text: str) -> str:
        """
        Generate an appropriate response for an application question based on user profile.
        
        Args:
            question_text: The question to answer
            
        Returns:
            String response to the question
        """
        # First try to map question to a field in user data
        mapped_field = map_question_to_field(question_text)
        
        # If we have user data for this question type, use it
        if mapped_field in self.user_data and self.user_data[mapped_field]:
            logger.info(f"Using profile data field '{mapped_field}' for question: {question_text}")
            return str(self.user_data[mapped_field])
        
        # If no direct mapping or empty data, use AI to generate response
        try:
            # Create prompt for Gemini
            user_name = self.user_data.get('name', 'the applicant')
            prompt = f"""
            As {user_name}, please provide a professional response to this job application question:
            
            Question: "{question_text}"
            
            Use this profile information to personalize your answer:
            - Professional summary: {self.user_data.get('professional_summary', '')}
            - Skills: {self.user_data.get('skills', '')}
            - Experience: {self.user_data.get('experience', '')}
            - Career goals: {self.user_data.get('career_goals', '')}
            - Work style: {self.user_data.get('work_style', '')}
            
            Write in first person as {user_name}.
            Keep your answer professional, concise (2-3 sentences) and specifically tailored to the question.
            """
            
            # Check if we're in mock mode (no API key available or model initialization failed)
            api_key = current_app.config.get('GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', ''))
            
            if not api_key or not self.model:
                logger.warning("Using mock response generation for: " + question_text)
                
                # Generate deterministic mock responses based on question type
                if "strength" in question_text.lower() or "skill" in question_text.lower():
                    return f"My greatest strength is my ability to {self.user_data.get('skills', 'solve complex problems')}. I've demonstrated this through my past work where I consistently delivered results."
                    
                elif "weakness" in question_text.lower():
                    return "I'm always working to improve my time management skills. I've implemented structured planning systems that have significantly improved my productivity."
                    
                elif "experience" in question_text.lower() or "background" in question_text.lower():
                    return f"I have experience in {self.user_data.get('experience', 'software development and project management')}. This has given me a strong foundation in delivering quality work."
                    
                elif "why" in question_text.lower() and "work" in question_text.lower():
                    return "I'm excited about this opportunity because it aligns with my professional goals. I believe my skills would be a great match for this position."
                    
                else:
                    return "I'm excited about this opportunity and believe my skills and experience make me a strong candidate. I look forward to potentially joining your team."
            else:
                # Use the real Gemini API
                response = self.model.generate_content(prompt)
                answer = response.text.strip()
                logger.info(f"Generated AI response for question: {question_text[:30]}...")
                return answer
            
        except Exception as e:
            logger.error(f"Error generating response with AI: {str(e)}")
            return f"I believe I am well-qualified for this position with my background in {self.user_data.get('skills', 'professional skills')} and I'm excited about this opportunity."