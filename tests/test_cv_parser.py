import pytest
from utils.document_parser import parse_resume_with_spacy
import sys
print("PYTHON:", sys.executable)

@pytest.fixture
def sample_resume_text():
    return """
    John Doe
    LinkedIn: https://linkedin.com/in/johndoe
    Summary: Experienced Software Engineer with expertise in Python, Flask, and Docker.
    Skills: Python, Flask, Docker, SQL, Agile
    Work Experience: 
    Software Engineer at TechCorp (2018-2021)
    Certifications: AWS Certified Solutions Architect
    Languages: English, Spanish
    Career goals: To lead backend engineering teams and build scalable systems.
    Biggest Achievement: Migrated legacy systems to microservices, improving performance by 30%.
    Work Style: Independent but highly collaborative
    Industry attraction: Passionate about the impact of AI on healthcare.
    Education: Bachelor of Science in Computer Science, ABC University, 2017
    """

def test_parse_resume_with_spacy(sample_resume_text):
    parsed = parse_resume_with_spacy(sample_resume_text)
    
    assert parsed['name'] == "John Doe"
    assert parsed['linkedin'] == "https://linkedin.com/in/johndoe"
    assert "Python" in parsed['skills']
    assert any("Software Engineer at TechCorp" in exp for exp in parsed['experience'])    
    assert any("AWS Certified Solutions Architect" in cert for cert in parsed['certifications'])
    assert "English" in parsed['languages']
    assert "Spanish" in parsed['languages']
    assert "Experienced Software Engineer" in parsed['professional_summary']
    assert "To lead backend engineering teams" in parsed['career_goals']
    assert "Migrated legacy systems" in parsed['biggest_achievement']
    assert "Independent but highly collaborative" in parsed['work_style']
    assert "impact of AI on healthcare" in parsed['industry_attraction']
    assert any("Bachelor" in edu for edu in parsed['education'])