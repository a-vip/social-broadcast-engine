import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
import broadcast_engine

class TestBroadcaster(unittest.TestCase):
    def test_clean_text(self):
        html_input = "Hello &amp; welcome to &#8217;AI Governance&#8217; <p>Test</p>"
        cleaned = broadcast_engine.clean_text(html_input)
        self.assertEqual(cleaned, "Hello & welcome to ’AI Governance’ Test")

    def test_format_social_copy(self):
        post = {
            "title": "Switchblade 300 and 600",
            "link": "https://aviperera.com/switchblade-300-600/"
        }
        copy = broadcast_engine.format_social_copy(post)
        self.assertIn("Switchblade 300 and 600", copy)
        self.assertIn("https://aviperera.com/switchblade-300-600/", copy)
        self.assertIn("#AIGovernance", copy)

    @patch("urllib.request.urlopen")
    def test_post_to_webhook(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = broadcast_engine.post_to_webhook(
            webhook_url="https://discord.com/api/webhooks/mock/123",
            title="Test Post",
            link="https://aviperera.com/test/",
            excerpt="Test Excerpt"
        )
        self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
