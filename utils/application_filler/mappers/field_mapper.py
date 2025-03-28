"""
Maps application form questions to user profile fields
"""
import re
import logging

logger = logging.getLogger(__name__)

# Dictionary mapping question patterns to user profile fields
QUESTION_TO_FIELD_MAP = {
    # Name related questions
    r'(?i)(?:your|full|legal)?\s*name': 'name',
    
    # Email related questions
    r'(?i)(?:your|work|personal)?\s*email': 'email',
    
    # Phone related questions
    r'(?i)(?:your|mobile|phone|cell)\s*(?:number|phone|#)': 'phone',
    
    # Professional summary related questions
    r'(?i)(?:tell us about yourself|introduce yourself|professional summary|summary of qualifications|career summary|profile summary)': 'professional_summary',
    
    # Skills related questions
    r'(?i)(?:your|technical|professional|key)?\s*(?:skills|expertise|strengths|competencies)': 'skills',
    r'(?i)what (?:technical|programming|development) (?:languages|tools|frameworks) (?:do you|are you|have you)': 'skills',
    
    # Experience related questions
    r'(?i)(?:your|work|professional|relevant)?\s*(?:experience|background|history)': 'experience',
    r'(?i)tell us about your (?:experience|background|work history)': 'experience',
    r'(?i)years of experience': 'experience',
    
    # Career goals related questions
    r'(?i)(?:your|career|professional)?\s*(?:goals|objectives|aspirations)': 'career_goals',
    r'(?i)where do you see yourself': 'career_goals',
    
    # Achievements related questions
    r'(?i)(?:your|greatest|biggest|significant)?\s*(?:achievement|accomplishment)': 'biggest_achievement',
    
    # Work style related questions
    r'(?i)(?:your|preferred)?\s*(?:work style|working style|work preference)': 'work_style',
    r'(?i)(?:describe|tell us about) your (?:work style|working style|approach to work)': 'work_style',
    
    # Industry attraction related questions
    r'(?i)why (?:are you interested in|do you want to work in) this (?:industry|field|role|position)': 'industry_attraction',
    
    # Relocation related questions
    r'(?i)(?:are you willing to|would you consider|can you) relocate': 'willing_to_relocate',
    r'(?i)willing(?:ness)? to relocate': 'willing_to_relocate',
    
    # Work authorization related questions
    r'(?i)(?:are you|work) authoriz(?:ed|ation)': 'authorization_status',
    r'(?i)(?:legal|eligible) to work': 'authorization_status',
    
    # Start date related questions
    r'(?i)(?:when can you|earliest|available|start) (?:start|date)': 'available_start_date',
    
    # Portfolio/LinkedIn questions
    r'(?i)(?:your|professional)?\s*(?:portfolio|website|linkedin|github)': 'portfolio_links'
}

def map_question_to_field(question_text: str) -> str:
    """
    Maps a question to a user profile field.
    
    Args:
        question_text: The question to map
    
    Returns:
        The name of the user profile field that best matches the question, or empty string if no match
    """
    if not question_text:
        return ""
    
    # Clean the question text (remove punctuation, extra spaces)
    clean_text = question_text.strip()
    
    # Try to match the question against our patterns
    for pattern, field in QUESTION_TO_FIELD_MAP.items():
        if re.search(pattern, clean_text):
            logger.debug(f"Mapped question '{clean_text}' to field '{field}' using pattern '{pattern}'")
            return field
    
    # If no direct match, try a more flexible approach with keyword matching
    keywords = {
        'name': ['name', 'full name', 'legal name'],
        'email': ['email', 'e-mail', 'electronic mail'],
        'phone': ['phone', 'telephone', 'mobile', 'cell'],
        'skills': ['skills', 'abilities', 'competencies', 'qualifications', 'expertise'],
        'experience': ['experience', 'work history', 'employment history', 'job history'],
        'work_style': ['work style', 'working style', 'team work', 'collaboration'],
        'career_goals': ['goals', 'objectives', 'aspirations', 'career plan']
    }
    
    lower_text = clean_text.lower()
    for field, field_keywords in keywords.items():
        for keyword in field_keywords:
            if keyword.lower() in lower_text:
                logger.debug(f"Mapped question '{clean_text}' to field '{field}' using keyword '{keyword}'")
                return field
    
    # No match found
    logger.debug(f"No mapping found for question: '{clean_text}'")
    return ""