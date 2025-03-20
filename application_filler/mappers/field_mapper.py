import re
def map_question_to_field(question_text: str) -> str:
    """
    Map application question text to a user profile field.
    """
    q = question_text.lower()

    if any(phrase in q for phrase in ["greatest strength", "biggest strength", "key strength", "your strength", "top strength"]):
        return "biggest_achievement"
    elif any(phrase in q for phrase in ["career goal", "career ambition", "long-term goal", "short-term goal", "where do you see yourself"]):
        return "career_goals"
    elif any(phrase in q for phrase in ["experience", "work history", "previous roles", "professional background", "your background"]):
        return "experience"
    elif any(phrase in q for phrase in ["skills", "core competencies", "technical skills", "expertise", "areas of expertise"]):
        return "skills"
    elif any(phrase in q for phrase in ["visa sponsorship", "authorization", "sponsorship", "work authorization", "require sponsorship"]):
        return "authorization_status"
    elif any(phrase in q for phrase in ["relocate", "willing to move", "open to relocation", "consider relocation", "change location"]):
        return "willing_to_relocate"
    elif any(phrase in q for phrase in ["start date", "availability date", "when can you start", "available to start", "available start date"]):
        return "available_start_date"
    elif any(phrase in q for phrase in ["github", "portfolio", "personal site", "personal website", "online portfolio"]):
        return "portfolio_links"
    elif any(phrase in q for phrase in ["certifications", "licenses", "certification", "credentials", "accreditations"]):
        return "certifications"
    elif any(phrase in q for phrase in ["languages", "language proficiency", "what languages", "spoken languages", "which languages"]):
        return "languages"
    else:
        return "career_goals"