import unittest
from unittest.mock import patch, MagicMock
from requests.models import Response
from src.crawler.udn_crawler import UDNCrawler


class TestUDNCrawler(unittest.TestCase):

    def setUp(self):
        self.scraper = UDNCrawler(timeout=5)

    @patch("src.crawler.udn_crawler.UDNCrawler._perform_request")
    def test_fetch_news_data(self, mock_perform_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [{"title": "Test News", "titleLink": "https://udn.com/news/test-news"}]
        }
        mock_perform_request.return_value = mock_response

        headlines = self.scraper._fetch_news(page=1, search_term="technology")
        self.assertEqual(len(headlines), 1)
        self.assertEqual(headlines[0].title, "Test News")
        self.assertEqual(headlines[0].url, "https://udn.com/news/test-news")

    @patch("src.crawler.udn_crawler.UDNCrawler._perform_request")
    def test_parse_invalid_domain(self, mock_perform_request):
        mock_perform_request.side_effect = ConnectionError("Failed to fetch data: 404 Client Error")
        with self.assertRaises(ConnectionError):
            self.scraper.parse("https://udn.com/news/e404?miscinit")

    @patch("src.crawler.udn_crawler.UDNCrawler._perform_request")
    def test_parse_news(self, mock_perform_request):
        mock_response = MagicMock()
        mock_response.content = """
            <html>
                <h1 class="article-content__title">Test Title</h1>
                <time class="article-content__time">2023-09-08T00:00:00</time>
                <section class="article-content__editor">
                    <p>Content paragraph 1.</p>
                    <p>Content paragraph 2.</p>
                </section>
            </html>
        """
        mock_perform_request.return_value = mock_response

        news = self.scraper.parse("https://udn.com/news/test-news")
        self.assertEqual(news.title, "Test Title")
        self.assertEqual(news.time, "2023-09-08T00:00:00")
        self.assertEqual(news.content, "Content paragraph 1.\nContent paragraph 2.")

if __name__ == "__main__":
    unittest.main()
