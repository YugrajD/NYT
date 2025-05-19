import unittest
from unittest.mock import patch, MagicMock
import os

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        """Set up the test client and mock MongoDB."""
        os.environ['NYT_API_KEY'] = 'test-key'

        # Mock MongoClient
        self.mongo_patch = patch('pymongo.MongoClient', autospec=True)
        self.mock_mongo_client = self.mongo_patch.start()
        # Sets up a mock database and collection
        self.mock_db = MagicMock()
        self.mock_comments = MagicMock()
        self.mock_db.comments = self.mock_comments
        self.mock_mongo_client.return_value.get_database.return_value = self.mock_db
        # then import the app after the mock is done 
        from app import app
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up after each test."""
        self.mongo_patch.stop()
        os.environ.pop('NYT_API_KEY', None)

    def test_comments_get(self):
        """Test retrieving comments."""
        self.mock_comments.find.return_value = [{'_id': 'abc123', 'url': 'http://example.com/1', 'text': 'Test comment'}]
        response = self.client.get('/api/comments?url=http://example.com/1')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 0)  

    def test_comments_post(self):
        """Test posting a comment."""
        self.mock_comments.insert_one.return_value = MagicMock(inserted_id='abc123')

        comment_data = {'url': 'http://example.com/1', 'text': 'New comment'}
        response = self.client.post('/api/comments', json=comment_data, headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})
        self.assertFalse(self.mock_comments.insert_one.called)  

    def test_comments_delete(self):
        """Test deleting a comment as a moderator."""
        self.mock_comments.update_one.return_value = MagicMock(matched_count=1)
        with self.client.session_transaction() as sess:
            sess['user'] = {'email': 'moderator@hw3.com'}
        response = self.client.delete('/api/comments/123456789012345678901234')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'soft-deleted', 'id': '123456789012345678901234'})

        self.mock_comments.update_one.assert_called_once()

if __name__ == '__main__':
    unittest.main()