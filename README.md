# Federal Supreme Court of Ethiopia (FSC) Document Scraper & Crawler

A robust, modular web crawler and scraper designed to discover, track, and download all legal decisions, law publications, and PDF documents published on the [Federal Supreme Court of Ethiopia](https://www.fsc.gov.et/) website.

---

## Features

- **Multi-Section Discovery**: Automatically crawls and paginates through all document repositories on `fsc.gov.et`:
  - **Supreme Court Decisions** (Full multi-hundred page volume compilations)
  - **Federal Cassation Decision Series** (Vols 1 to 28+)
  - **Comprehensive Cassation Judgments** (~2,700 individual cases across 680+ listing pages)
  - **Federal Laws & Proclamations** (Directives, regulations, statutes)
  - **Annual Reports**
  - **Newsletters & Journals**
  - **Procurement Tenders & Standard Bidding Documents**
  - **Job Vacancies & Auction Notices**
- **Resumable & Deduplicated**:
  - Automatically identifies unique documents using EasyDNNNews document IDs.
  - Skips already-downloaded documents and verifies local file integrity on disk.
  - Can be stopped and resumed at any time without duplicate requests.
- **Sensible & Unicode Filenames**:
  - Correctly extracts and decodes Amharic / Ethiopic Unicode characters from HTTP `Content-Disposition` headers (e.g., `doc_2971_ቅጽ(volume)14.pdf`, `doc_3867_ሰበር መዝገብ 244308.pdf`).
  - Falls back to link text, case numbers, or article titles.
  - Filesystem-sanitized and prefixed with `doc_{id}_` to avoid collisions.
- **Atomic Downloads**:
  - Downloads in chunks via `.part` files, renaming atomically upon completion to guarantee zero corrupted files if interrupted.
- **Progress Tracking & Manifest**:
  - Live progress bars (`tqdm`) showing transfer speeds and counters (`DL`, `Skip`, `Fail`).
  - Records full metadata to both `downloads/manifest.json` and `downloads/manifest.csv` (source URL, PDF URL, document ID, article title, file size, timestamp).
- **Graceful Error Handling & Retries**:
  - Automatic exponential backoff retries on network dropouts, HTTP 429, and 5xx errors via `urllib3.util.Retry`.
  - Configurable rate limiting / politeness delay between requests.

---

## Project Structure

```text
scraper/
├── fsc_scraper/
│   ├── __init__.py         # Package exports
│   ├── config.py           # Pre-configured sections, URLs, headers, and defaults
│   ├── session.py          # Session factory with retries, pooling, and SSL handling
│   ├── paginator.py        # Pager detector (PageID/PgrID) and listing page generator
│   ├── extractor.py        # Article and PDF link parsers (BeautifulSoup)
│   ├── downloader.py       # Atomic streaming downloader with Unicode header decoding
│   ├── manifest.py         # JSON and CSV download tracking & deduplication
│   └── crawler.py          # Orchestrator pipeline
├── run_scraper.py          # CLI entry point
├── requirements.txt        # Python package dependencies
├── .gitignore              # Ignores .venv, downloads/, __pycache__
└── README.md               # Documentation
```

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hopeIsCo0l/scraper.git
   cd scraper
   ```

2. **Set up a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage Guide

### 1. View Available Document Sections
```bash
python run_scraper.py --list-sections
```
Output:
```text
Available Document Sections on fsc.gov.et:
---------------------------------------------------------------------------
  supreme-court          : Supreme Court Decisions (Volumes)
  cassation-series       : Federal Cassation Decision Series
  federal-laws           : Federal Laws
  annual-reports         : Annual Reports
  newsletter             : Newsletters
  tenders                : Tenders & Bidding Documents
  vacancies              : Vacancies & Announcements
  auctions               : Auctions (Judgement Execution)
  archives               : Archives
  cassation-decisions    : Cassation Decisions (Comprehensive)
  all                    : Crawl all of the above sections sequentially
---------------------------------------------------------------------------
```

### 2. Discovery Test (Dry Run — No Downloads)
Discovers all pages and document links without writing any files:
```bash
python run_scraper.py --section supreme-court --dry-run
```

To limit page scanning during tests:
```bash
python run_scraper.py --section cassation-series --max-pages 2 --dry-run
```

### 3. Sample Download Test (e.g., First 5 PDFs)
Download a limited batch to verify end-to-end functionality:
```bash
python run_scraper.py --section supreme-court --limit 5
```

### 4. Download a Specific Section
Download all files in a specific category:
```bash
# Federal Cassation Decision Series (28+ volumes)
python run_scraper.py --section cassation-series

# Federal Laws, Directives, and Regulations
python run_scraper.py --section federal-laws

# Annual Reports
python run_scraper.py --section annual-reports
```

### 5. Download All Available Documents (500+ PDFs)
To crawl and download across all categories sequentially:
```bash
python run_scraper.py --section all --delay 0.5
```

---

## Output & Manifest

Downloaded files are organized by category under `downloads/`:
```text
downloads/
├── manifest.csv
├── manifest.json
├── supreme-court/
│   ├── doc_2971_ቅጽ(volume)14.pdf
│   ├── doc_2970_ቅጽ(volume)13.pdf
│   └── ...
├── cassation-series/
│   ├── doc_3864_ቅጽ_28_.pdf
│   └── ...
└── cassation-decisions/
    ├── doc_3883_271003.pdf
    ├── doc_3869_271726.pdf
    └── doc_3867_ሰበር መዝገብ 244308 (1).pdf
```

The `downloads/manifest.csv` and `manifest.json` files contain complete metadata for every discovered document:
- `document_id`: EasyDNNNews document ID
- `article_id`: Associated article ID
- `section`: Document category
- `filename`: Local filesystem filename
- `file_path`: Subfolder and filename
- `file_size_bytes`: Exact byte size
- `article_title`: Clean article title / case name
- `article_url`: Full article web page URL
- `download_url`: Direct endpoint URL
- `status`: `success`, `skipped`, or `failed`
- `timestamp`: UTC ISO timestamp of download

---

## CLI Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `--section` | string | `supreme-court` | Target section or `all` |
| `--limit` | int | `None` | Max number of PDFs to download |
| `--max-pages` | int | `None` | Max listing pages to crawl per section |
| `--dry-run` | flag | `False` | Discovery only, do not download |
| `--output-dir` | path | `./downloads` | Directory to save PDFs and manifest |
| `--delay` | float | `0.4` | Polite sleep in seconds between requests |
| `--verbose`, `-v` | flag | `False` | Enable debug logs |
| `--list-sections`| flag | `False` | Display known sections and exit |
