import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from app import create_app

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import target module
from application_filler.services import job_service

class TestJobService(unittest.TestCase):
    """Unit tests for job_service functions"""

    def setUp(self):
        self.user = MagicMock(id=1, email="test@example.com")
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.mock_jobs = [
            MagicMock(id=1, user_id=1, job_title="Engineer", match_score=85, url="http://job1.com"),
            MagicMock(id=2, user_id=1, job_title="Scientist", match_score=75, url="http://job2.com"),
            MagicMock(id=3, user_id=1, job_title="Manager", match_score=60, url="http://job3.com"),
        ]

    def tearDown(self):
        self.app_context.pop()

    @patch('models.job_recommendation.JobRecommendation.query')
    def test_get_job_recommendations_for_user(self, mock_query):
        """Test job recommendations retrieval with min_score filtering"""
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = self.mock_jobs

        jobs = job_service.get_job_recommendations_for_user(self.user, min_score=70)
        self.assertEqual(len(jobs), 3)
        mock_query.filter_by.assert_called_with(user_id=self.user.id)
        mock_query.filter.assert_called()

    @patch('models.job_recommendation.JobRecommendation.query')
    def test_get_job_links_for_user(self, mock_query):
        """Test extracting job links from recommended jobs"""
        mock_query.filter_by.return_value = mock_query
        mock_query.all.return_value = self.mock_jobs

        urls = job_service.get_job_links_for_user(self.user, min_score=0)
        self.assertEqual(len(urls), 3)
        self.assertIn("http://job1.com", urls)
        self.assertIn("http://job2.com", urls)

    @patch('models.user.User.query')
    def test_get_user_by_id(self, mock_user_query):
        """Test retrieving user by ID"""
        mock_user_query.get.return_value = self.user
        user = job_service.get_user_by_id(1)
        self.assertEqual(user, self.user)
        mock_user_query.get.assert_called_with(1)

if __name__ == '__main__':
    unittest.main()
