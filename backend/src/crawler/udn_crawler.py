"""
UDN News Scraper Module

This module provides the UDNCrawler class for fetching, parsing, and saving news articles from the UDN website.
The class extends the NewsCrawlerBase and includes functionalities to search for news articles based on a search term,
parse the details of individual articles, and save them to a database using SQLAlchemy ORM.

Classes:
    UDNCrawler: A class to scrape news from UDN.

Exceptions:
    DomainMismatchException: Raised when the URL domain does not match the expected domain for the crawler.

Usage Example:
    crawler = UDNCrawler(timeout=10)
    headlines = crawler.startup("technology")
    for headline in headlines:
        news = crawler.parse(headline.url)
        crawler.save(news, db_session)

UDNCrawler Methods:
    __init__(self, timeout: int = 5): Initializes the crawler with a default timeout for HTTP requests.
    startup(self, search_term: str) -> list[Headline]: Fetches news headlines for a given search term across multiple pages.
    get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]: Fetches news headlines for specified pages.
    _fetch_news(self, page: int, search_term: str) -> list[Headline]: Helper method to fetch news headlines for a specific page.
    _create_search_params(self, page: int, search_term: str): Creates the parameters for the search request.
    _perform_request(self, params: dict): Performs the HTTP request to fetch news data.
    _parse_headlines(response): Parses the response to extract headlines.
    parse(self, url: str) -> News: Parses a news article from a given URL.
    _extract_news(soup, url: str) -> News: Extracts news details from the BeautifulSoup object.
    save(self, news: News, db: Session): Saves a news article to the database.
    _commit_changes(db: Session): Commits the changes to the database with error handling.
"""

from requests import Response, get
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from urllib.parse import quote
from src.crawler.crawler_base import NewsCrawlerBase, Headline, News, NewsWithSummary
from typing import Union, Tuple, Optional, Dict
from pydantic import AnyHttpUrl
from src.logging_config import logger
from sentry_sdk import capture_exception
from src.crawler.config import DEFAULT_TIMEOUT

class UDNCrawler(NewsCrawlerBase):
    CHANNEL_ID = 2

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.news_website_url = "https://udn.com/api/more"
        self.timeout = timeout

    def startup(self, search_term: str) -> list[Headline]:
        """
        Initializes the application by fetching news headlines for a given search term across multiple pages.
        This method is typically called at the beginning of the program when there is no data available,
        hence it fetches headlines from the first 10 pages.

        :param search_term: The term to search for in news headlines.
        :return: A list of Headline namedtuples containing the title and URL of news articles.
        :rtype: list[Headline]
        """
        return self.get_headline(search_term, page=(1, 10))

    def get_headline(
        self, search_term: str, page: Union[int, Tuple[int, int]]
    ) -> list[Headline]:

        # Calculate the range of pages to fetch news from.
        # If 'page' is a tuple, unpack it and create a range representing those pages (inclusive).
        # If 'page' is an int, create a list containing only that single page number.
        # page_range = range(*page) if isinstance(page, tuple) else [page]
        page_range = (
            range(*page) if isinstance(page, tuple) else [page]
        )
        headlines = []
        for single_page in page_range:
            try:
                headlines.extend(self._fetch_news(single_page, search_term))
            except Exception as err:
                logger.error(f"Error fetching headlines on page {single_page}: {err}", exc_info=True)
                capture_exception(err)
        return headlines

    def _fetch_news(self, page: int, search_term: str) -> list[Headline]:
        try:
            params = self._create_search_params(page, search_term)
            response = self._perform_request(params=params)
            return self._parse_headlines(response)
        except Exception as err:
            logger.error(f"Error in _fetch_news: {err}", exc_info=True)
            capture_exception(err)
            raise
    def _create_search_params(self, page: int, search_term: str) -> dict:
        return {
            "page": page,
            "id": f"search:{quote(search_term)}",
            "channelId": self.CHANNEL_ID,
            "type": "searchword",
        }

    def _perform_request(self, url: Optional[str] = None, params: Optional[Dict] = None) -> Response:
        try:
            response = get(self.news_website_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response
        except Exception as err:
            logger.error(f"Failed to perform request: {err}", exc_info=True)
            capture_exception(err)
            raise ConnectionError(f"Failed to fetch data: {err}")


    @staticmethod
    def _parse_headlines(response: Response) -> list[Headline]:
        try:
            data = response.json()
            if "lists" not in data:
                return []
            return [
                Headline(title=item["title"], url=item["titleLink"])
                for item in data["lists"]
            ]
        except Exception as err:
            logger.error(f"Error parsing headlines: {err}", exc_info=True)
            capture_exception(err)
            raise

    def parse(self, url: Union[AnyHttpUrl, str]) -> News:
        try:
            response = self._perform_request(params=None, url=url)
            soup = BeautifulSoup(response.content, "html.parser")
            return self._extract_news(soup, url)
        except Exception as err:
            logger.error(f"Error parsing article at {url}: {err}", exc_info=True)
            capture_exception(err)
            raise

    @staticmethod
    def _extract_news(soup: BeautifulSoup, url: str) -> News:
        try:
            title = soup.find("h1", class_="article-content__title").text.strip()
        except AttributeError as err:
            logger.error(f"Error extracting title: {err}", exc_info=True)
            capture_exception(err)
            raise

        try:
            time = soup.find("time", class_="article-content__time").text.strip()
        except AttributeError as err:
            logger.error(f"Error extracting time: {err}", exc_info=True)
            capture_exception(err)
            raise

        try:
            content_section = soup.find("section", class_="article-content__editor")
            paragraphs = [
                p.text.strip()
                for p in content_section.find_all("p")
                if p.text.strip() and "▪" not in p.text
            ]
        except AttributeError as err:
            logger.error(f"Error extracting content: {err}", exc_info=True)
            capture_exception(err)
            raise

        return News(
            title=title,
            url=url,
            time=time,
            content="\n".join(paragraphs),
        )

    def save(self, news: NewsWithSummary, db: Session):
        try:
            db.add(news)
            self._commit_changes(db)
        except Exception as err:
            logger.error(f"Error saving news: {err}", exc_info=True)
            capture_exception(err)
            raise

    @staticmethod
    def _commit_changes(db: Session):
        try:
            db.commit()
        except Exception as err:
            db.rollback()
            logger.error(f"Failed to commit database changes: {err}", exc_info=True)
            capture_exception(err)
            raise RuntimeError(f"Failed to save data: {err}")