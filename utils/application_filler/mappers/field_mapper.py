"""
Field mapper for application forms
Maps form field questions/labels to user profile fields
"""
import re
from typing import Dict, Optional

# Field mapping patterns
NAME_PATTERNS = [
    r'(?i)full\s*name',
    r'(?i)^name$',
    r'(?i)your\s*name',
    r'(?i)preferred\s*name',
    r'(?i)legal\s*name',
    r'(?i)first\s*and\s*last\s*name'
]

FIRST_NAME_PATTERNS = [
    r'(?i)first\s*name',
    r'(?i)given\s*name',
    r'(?i)forename'
]

LAST_NAME_PATTERNS = [
    r'(?i)last\s*name',
    r'(?i)family\s*name',
    r'(?i)surname'
]

EMAIL_PATTERNS = [
    r'(?i)e\-?mail',
    r'(?i)email\s*address',
    r'(?i)your\s*email'
]

PHONE_PATTERNS = [
    r'(?i)phone',
    r'(?i)mobile',
    r'(?i)cell',
    r'(?i)telephone'
]

ADDRESS_PATTERNS = [
    r'(?i)address',
    r'(?i)street',
    r'(?i)location'
]

CITY_PATTERNS = [
    r'(?i)city',
    r'(?i)town'
]

STATE_PATTERNS = [
    r'(?i)state',
    r'(?i)province',
    r'(?i)region'
]

ZIP_PATTERNS = [
    r'(?i)zip',
    r'(?i)postal\s*code',
    r'(?i)post\s*code'
]

COUNTRY_PATTERNS = [
    r'(?i)country',
    r'(?i)nation'
]

EDUCATION_PATTERNS = [
    r'(?i)education',
    r'(?i)degree',
    r'(?i)qualification',
    r'(?i)university',
    r'(?i)college',
    r'(?i)school'
]

EXPERIENCE_PATTERNS = [
    r'(?i)experience',
    r'(?i)work\s*history',
    r'(?i)employment',
    r'(?i)job\s*history'
]

SKILLS_PATTERNS = [
    r'(?i)skills',
    r'(?i)abilities',
    r'(?i)competencies',
    r'(?i)qualifications'
]

LINKEDIN_PATTERNS = [
    r'(?i)linkedin',
    r'(?i)linkedin\s*profile',
    r'(?i)linkedin\s*url'
]

GITHUB_PATTERNS = [
    r'(?i)github',
    r'(?i)github\s*profile',
    r'(?i)github\s*url'
]

WEBSITE_PATTERNS = [
    r'(?i)website',
    r'(?i)personal\s*website',
    r'(?i)portfolio',
    r'(?i)blog'
]

COVER_LETTER_PATTERNS = [
    r'(?i)cover\s*letter',
    r'(?i)application\s*letter',
    r'(?i)motivation',
    r'(?i)why\s*do\s*you\s*want\s*to\s*work',
    r'(?i)why\s*are\s*you\s*interested',
    r'(?i)why\s*should\s*we\s*hire\s*you'
]

RESUME_PATTERNS = [
    r'(?i)resume',
    r'(?i)cv',
    r'(?i)curriculum\s*vitae',
    r'(?i)upload\s*resume',
    r'(?i)upload\s*cv'
]

# Pattern to field mapping
FIELD_PATTERNS = {
    'name': NAME_PATTERNS,
    'first_name': FIRST_NAME_PATTERNS,
    'last_name': LAST_NAME_PATTERNS,
    'email': EMAIL_PATTERNS,
    'phone': PHONE_PATTERNS,
    'address': ADDRESS_PATTERNS,
    'city': CITY_PATTERNS,
    'state': STATE_PATTERNS,
    'zip_code': ZIP_PATTERNS,
    'country': COUNTRY_PATTERNS,
    'education': EDUCATION_PATTERNS,
    'experience': EXPERIENCE_PATTERNS,
    'skills': SKILLS_PATTERNS,
    'linkedin_url': LINKEDIN_PATTERNS,
    'github_url': GITHUB_PATTERNS,
    'website': WEBSITE_PATTERNS,
    'cover_letter': COVER_LETTER_PATTERNS,
    'resume': RESUME_PATTERNS
}

# Field priority order (for when multiple patterns match)
FIELD_PRIORITY = [
    'resume',
    'first_name',
    'last_name',
    'name',
    'email',
    'phone',
    'address',
    'city',
    'state',
    'zip_code',
    'country',
    'education',
    'experience',
    'skills',
    'linkedin_url',
    'github_url',
    'website',
    'cover_letter'
]

def map_question_to_field(question: str) -> Optional[str]:
    """
    Map a form question/label to a user profile field
    
    Args:
        question: The question or label text from the form
        
    Returns:
        The mapped field name or None if no mapping found
    """
    if not question:
        return None
        
    matches = []
    
    # Check for matches in our patterns
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, question):
                matches.append(field)
                break
    
    # If multiple matches, use priority order
    if len(matches) > 1:
        for field in FIELD_PRIORITY:
            if field in matches:
                return field
    elif len(matches) == 1:
        return matches[0]
    
    return None
    
def generate_answer(field: str, user_data: Dict[str, str]) -> Optional[str]:
    """
    Generate an answer for a form field based on user data
    
    Args:
        field: The mapped field name
        user_data: Dictionary containing user profile data
        
    Returns:
        The answer string or None if no data available
    """
    if field in user_data and user_data[field]:
        return user_data[field]
    
    # Special handling for combined fields
    if field == 'name' and 'first_name' in user_data and 'last_name' in user_data:
        return f"{user_data['first_name']} {user_data['last_name']}"
    
    # Special handling for address
    if field == 'address' and 'street' in user_data:
        return user_data['street']
        
    return None