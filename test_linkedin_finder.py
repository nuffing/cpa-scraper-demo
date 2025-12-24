import unittest
from unittest.mock import patch, Mock
import pandas as pd
from linkedin_finder import search_cpa_profiles

class TestLinkedInFinder(unittest.TestCase):

    def setUp(self):
        # Set dummy API key for tests
        self.patcher = patch.dict('os.environ', {'SERPER_API_KEY': 'dummy_key'})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('linkedin_finder.requests.post')
    def test_google_search_logic(self, mock_post):
        """
        Req 1: Verify the Google search query is constructed correctly.
        """
        # Setup mock response (empty organic results is fine for this test)
        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_data = [{"name": "John Doe", "state": "Maine"}]
        search_cpa_profiles(input_data)

        # Check if the query in the payload matches the required format
        # "Name" "CPA" "state" "United States" LinkedIn
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        expected_query = '"John Doe" "CPA" "Maine" "United States" LinkedIn'
        self.assertEqual(payload['q'], expected_query)

    @patch('linkedin_finder.requests.post')
    def test_url_filtering_accept_reject(self, mock_post):
        """
        Req 3: 
        - Accept only linkedin.com/in/...
        - Reject linkedin.com/company/, /jobs/, etc.
        """
        mock_response = Mock()
        mock_response.json.return_value = {
            "organic": [
                {"link": "https://www.linkedin.com/in/johndoe", "title": "John Doe", "snippet": "CPA"},  # Valid
                {"link": "https://www.linkedin.com/company/doe-cpa", "title": "Doe CPA Firm", "snippet": "Firm"}, # Invalid
                {"link": "https://www.linkedin.com/jobs/view/123", "title": "Job", "snippet": "Job"}, # Invalid
                {"link": "https://www.linkedin.com/in/janesmith", "title": "Jane Smith", "snippet": "CPA"} # Valid
            ]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_data = [{"name": "Test", "state": "Test"}]
        df = search_cpa_profiles(input_data)

        # We expect 2 valid profiles
        self.assertEqual(len(df), 2)
        self.assertTrue("johndoe" in df.iloc[0]['linkedin_url'])
        self.assertTrue("janesmith" in df.iloc[1]['linkedin_url'])
        # Ensure 'company' did not sneak in
        self.assertFalse(df['linkedin_url'].str.contains('company').any())

    @patch('linkedin_finder.requests.post')
    def test_url_normalization(self, mock_post):
        """
        Req 3: URL Normalization - Remove tracking/query parameters.
        """
        mock_response = Mock()
        # URL with tracking parameters
        dirty_url = "https://www.linkedin.com/in/johndoe?originalSubdomain=uk&trackingId=123"
        
        mock_response.json.return_value = {
            "organic": [
                {"link": dirty_url, "title": "John", "snippet": "Desc"}
            ]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_data = [{"name": "Test", "state": "Test"}]
        df = search_cpa_profiles(input_data)

        expected_clean_url = "https://www.linkedin.com/in/johndoe"
        self.assertEqual(df.iloc[0]['linkedin_url'], expected_clean_url)

    @patch('linkedin_finder.requests.post')
    def test_volume_deduplication(self, mock_post):
        """
        Req 5: Deduplicate results using the normalized LinkedIn URL.
        """
        mock_response = Mock()
        # Same profile appearing twice in search results (perhaps with diff params)
        mock_response.json.return_value = {
            "organic": [
                {"link": "https://www.linkedin.com/in/duplicate?id=1", "title": "Dup 1", "snippet": "Desc"},
                {"link": "https://www.linkedin.com/in/duplicate?id=2", "title": "Dup 1", "snippet": "Desc"} 
            ]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_data = [{"name": "Test", "state": "Test"}]
        df = search_cpa_profiles(input_data)

        # Should only be 1 row, not 2
        self.assertEqual(len(df), 1)

    @patch('linkedin_finder.requests.post')
    def test_error_handling_missing_meta(self, mock_post):
        """
        Req 6: If meta data cannot be fetched -> keep URL + rank, leave meta fields blank.
        """
        mock_response = Mock()
        # Result missing 'snippet' (description)
        mock_response.json.return_value = {
            "organic": [
                {"link": "https://www.linkedin.com/in/ghost", "title": "Ghost User"} 
                # Note: 'snippet' key is missing entirely
            ]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_data = [{"name": "Test", "state": "Test"}]
        df = search_cpa_profiles(input_data)

        self.assertEqual(df.iloc[0]['linkedin_url'], "https://www.linkedin.com/in/ghost")
        self.assertEqual(df.iloc[0]['meta_description'], "") # Should default to empty string, not error

if __name__ == '__main__':
    unittest.main()
