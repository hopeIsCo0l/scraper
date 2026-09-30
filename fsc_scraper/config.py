"""
FSC Scraper Configuration
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

BASE_URL = "https://www.fsc.gov.et"

# Pre-configured sections known to contain documents and legal decisions
SECTIONS: Dict[str, dict] = {
    # High-priority legal publications & court volumes
    "supreme-court": {
        "name": "Supreme Court Decisions (Volumes)",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Judgments/Supreme-Court-Decisions",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Judgments/Supreme-Court-Decisions/PgrID/1211/PageID/{{page}}",
        "description": "Supreme Court Decision volumes (e.g., Volume 1 to 14)",
    },
    "cassation-series": {
        "name": "Federal Cassation Decision Series",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Publications/Federal-Cassation-Decision-Series",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Publications/Federal-Cassation-Decision-Series/PgrID/1026/PageID/{{page}}",
        "description": "Full Cassation Decision Series volumes (e.g., Volume 1 to 28+)",
    },
    "federal-laws": {
        "name": "Federal Laws",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Federal-Laws",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Federal-Laws/PgrID/1179/PageID/{{page}}",
        "description": "Federal Laws, Proclamations, Regulations, Directives",
    },
    "annual-reports": {
        "name": "Annual Reports",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Annual-Reports",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Annual-Reports/PgrID/888/PageID/{{page}}",
        "description": "Federal Supreme Court annual reports",
    },
    "newsletter": {
        "name": "Newsletters",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Publications/Newsletter",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Publications/Newsletter/PgrID/1036/PageID/{{page}}",
        "description": "Quarterly and special newsletters",
    },
    "tenders": {
        "name": "Tenders & Bidding Documents",
        "start_url": f"{BASE_URL}/Tender",
        "pager_pattern": f"{BASE_URL}/Tender/PgrID/1409/PageID/{{page}}",
        "description": "Procurement and standard bidding documents",
    },
    "vacancies": {
        "name": "Vacancies & Announcements",
        "start_url": f"{BASE_URL}/Vacancy",
        "pager_pattern": f"{BASE_URL}/Vacancy/PgrID/1386/PageID/{{page}}",
        "description": "Job vacancies and official application criteria",
    },
    "auctions": {
        "name": "Auctions (Judgement Execution)",
        "start_url": f"{BASE_URL}/Judgement-Execution-Directorate/Auction",
        "pager_pattern": f"{BASE_URL}/Judgement-Execution-Directorate/Auction/PgrID/1347/PageID/{{page}}",
        "description": "Judgement execution auction announcements",
    },
    "archives": {
        "name": "Archives",
        "start_url": f"{BASE_URL}/Digital-Law-Library/Archives",
        "pager_pattern": f"{BASE_URL}/Digital-Law-Library/Archives/PgrID/1027/PageID/{{page}}",
        "description": "Archived legal documents",
    },
    # The massive database of individual Cassation Decisions (680+ pages)
    "cassation-decisions": {
        "name": "Cassation Decisions (Comprehensive)",
        "start_url": f"{BASE_URL}/Home/PgrID/538/PageID/1",
        "pager_pattern": f"{BASE_URL}/Home/PgrID/538/PageID/{{page}}",
        "description": "Complete database of individual Cassation Court judgments (~2,700 cases)",
    },
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF = 1.5
DEFAULT_REQUEST_DELAY = 0.4
DEFAULT_DOWNLOAD_DIR = Path("./downloads")
