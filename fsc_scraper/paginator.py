"""
Pagination handler for FSC EasyDNNNews listing pages
"""
import logging
import re
from typing import Iterator, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

from .config import DEFAULT_TIMEOUT

logger = logging.getLogger("fsc_scraper.paginator")


def extract_pager_info(soup: BeautifulSoup) -> Tuple[Optional[str], int]:
    """
    Examines an EasyDNNNews HTML page to discover the pagination pattern
    and the total number of pages.
    
    Returns:
        (pager_pattern_template, max_page_number)
    """
    pager_links = soup.find_all("a", href=lambda h: h and "PageID/" in h)
    if not pager_links:
        return None, 1
    
    max_page = 1
    sample_url = None
    
    for a in pager_links:
        href = a["href"]
        text = a.get_text(strip=True).lower()
        match = re.search(r"PageID/(\d+)", href)
        if match:
            p_num = int(match.group(1))
            if text == "last":
                max_page = max(max_page, p_num)
                sample_url = href
            else:
                max_page = max(max_page, p_num)
                if not sample_url:
                    sample_url = href
                    
    pattern = None
    if sample_url:
        pattern = re.sub(r"PageID/\d+", "PageID/{page}", sample_url)
        
    return pattern, max_page


def generate_page_urls(
    session: requests.Session,
    start_url: str,
    pager_pattern: Optional[str] = None,
    max_pages: Optional[int] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Iterator[Tuple[int, str, BeautifulSoup]]:
    """
    Discovers total pages and yields (page_number, page_url, parsed_soup).
    
    If pager_pattern is not pre-configured, it discovers it from start_url.
    Respects max_pages if user limits pagination.
    """
    logger.info(f"Fetching initial listing page: {start_url}")
    resp = session.get(start_url, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Discover pattern and max_page if not provided
    disc_pattern, disc_max = extract_pager_info(soup)
    effective_pattern = pager_pattern or disc_pattern
    total_pages = disc_max
    
    if max_pages and max_pages > 0:
        total_pages = min(total_pages, max_pages)
        
    logger.info(f"Discovered total pages: {disc_max} (will crawl: {total_pages})")
    
    # Yield the first page (already fetched)
    yield (1, start_url, soup)
    
    if total_pages <= 1 or not effective_pattern:
        return
        
    # Fetch subsequent pages
    for page_num in range(2, total_pages + 1):
        page_url = effective_pattern.format(page=page_num)
        page_url = urljoin(start_url, page_url)
        try:
            logger.debug(f"Fetching listing page {page_num}/{total_pages}: {page_url}")
            p_resp = session.get(page_url, timeout=timeout)
            p_resp.raise_for_status()
            p_soup = BeautifulSoup(p_resp.text, "lxml")
            yield (page_num, page_url, p_soup)
        except Exception as e:
            logger.error(f"Failed to fetch listing page {page_num} ({page_url}): {e}")
            continue
