from archive.gemini_caller import generate_cover_letter, match_job_description
import unittest

class InstantApplyServiceTest(unittest.TestCase):
    def setUp(self):
        """Set up user data for testing"""
        self.user_data = {
            'name': 'Test User',
            'skills': ['Python', 'AI', 'Machine Learning'],
            'experience': ['Software Engineer at XYZ', 'AI Developer at ABC'],
            'resume': "Experienced Python Developer skilled in AI and automation."
        }

    def test_generate_cover_letter(self):
        job_title = "Software Engineer"
        company = "TestCorp"
        cover_letter = generate_cover_letter(job_title, company, self.user_data)

        self.assertIsInstance(cover_letter, str)
        self.assertIn("Software Engineer", cover_letter)
        self.assertIn("TestCorp", cover_letter)
        self.assertIn("Python", cover_letter)
        self.assertIn("AI", cover_letter)

    def test_match_job_description(self):
        job_description = "Looking for a Software Engineer with expertise in Python, AI, and API Development."
        match_result = match_job_description(job_description, self.user_data)

        self.assertIsInstance(match_result, str)
        self.assertIn("Software Engineer", match_result)
        self.assertIn("Python", match_result)
        self.assertIn("AI", match_result)

if __name__ == '__main__':
    unittest.main()
