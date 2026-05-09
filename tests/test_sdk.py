import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path to import hiresquire
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hiresquire import HireSquire, HireSquireError

class TestHireSquireSDK(unittest.TestCase):
    def setUp(self):
        self.api_token = "test_token"
        self.client = HireSquire(api_token=self.api_token)

    def test_init_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HireSquireError):
                HireSquire()

    def test_init_with_env_token(self):
        with patch.dict(os.environ, {"HIRESQUIRE_API_TOKEN": "env_token"}):
            client = HireSquire()
            self.assertEqual(client.api_token, "env_token")

    @patch('hiresquire.whoami')
    def test_whoami(self, mock_whoami):
        mock_whoami.return_value = {"valid": True, "user": {"name": "Test"}}
        result = self.client.whoami()
        self.assertTrue(result["valid"])
        mock_whoami.assert_called_once_with(api_token=self.api_token, base_url=self.client.base_url)

    @patch('hiresquire.create_screening_job')
    def test_jobs_create(self, mock_create):
        mock_create.return_value = {"job_id": 123}
        resumes = [{"filename": "test.pdf", "content": "base64data"}]
        result = self.client.jobs.create("Title", "Desc", resumes)
        self.assertEqual(result["job_id"], 123)
        mock_create.assert_called_once()

    @patch('hiresquire.get_credit_balance')
    def test_credits_balance(self, mock_balance):
        mock_balance.return_value = {"balance": 100.0}
        result = self.client.credits.get_balance()
        self.assertEqual(result["balance"], 100.0)
        mock_balance.assert_called_once()

    @patch('hiresquire.create_calendar_connection')
    def test_calendar_connect(self, mock_connect):
        mock_connect.return_value = {"success": True}
        result = self.client.calendar.connect("calendly", "key123")
        self.assertTrue(result["success"])
        mock_connect.assert_called_once_with(
            "calendly", "key123", None, 
            api_token=self.api_token, 
            base_url=self.client.base_url
        )

if __name__ == '__main__':
    unittest.main()
