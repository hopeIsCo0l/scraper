"""
Federal Supreme Court of Ethiopia (FSC) PDF Document Scraper & Crawler
"""
from .config import BASE_URL, SECTIONS
from .crawler import FSCCrawler
from .downloader import download_pdf
from .extractor import extract_article_links, extract_document_links
from .manifest import Manifest
from .paginator import generate_page_urls
from .session import create_session

__all__ = [
    "FSCCrawler",
    "create_session",
    "Manifest",
    "download_pdf",
    "extract_article_links",
    "extract_document_links",
    "generate_page_urls",
    "BASE_URL",
    "SECTIONS",
]
