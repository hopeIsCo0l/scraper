#!/usr/bin/env python3
"""
Federal Supreme Court of Ethiopia (FSC) PDF Document Scraper & Crawler
CLI Entry Point
"""
import argparse
import logging
import sys
from pathlib import Path

from fsc_scraper.config import DEFAULT_DOWNLOAD_DIR, DEFAULT_REQUEST_DELAY, SECTIONS
from fsc_scraper.crawler import FSCCrawler


def setup_logging(verbose: bool = False):
    """Configures console and file logging."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=log_format, datefmt="%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(
        description="FSC Ethiopia PDF Document Scraper & Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test run: crawl discovery only without downloading
  python run_scraper.py --dry-run --section supreme-court

  # Test run: download only 5 PDFs from Cassation Decision Series
  python run_scraper.py --section cassation-series --limit 5

  # Download all Supreme Court Decision volumes
  python run_scraper.py --section supreme-court

  # List all available sections
  python run_scraper.py --list-sections

  # Full download of all sections with polite delay
  python run_scraper.py --section all --delay 0.5
        """,
    )
    
    parser.add_argument(
        "--section",
        default="supreme-court",
        help="Section to crawl. Choose from available sections or 'all' (default: supreme-court)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after downloading this many PDFs (recommended for initial tests)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum listing pages to crawl per section",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover pages and PDF links only; do not download files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"Destination directory for downloads (default: {DEFAULT_DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help=f"Delay in seconds between HTTP requests (default: {DEFAULT_REQUEST_DELAY}s)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="List all known document sections and exit",
    )

    args = parser.parse_args()

    if args.list_sections:
        print("\nAvailable Document Sections on fsc.gov.et:")
        print("-" * 75)
        for key, val in SECTIONS.items():
            print(f"  {key:22} : {val['name']}")
            print(f"                         {val['description']}")
            print(f"                         Start: {val['start_url']}\n")
        print("  all                    : Crawl all of the above sections sequentially")
        print("-" * 75)
        return

    setup_logging(args.verbose)
    
    crawler = FSCCrawler(
        output_dir=args.output_dir,
        delay=args.delay,
        dry_run=args.dry_run,
        limit=args.limit,
        max_pages=args.max_pages,
    )

    try:
        stats = crawler.run(section_name=args.section)
        print("\n" + "=" * 50)
        print("Scraping Summary:")
        print(f"  Total Discovered : {stats['pdfs_discovered']}")
        print(f"  Downloaded       : {stats['pdfs_downloaded']}")
        print(f"  Skipped (Dupes)  : {stats['pdfs_skipped']}")
        print(f"  Failed           : {stats['pdfs_failed']}")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\n[!] Crawl interrupted by user. Manifest saved with completed downloads.")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Fatal error during crawl: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
