import unittest
from unittest.mock import MagicMock
import sys
import os
from app import create_app

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import the module to test
from application_filler.services import user_service

class TestUserService(unittest.TestCase):
    """Tests for the user_service functions"""

    def setUp(self):
        self.test_user = MagicMock(
            id=1,
            name="Test User",
            email="test@example.com",
            resume_file_path="/path/to/resume.pdf",
            skills='["Python", "JavaScript"]',
            experience="3 years in software development"
        )
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def test_get_user_profile_dict_success(self):
        """Test retrieving a user profile by ID"""
        mock_get = MagicMock(return_value=self.test_user)
        user_service.User.query.get = mock_get

        profile = user_service.get_user_profile_dict(user_id=1)

        mock_get.assert_called_once_with(1)
        self.assertEqual(profile["id"], 1)
        self.assertEqual(profile["name"], "Test User")
        self.assertEqual(profile["email"], "test@example.com")

    def test_get_user_profile_dict_user_not_found(self):
        """Test get_user_profile_dict when user not found"""
        mock_get = MagicMock(return_value=None)
        user_service.User.query.get = mock_get
        profile = user_service.get_user_profile_dict(user_id=999)
        self.assertEqual(profile, {})

    def test_get_user_email_success(self):
        """Test get_user_email for a valid user"""
        mock_get = MagicMock(return_value=self.test_user)
        user_service.User.query.get = mock_get
        email = user_service.get_user_email(user_id=1)
        self.assertEqual(email, "test@example.com")

    def test_get_user_email_user_not_found(self):
        """Test get_user_email when user is missing"""
        mock_get = MagicMock(return_value=None)
        user_service.User.query.get = mock_get
        email = user_service.get_user_email(user_id=999)
        self.assertEqual(email, "")

if __name__ == '__main__':
    unittest.main()
