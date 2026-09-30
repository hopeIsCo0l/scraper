"""
Download Manifest & Tracking System
Avoids duplicates, records comprehensive metadata, and supports resuming.
"""
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("fsc_scraper.manifest")


class Manifest:
    """
    Persistent registry of discovered and downloaded PDF documents.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.output_dir / "manifest.json"
        self.csv_path = self.output_dir / "manifest.csv"
        
        self.entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Loads existing manifest from disk if present."""
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
                logger.info(f"Loaded existing manifest with {len(self.entries)} records.")
            except Exception as e:
                logger.warning(f"Could not load existing manifest: {e}. Starting fresh.")
                self.entries = {}

    def _save(self):
        """Saves current state to JSON and CSV."""
        try:
            # Save JSON
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
                
            # Save CSV for easy viewing in Excel / LibreOffice
            fieldnames = [
                "key",
                "document_id",
                "article_id",
                "section",
                "filename",
                "file_path",
                "file_size_bytes",
                "article_title",
                "article_url",
                "download_url",
                "status",
                "error",
                "timestamp",
            ]
            with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for key, data in self.entries.items():
                    row = {"key": key, **data}
                    writer.writerow(row)
        except Exception as e:
            logger.error(f"Failed to persist manifest: {e}")

    def make_key(self, doc_info: Dict[str, Any]) -> str:
        """Generates a unique key for deduplication."""
        doc_id = doc_info.get("document_id")
        if doc_id:
            return f"doc_{doc_id}"
        return doc_info["download_url"]

    def is_already_downloaded(self, doc_info: Dict[str, Any]) -> bool:
        """
        Returns True if the document was previously downloaded and the file still exists on disk.
        """
        key = self.make_key(doc_info)
        entry = self.entries.get(key)
        if not entry or entry.get("status") != "success":
            return False
            
        file_path_str = entry.get("file_path")
        if not file_path_str:
            return False
            
        file_path = self.output_dir / file_path_str
        return file_path.exists() and file_path.stat().st_size > 0

    def record_success(
        self,
        doc_info: Dict[str, Any],
        filename: str,
        relative_path: str,
        file_size_bytes: int,
        section_name: str = "",
    ):
        """Records a successful download."""
        key = self.make_key(doc_info)
        self.entries[key] = {
            "document_id": doc_info.get("document_id"),
            "article_id": doc_info.get("article_id"),
            "section": section_name,
            "filename": filename,
            "file_path": relative_path,
            "file_size_bytes": file_size_bytes,
            "article_title": doc_info.get("article_title", ""),
            "article_url": doc_info.get("article_url", ""),
            "download_url": doc_info.get("download_url", ""),
            "link_text": doc_info.get("link_text", ""),
            "status": "success",
            "error": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def record_failure(
        self,
        doc_info: Dict[str, Any],
        error_msg: str,
        section_name: str = "",
    ):
        """Records a failed download attempt."""
        key = self.make_key(doc_info)
        self.entries[key] = {
            "document_id": doc_info.get("document_id"),
            "article_id": doc_info.get("article_id"),
            "section": section_name,
            "filename": "",
            "file_path": "",
            "file_size_bytes": 0,
            "article_title": doc_info.get("article_title", ""),
            "article_url": doc_info.get("article_url", ""),
            "download_url": doc_info.get("download_url", ""),
            "link_text": doc_info.get("link_text", ""),
            "status": "failed",
            "error": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def record_skipped(
        self,
        doc_info: Dict[str, Any],
        reason: str = "already_exists",
        section_name: str = "",
    ):
        """Ensures entry exists when skipped."""
        key = self.make_key(doc_info)
        if key not in self.entries:
            self.entries[key] = {
                "document_id": doc_info.get("document_id"),
                "article_id": doc_info.get("article_id"),
                "section": section_name,
                "status": "skipped",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def get_summary(self) -> Dict[str, int]:
        """Returns statistics for reporting."""
        total = len(self.entries)
        success = sum(1 for e in self.entries.values() if e.get("status") == "success")
        failed = sum(1 for e in self.entries.values() if e.get("status") == "failed")
        skipped = sum(1 for e in self.entries.values() if e.get("status") == "skipped")
        return {
            "total_tracked": total,
            "successful_downloads": success,
            "failed_downloads": failed,
            "skipped": skipped,
        }
