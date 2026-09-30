"""
Robust, resumable file downloader with Amharic/Unicode filename support and atomic writes.
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse
import requests
from tqdm import tqdm

from .config import DEFAULT_TIMEOUT

logger = logging.getLogger("fsc_scraper.downloader")

INVALID_FILENAME_CHARS = r'[\\/*?:"<>|\r\n\t\0]'


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """
    Cleans a string to make it safe for Linux/Windows/macOS filesystems
    while preserving Amharic / Unicode characters.
    """
    name = re.sub(INVALID_FILENAME_CHARS, "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    if not name:
        name = "unnamed_document"
    
    # Ensure extension is preserved if truncated
    if len(name.encode("utf-8")) > max_length:
        stem, ext = os.path.splitext(name)
        # truncate stem
        name = stem[:150].strip(" ._") + ext
        
    return name


def decode_content_disposition_filename(cd_header: str) -> Optional[str]:
    """
    Extracts and properly decodes the filename from a Content-Disposition header.
    Handles standard filenames, RFC 5987 UTF-8 encoded filenames,
    and Latin-1 mangled UTF-8 characters (common in ASP.NET / DNN servers).
    """
    if not cd_header:
        return None
        
    # Check for RFC 5987 format: filename*=UTF-8''...
    rfc_match = re.search(r"filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)", cd_header)
    if rfc_match:
        return unquote(rfc_match.group(1))
        
    # Standard format: filename="..." or filename=...
    match = re.search(r'filename\s*=\s*(?:"([^"]+)"|([^\s;]+))', cd_header)
    if not match:
        return None
        
    raw_name = match.group(1) or match.group(2)
    raw_name = raw_name.strip()
    
    # Try Latin-1 to UTF-8 decoding to fix server-side character encoding mismatch
    try:
        fixed_name = raw_name.encode("latin-1").decode("utf-8")
        return fixed_name
    except (UnicodeEncodeError, UnicodeDecodeError):
        return raw_name


def determine_filename(
    doc_info: Dict[str, Any],
    response_headers: Optional[Dict[str, str]] = None,
) -> str:
    """
    Determines a sensible, unique, and safe filename for the PDF.
    
    Strategy:
    1. Content-Disposition filename (cleaned and decoded)
    2. Document ID + link text (if link text is informative)
    3. Document ID + article title (sanitized)
    4. Fallback: document_{documentid}.pdf
    """
    doc_id = doc_info.get("document_id") or "doc"
    raw_filename = None
    
    if response_headers:
        cd = response_headers.get("Content-Disposition") or response_headers.get("content-disposition")
        if cd:
            raw_filename = decode_content_disposition_filename(cd)
            
    if not raw_filename:
        # Check if URL ends with a recognizable .pdf
        path_name = Path(urlparse(doc_info["download_url"]).path).name
        if path_name.lower().endswith(".pdf"):
            raw_filename = unquote(path_name)

    if not raw_filename:
        # Check link text
        text = doc_info.get("link_text", "").strip()
        if text and len(text) > 2 and not text.lower().startswith("http"):
            raw_filename = text if text.lower().endswith(".pdf") else f"{text}.pdf"

    if not raw_filename:
        # Check article title
        art_title = doc_info.get("article_title", "").strip()
        if art_title:
            raw_filename = f"{art_title}.pdf"

    if not raw_filename:
        raw_filename = f"document_{doc_id}.pdf"
        
    # Sanitize
    clean_name = sanitize_filename(raw_filename)
    if not clean_name.lower().endswith(".pdf"):
        clean_name += ".pdf"
        
    # Prefix with document_id to guarantee uniqueness across thousands of cases
    prefix = f"doc_{doc_id}_"
    if not clean_name.startswith(prefix) and doc_id != "doc":
        final_name = f"{prefix}{clean_name}"
    else:
        final_name = clean_name
        
    return sanitize_filename(final_name)


def download_pdf(
    session: requests.Session,
    doc_info: Dict[str, Any],
    destination_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    show_progress: bool = True,
) -> Tuple[bool, str, int, Optional[str]]:
    """
    Downloads a PDF file atomically (.part -> .pdf).
    
    Returns:
        (success: bool, final_filename: str, file_size_bytes: int, error_message: Optional[str])
    """
    url = doc_info["download_url"]
    destination_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with session.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            
            # Determine filename
            filename = determine_filename(doc_info, resp.headers)
            target_path = destination_dir / filename
            part_path = destination_dir / f"{filename}.part"
            
            # If target already exists and is non-empty, skip
            if target_path.exists() and target_path.stat().st_size > 0:
                logger.info(f"File already exists: {filename}")
                return True, filename, target_path.stat().st_size, None
                
            total_size = int(resp.headers.get("content-length", 0))
            chunk_size = 65536  # 64 KB
            downloaded = 0
            
            first_chunk = True
            with open(part_path, "wb") as f:
                desc = filename[:35]
                with tqdm(
                    total=total_size if total_size > 0 else None,
                    unit="B",
                    unit_scale=True,
                    desc=desc,
                    leave=False,
                    disable=not show_progress,
                ) as pbar:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        if first_chunk:
                            first_chunk = False
                            # Optional sanity check: is this HTML instead of PDF?
                            if chunk.strip().startswith(b"<!DOCTYPE") or chunk.strip().startswith(b"<html"):
                                part_path.unlink(missing_ok=True)
                                return False, filename, 0, "Server returned HTML error page instead of PDF"
                        f.write(chunk)
                        downloaded += len(chunk)
                        pbar.update(len(chunk))
                        
            # Atomic rename
            part_path.rename(target_path)
            actual_size = target_path.stat().st_size
            logger.info(f"Downloaded: {filename} ({actual_size:,} bytes)")
            return True, filename, actual_size, None

    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        return False, "", 0, str(e)
