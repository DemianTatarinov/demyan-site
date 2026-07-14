import unittest
from unittest.mock import MagicMock, patch
import importlib
import os

class TestTelegramBotImports(unittest.TestCase):
    def test_imports_and_regex(self):
        # Dynamically import main to see if syntax and structural dependencies are valid
        try:
            import main
        except ImportError as e:
            self.fail(f"Failed to import main.py: {e}")

        # Test LINK_PATTERN matches correct URLs
        link_pattern = main.LINK_PATTERN

        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/shorts/tPEE9ZwTmy0?feature=share",
            "https://youtu.be/tPEE9ZwTmy0",
            "https://www.instagram.com/reel/C89abcdefgh/",
            "https://instagram.com/p/C89abcdefgh/",
            "https://www.instagram.com/reels/C89abcdefgh/",
            "http://instagram.com/tv/C89abcdefgh/"
        ]

        invalid_urls = [
            "https://google.com",
            "https://github.com",
            "not_a_link"
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                match = link_pattern.search(url)
                self.assertIsNotNone(match, f"Should match valid URL: {url}")
                self.assertEqual(match.group(1), url)

        for url in invalid_urls:
            with self.subTest(url=url):
                match = link_pattern.search(url)
                self.assertIsNone(match, f"Should NOT match invalid URL: {url}")

if __name__ == '__main__':
    unittest.main()
