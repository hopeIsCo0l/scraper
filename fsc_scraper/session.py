"""
HTTP Session Management with automatic retries and error handling
"""
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

from .config import DEFAULT_USER_AGENT, DEFAULT_TIMEOUT, DEFAULT_RETRY_COUNT, DEFAULT_RETRY_BACKOFF

# Suppress insecure SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("fsc_scraper.session")


def create_session(
    user_agent: str = DEFAULT_USER_AGENT,
    retries: int = DEFAULT_RETRY_COUNT,
    backoff_factor: float = DEFAULT_RETRY_BACKOFF,
    verify_ssl: bool = False,
) -> requests.Session:
    """
    Creates and configures a requests.Session with retry logic and standard headers.
    """
    session = requests.Session()
    
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,am;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.verify = verify_ssl
    
    return session
