"""
Crawler Orchestrator
Coordinates listing discovery, article parsing, PDF extraction, deduplication, and downloading.
"""
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests

from .config import BASE_URL, DEFAULT_DOWNLOAD_DIR, DEFAULT_REQUEST_DELAY, DEFAULT_TIMEOUT, SECTIONS
from .downloader import download_pdf
from .extractor import extract_article_links, extract_document_links
from .manifest import Manifest
from .paginator import generate_page_urls
from .session import create_session

logger = logging.getLogger("fsc_scraper.crawler")


class FSCCrawler:
    """
    Crawler for Federal Supreme Court of Ethiopia documents and legal decisions.
    """

    def __init__(
        self,
        output_dir: Path = DEFAULT_DOWNLOAD_DIR,
        delay: float = DEFAULT_REQUEST_DELAY,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
        dry_run: bool = False,
        limit: Optional[int] = None,
        max_pages: Optional[int] = None,
    ):
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.timeout = timeout
        self.session = session or create_session()
        self.dry_run = dry_run
        self.limit = limit
        self.max_pages = max_pages
        
        self.manifest = Manifest(self.output_dir)
        
        # Runtime stats
        self.stats = {
            "listing_pages_crawled": 0,
            "articles_visited": 0,
            "pdfs_discovered": 0,
            "pdfs_downloaded": 0,
            "pdfs_skipped": 0,
            "pdfs_failed": 0,
        }

    def _sleep(self):
        """Politeness delay between network requests."""
        if self.delay > 0:
            time.sleep(self.delay)

    def crawl_section(self, section_key: str, section_cfg: dict):
        """
        Crawls a single document section across all its paginated listing pages.
        """
        section_name = section_cfg.get("name", section_key)
        start_url = section_cfg.get("start_url")
        pager_pattern = section_cfg.get("pager_pattern")
        
        logger.info(f"\n{'='*70}\nStarting Section: [{section_name}]\nURL: {start_url}\n{'='*70}")
        
        # Subdirectory per section for clean organization
        section_dir = self.output_dir / section_key
        
        pages_generator = generate_page_urls(
            session=self.session,
            start_url=start_url,
            pager_pattern=pager_pattern,
            max_pages=self.max_pages,
            timeout=self.timeout,
        )
        
        for page_num, page_url, soup in pages_generator:
            self.stats["listing_pages_crawled"] += 1
            logger.info(f"--- Processing [{section_key}] Page {page_num} ({page_url}) ---")
            
            # 1. Extract articles on this listing page
            articles = extract_article_links(soup, page_url)
            logger.info(f"Found {len(articles)} article links on page {page_num}")
            
            # Also check if this listing page itself has direct document links
            direct_docs = extract_document_links(soup, page_url)
            if direct_docs:
                logger.info(f"Found {len(direct_docs)} direct document links on listing page")
                for doc in direct_docs:
                    self._process_document(doc, section_key, section_dir)
                    if self._limit_reached():
                        logger.info(f"Download limit reached ({self.limit}). Stopping.")
                        return

            # 2. Visit each article to find attached documents
            for art in articles:
                if self._limit_reached():
                    logger.info(f"Download limit reached ({self.limit}). Stopping.")
                    return
                    
                art_url = art["url"]
                art_title = art["title"]
                self.stats["articles_visited"] += 1
                
                self._sleep()
                try:
                    logger.debug(f"Fetching article: {art_title[:40]} -> {art_url}")
                    art_resp = self.session.get(art_url, timeout=self.timeout)
                    if art_resp.status_code == 404:
                        logger.warning(f"Article returned 404: {art_url}")
                        continue
                    art_resp.raise_for_status()
                    
                    from bs4 import BeautifulSoup
                    art_soup = BeautifulSoup(art_resp.text, "lxml")
                    
                    # Extract PDFs in this article
                    docs = extract_document_links(art_soup, art_url)
                    if docs:
                        logger.info(f"Found {len(docs)} PDF(s) in: '{art_title[:50]}'")
                    else:
                        logger.debug(f"No PDFs attached in article: {art_url}")
                        
                    for doc in docs:
                        # Carry over article title if not set
                        if not doc.get("article_title"):
                            doc["article_title"] = art_title
                        self._process_document(doc, section_key, section_dir)
                        if self._limit_reached():
                            logger.info(f"Download limit reached ({self.limit}). Stopping.")
                            return

                except Exception as e:
                    logger.error(f"Error reading article ({art_url}): {e}")
                    continue

    def _process_document(self, doc_info: dict, section_key: str, section_dir: Path):
        """
        Handles discovery, deduplication, and downloading of an extracted PDF.
        """
        self.stats["pdfs_discovered"] += 1
        download_url = doc_info["download_url"]
        
        # Check if already downloaded
        if self.manifest.is_already_downloaded(doc_info):
            self.stats["pdfs_skipped"] += 1
            logger.info(f"Skipping duplicate/already downloaded: {download_url}")
            return
            
        if self.dry_run:
            logger.info(f"[DRY RUN] Discovered PDF: {download_url} (Article: {doc_info.get('article_title', '')[:40]})")
            return
            
        # Download document
        self._sleep()
        success, filename, file_size, err = download_pdf(
            session=self.session,
            doc_info=doc_info,
            destination_dir=section_dir,
            timeout=self.timeout,
            show_progress=True,
        )
        
        if success:
            self.stats["pdfs_downloaded"] += 1
            rel_path = f"{section_key}/{filename}"
            self.manifest.record_success(
                doc_info=doc_info,
                filename=filename,
                relative_path=rel_path,
                file_size_bytes=file_size,
                section_name=section_key,
            )
            print(
                f"[{self.stats['pdfs_downloaded']} DL | {self.stats['pdfs_skipped']} Skip | "
                f"{self.stats['pdfs_failed']} Fail] -> {filename} ({file_size:,} bytes)"
            )
        else:
            self.stats["pdfs_failed"] += 1
            self.manifest.record_failure(
                doc_info=doc_info,
                error_msg=err or "Unknown error",
                section_name=section_key,
            )
            logger.error(f"Failed to download {download_url}: {err}")

    def _limit_reached(self) -> bool:
        """Checks if configured download limit has been satisfied."""
        if self.limit and self.stats["pdfs_downloaded"] >= self.limit:
            return True
        return False

    def run(self, section_name: str = "all") -> Dict[str, int]:
        """
        Runs the crawler for a specific section or all known sections.
        """
        start_time = time.time()
        logger.info(f"FSC Scraper started (dry_run={self.dry_run}, limit={self.limit}, max_pages={self.max_pages})")
        
        if section_name == "all":
            target_sections = list(SECTIONS.items())
        elif section_name in SECTIONS:
            target_sections = [(section_name, SECTIONS[section_name])]
        else:
            raise ValueError(f"Unknown section '{section_name}'. Available: {list(SECTIONS.keys()) + ['all']}")
            
        for sec_key, sec_cfg in target_sections:
            if self._limit_reached():
                break
            self.crawl_section(sec_key, sec_cfg)
            
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}\nCRAWL COMPLETE in {elapsed:.1f}s\n{'='*70}")
        logger.info(f"Listing Pages Crawled: {self.stats['listing_pages_crawled']}")
        logger.info(f"Articles Visited:      {self.stats['articles_visited']}")
        logger.info(f"PDFs Discovered:       {self.stats['pdfs_discovered']}")
        logger.info(f"PDFs Downloaded:       {self.stats['pdfs_downloaded']}")
        logger.info(f"PDFs Skipped (Dupes):  {self.stats['pdfs_skipped']}")
        logger.info(f"PDFs Failed:           {self.stats['pdfs_failed']}")
        logger.info(f"Manifest written to:   {self.manifest.json_path}")
        logger.info(f"CSV index written to:  {self.manifest.csv_path}")
        
        return self.stats
