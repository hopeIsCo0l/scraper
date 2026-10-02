"""
Extraction functions for article listings and attached PDF documents
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger("fsc_scraper.extractor")

IGNORED_URL_SUBSTRINGS = [
    "pageid/",
    "pgrid/",
    "categoryid/",
    "tagid/",
    "authorid/",
    "returnurl=",
    "login",
    "register",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "t.me",
    "#",
    "javascript:",
    "mailto:",
    "tel:",
]


def extract_article_links(soup: BeautifulSoup, current_page_url: str) -> List[Dict[str, str]]:
    """
    Extracts individual article/document detail links from a listing page.
    Handles various EasyDNNNews layouts (cards, lists, tables).
    """
    articles: List[Dict[str, str]] = []
    seen_urls = set()

    # 1. Primary strategy: find <article> elements (standard EasyDNNNews)
    article_elements = soup.find_all("article")
    if article_elements:
        for art in article_elements:
            # Look for heading or title link inside the article
            title_tag = art.find(["h2", "h3", "h4", "h5", "a"], class_=lambda c: c and any(w in str(c).lower() for w in ["title", "head"]))
            link = title_tag if (title_tag and title_tag.name == "a") else (title_tag.find("a", href=True) if title_tag else art.find("a", href=True))
            
            if link and link.get("href"):
                raw_href = link["href"].strip()
                if any(bad in raw_href.lower() for bad in IGNORED_URL_SUBSTRINGS):
                    continue
                full_url = urljoin(current_page_url, raw_href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                title = link.get_text(strip=True) or (art.find(["h2", "h3", "h4"]).get_text(strip=True) if art.find(["h2", "h3", "h4"]) else "")
                # Extract date if available
                date_tag = art.find(class_=lambda c: c and any(d in str(c).lower() for d in ["date", "publish", "time"]))
                date_str = date_tag.get_text(strip=True) if date_tag else ""
                
                articles.append({
                    "url": full_url,
                    "title": title.strip(),
                    "date": date_str,
                })
        if articles:
            return articles

    # 2. Fallback: find links inside EasyDNNNews containers (.EDN_article, .article, etc.)
    containers = soup.find_all(class_=lambda c: c and any(w in str(c).lower() for w in ["edn_", "article", "news_item"]))
    for cont in containers:
        for a in cont.find_all("a", href=True):
            raw_href = a["href"].strip()
            if any(bad in raw_href.lower() for bad in IGNORED_URL_SUBSTRINGS):
                continue
            full_url = urljoin(current_page_url, raw_href)
            if full_url in seen_urls:
                continue
            
            # Must look like a content link (has path segments)
            parsed = urlparse(full_url)
            path = parsed.path.rstrip("/")
            if len(path.split("/")) < 2:
                continue
                
            text = a.get_text(strip=True)
            if text.lower() in ["read more", "more", "detail", "view", "..."]:
                text = ""
                
            seen_urls.add(full_url)
            articles.append({
                "url": full_url,
                "title": text,
                "date": "",
            })

    return articles


def extract_document_links(soup: BeautifulSoup, article_url: str) -> List[Dict[str, str]]:
    """
    Extracts all attached PDF / document download links from an article page.
    """
    docs: List[Dict[str, str]] = []
    seen_urls = set()
    
    # Try to extract the page/article title
    page_title = ""
    for heading in soup.find_all(["h1", "h2"]):
        h_text = heading.get_text(strip=True)
        if h_text and len(h_text) > 3 and not any(k in h_text.lower() for k in ["court", "search", "menu", "login"]):
            page_title = h_text
            break
    if not page_title and soup.title:
        page_title = soup.title.get_text(strip=True).split("-")[0].strip()

    # 1. Look for DocumentDownload.ashx and direct PDF links in <a> tags
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        href_lower = href.lower()
        text = a.get_text(strip=True)
        
        is_dnn_doc = "documentdownload.ashx" in href_lower
        is_pdf_ext = href_lower.endswith(".pdf") or ".pdf?" in href_lower
        
        if is_dnn_doc or is_pdf_ext:
            full_url = urljoin(article_url, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            parsed = urlparse(full_url)
            raw_qs = parse_qs(parsed.query)
            qs = {k.lower(): v for k, v in raw_qs.items()}
            
            doc_id = qs.get("documentid", [None])[0]
            art_id = qs.get("articleid", [None])[0]
            mod_id = qs.get("moduleid", [None])[0]
            
            docs.append({
                "download_url": full_url,
                "link_text": text,
                "document_id": doc_id,
                "article_id": art_id,
                "module_id": mod_id,
                "article_title": page_title,
                "article_url": article_url,
            })

    # 2. Look for embedded PDFs (<iframe src="...pdf">, <embed>, <object>)
    for tag in soup.find_all(["iframe", "embed", "object"]):
        src = tag.get("src") or tag.get("data")
        if src and ".pdf" in src.lower():
            full_url = urljoin(article_url, src.strip())
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                docs.append({
                    "download_url": full_url,
                    "link_text": "Embedded Document",
                    "document_id": None,
                    "article_id": None,
                    "module_id": None,
                    "article_title": page_title,
                    "article_url": article_url,
                })

    return docs
